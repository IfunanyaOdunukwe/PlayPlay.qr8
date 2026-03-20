"""Playlist Sculptor agent — translates natural language into DataFrame operations."""

from __future__ import annotations

import json
import re
from typing import Literal

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Structured output models
# ---------------------------------------------------------------------------

AUDIO_FEATURES = [
    "energy", "valence", "tempo", "danceability", "acousticness",
    "loudness", "speechiness", "instrumentalness", "liveness",
]


class TrackOperation(BaseModel):
    action: Literal["remove", "reorder", "highlight"] = Field(
        description="The type of operation to perform."
    )
    track_ids: list[str] = Field(
        default_factory=list,
        description="Specific Spotify track IDs to act on (for remove/highlight).",
    )
    criteria: dict | None = Field(
        default=None,
        description='Criteria-based filter, e.g. {"energy": {">": 0.8}}.',
    )
    sort_key: str | None = Field(
        default=None,
        description="Column name to sort by (for reorder).",
    )
    sort_ascending: bool = Field(
        default=True,
        description="Sort direction (for reorder).",
    )


class SculptorProposal(BaseModel):
    reasoning: str = Field(description="Explanation of why these changes are proposed.")
    operations: list[TrackOperation] = Field(description="Ordered list of operations.")
    summary: str = Field(description="One-sentence summary of the proposed changes.")


# ---------------------------------------------------------------------------
# Playlist context builder
# ---------------------------------------------------------------------------

def build_playlist_context(df: pd.DataFrame) -> str:
    """Build a compact text representation of the playlist for the LLM."""
    lines: list[str] = []

    # Summary statistics
    lines.append("## Playlist Summary")
    lines.append(f"Track count: {len(df)}")
    for feat in AUDIO_FEATURES:
        if feat in df.columns:
            series = pd.to_numeric(df[feat], errors="coerce").dropna()
            if not series.empty:
                lines.append(f"  {feat}: mean={series.mean():.3f}, std={series.std():.3f}")

    if "mode" in df.columns:
        mode_series = pd.to_numeric(df["mode"], errors="coerce").dropna()
        if not mode_series.empty:
            major_pct = mode_series.mean() * 100
            lines.append(f"  mode: {major_pct:.0f}% Major / {100 - major_pct:.0f}% Minor")

    # Compact track listing
    cols = ["id", "name", "artist"] + [f for f in AUDIO_FEATURES if f in df.columns]
    if "mode" in df.columns:
        cols.append("mode")

    lines.append("")
    lines.append("## Track Listing")
    lines.append(" | ".join(cols))
    lines.append("-" * 40)

    # Vectorized: format floats to 3 decimals, everything else as string
    formatted = df[cols].copy()
    for c in cols:
        if formatted[c].dtype == "float64":
            formatted[c] = formatted[c].map(lambda v: f"{v:.3f}")
        else:
            formatted[c] = formatted[c].astype(str)
    lines.extend(formatted.agg(" | ".join, axis=1).tolist())

    return "\n".join(lines)


SYSTEM_PROMPT = """\
You are the Playlist Sculptor, an AI assistant that helps users understand and reshape Spotify playlists.

You have two modes:

**Conversation mode** — When the user asks questions about the playlist (e.g. "what is the vibe?", \
"which tracks are most energetic?", "describe this playlist"), respond naturally in plain text. \
Do NOT propose operations for conversational questions.

**Sculpting mode** — When the user asks you to change the playlist (e.g. "remove low energy tracks", \
"sort by tempo", "make it more danceable"), respond ONLY with a JSON object (no other text) matching this schema:
{{
  "reasoning": "why these changes are proposed",
  "operations": [
    {{
      "action": "remove" | "reorder" | "highlight",
      "track_ids": ["id1", "id2"],
      "criteria": {{"column_name": {{"operator": value}}}},
      "sort_key": "column_name",
      "sort_ascending": true
    }}
  ],
  "summary": "one-sentence summary"
}}

Operation details:
- **remove** — Remove tracks by specific IDs (set track_ids) or by criteria (set criteria, leave track_ids empty). \
Criteria operators: ">", "<", ">=", "<=", "==".
- **reorder** — Sort tracks by an audio feature column (set sort_key and sort_ascending).
- **highlight** — Mark tracks by IDs without removing them.

Be specific: name the tracks you'd affect and explain why. Keep reasoning concise.

{playlist_context}
"""


# ---------------------------------------------------------------------------
# Proposal generation
# ---------------------------------------------------------------------------

def _build_messages(df: pd.DataFrame, chat_history: list[dict], user_message: str):
    playlist_context = build_playlist_context(df)
    system = SystemMessage(content=SYSTEM_PROMPT.format(playlist_context=playlist_context))
    messages = [system]
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))
    return messages


def _parse_json_fallback(text: str) -> SculptorProposal:
    """Extract JSON from LLM text response when structured output fails."""
    # Try to find JSON in code blocks
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        data = json.loads(match.group(1))
        return SculptorProposal(**data)
    # Try the entire text as JSON
    data = json.loads(text)
    return SculptorProposal(**data)


def generate_response(
    llm, df: pd.DataFrame, chat_history: list[dict], user_message: str
) -> SculptorProposal | str:
    """Call the LLM and return a SculptorProposal or a plain text response.

    The LLM decides whether to respond conversationally (returns str) or
    propose playlist changes (returns SculptorProposal).
    """
    messages = _build_messages(df, chat_history, user_message)
    response = llm.invoke(messages)
    content = response.content
    # Some providers return content as a list of blocks
    if isinstance(content, list):
        text = " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ).strip()
    else:
        text = content.strip()

    # Try to parse as a proposal — if the LLM responded with JSON,
    # it's a sculpting action.
    try:
        return _parse_json_fallback(text)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass

    # Otherwise it's a conversational response.
    return text


# ---------------------------------------------------------------------------
# Proposal application
# ---------------------------------------------------------------------------

def apply_proposal(df: pd.DataFrame, proposal: SculptorProposal) -> pd.DataFrame:
    """Apply a SculptorProposal to a DataFrame and return the new copy."""
    result = df.copy()

    for op in proposal.operations:
        if op.action == "remove":
            if op.track_ids:
                result = result[~result["id"].isin(op.track_ids)]
            elif op.criteria:
                mask = pd.Series(True, index=result.index)
                for col, conditions in op.criteria.items():
                    if col not in result.columns:
                        continue
                    series = pd.to_numeric(result[col], errors="coerce")
                    for operator, value in conditions.items():
                        if operator == ">":
                            mask &= series > value
                        elif operator == "<":
                            mask &= series < value
                        elif operator == ">=":
                            mask &= series >= value
                        elif operator == "<=":
                            mask &= series <= value
                        elif operator == "==":
                            mask &= series == value
                # Remove tracks matching the criteria
                result = result[~mask]

        elif op.action == "reorder":
            if op.sort_key and op.sort_key in result.columns:
                result = result.sort_values(
                    op.sort_key, ascending=op.sort_ascending
                ).reset_index(drop=True)

        elif op.action == "highlight":
            if op.track_ids:
                result["_highlighted"] = result["id"].isin(op.track_ids)

    return result


# ---------------------------------------------------------------------------
# Before / after comparison
# ---------------------------------------------------------------------------

def compute_comparison(df_before: pd.DataFrame, df_after: pd.DataFrame) -> dict:
    """Return a dict of before/after stats for key metrics."""
    stats = {"track_count": (len(df_before), len(df_after))}

    for feat in ["energy", "valence", "danceability", "tempo", "acousticness"]:
        if feat in df_before.columns and feat in df_after.columns:
            before = pd.to_numeric(df_before[feat], errors="coerce").dropna()
            after = pd.to_numeric(df_after[feat], errors="coerce").dropna()
            stats[feat] = (
                round(float(before.mean()), 3) if not before.empty else None,
                round(float(after.mean()), 3) if not after.empty else None,
            )

    return stats
