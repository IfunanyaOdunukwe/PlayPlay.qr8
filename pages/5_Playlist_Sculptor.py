import streamlit as st
st.set_page_config(page_title="Playlist Sculptor | PlayPlay.qr8", layout="wide")

import spotipy
import pandas as pd
from src.auth import SpotifyAuthManager
from src.demo import load_playlist_df
from src.llm_providers import get_chat_model
from src.agent import generate_response, apply_proposal, compute_comparison, SculptorProposal
from src.session_state import get_selected_playlist_snapshot
from src.rate_limiter import (
    SESSION_MESSAGE_CAP,
    validate_prompt,
    check_session_cap,
    check_global_cap,
    record_request,
)
from src.theme import apply_spotify_theme, render_nav_button, render_playlist_indicator

apply_spotify_theme()
st.title("")

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
selected_playlist = get_selected_playlist_snapshot(st.session_state)

if not selected_playlist:
    st.warning("No playlist selected.")
    render_nav_button(
        "pages/2_Connect_and_Select.py",
        "Open Connect & Select →",
        icon="🔗",
        key="sculptor_open_connect",
    )
    st.stop()

playlist_name = selected_playlist["name"]
playlist_id = selected_playlist["id"]
playlist_source = selected_playlist.get("source") or "spotify"

render_playlist_indicator("Current Playlist", playlist_name)
st.write(
    "Review the working playlist, ask for changes, and export the result to Spotify if you want."
)

_cache_key = f"_cached_df_{playlist_id}"
if _cache_key not in st.session_state:
    try:
        st.session_state[_cache_key] = load_playlist_df(playlist_id, playlist_source)
    except (FileNotFoundError, KeyError, ValueError) as e:
        st.error(f"Failed to load playlist data: {e}")
        st.stop()
df_cached = st.session_state[_cache_key]
if df_cached is None or df_cached.empty:
    st.warning("No cached data found. Load the playlist on Breakdown first.")
    render_nav_button(
        "pages/3_Playlist_Breakdown.py",
        "Open Breakdown →",
        icon="📊",
        key="sculptor_open_breakdown",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Session state initialisation (resets when playlist changes)
# ---------------------------------------------------------------------------
if (
    "sculptor_df_original" not in st.session_state
    or st.session_state.get("sculptor_playlist_id") != playlist_id
):
    st.session_state["sculptor_df_original"] = df_cached.copy()
    st.session_state["sculptor_df_working"] = df_cached.copy()
    st.session_state["sculptor_messages"] = []
    st.session_state["sculptor_pending_proposal"] = None
    st.session_state["sculptor_pending_df_preview"] = None
    st.session_state["sculptor_pending_comparison"] = None
    st.session_state["sculptor_session_count"] = 0
    st.session_state["sculptor_playlist_id"] = playlist_id

df_working: pd.DataFrame = st.session_state["sculptor_df_working"]

# ---------------------------------------------------------------------------
# Process approve / reject from previous rerun
# ---------------------------------------------------------------------------
def _resolve_pending(apply: bool):
    """Clear pending proposal state; optionally apply the preview."""
    if apply:
        st.session_state["sculptor_df_working"] = st.session_state["sculptor_pending_df_preview"]
    msg = "Changes applied." if apply else "Changes discarded."
    st.session_state["sculptor_messages"].append({"role": "assistant", "content": msg})
    st.session_state["sculptor_pending_proposal"] = None
    st.session_state["sculptor_pending_df_preview"] = None
    st.session_state["sculptor_pending_comparison"] = None

if st.session_state.get("sculptor_do_approve"):
    _resolve_pending(apply=True)
    st.session_state["sculptor_do_approve"] = False
    df_working = st.session_state["sculptor_df_working"]

if st.session_state.get("sculptor_do_reject"):
    _resolve_pending(apply=False)
    st.session_state["sculptor_do_reject"] = False

# ---------------------------------------------------------------------------
# Sidebar — LLM configuration
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Sculptor")

    try:
        groq_api_key = st.secrets["groq_api_key"]
        llm_ready = True
    except (KeyError, FileNotFoundError):
        groq_api_key = None
        llm_ready = False
        st.error("Sculptor is not configured on this server.", icon="⚠️")

    if llm_ready:
        st.caption("Llama 4 Scout via Groq")
        remaining = SESSION_MESSAGE_CAP - st.session_state.get("sculptor_session_count", 0)
        st.caption(f"Session messages left: **{remaining}/{SESSION_MESSAGE_CAP}**")

# ---------------------------------------------------------------------------
# Working playlist stats bar
# ---------------------------------------------------------------------------
st.markdown("#### Stats")

stat_cols = st.columns(5)
stat_features = [
    ("Tracks", None, lambda df: str(len(df))),
    ("Avg Energy", "energy", lambda df: f"{pd.to_numeric(df['energy'], errors='coerce').mean():.0%}"),
    ("Avg Valence", "valence", lambda df: f"{pd.to_numeric(df['valence'], errors='coerce').mean():.0%}"),
    ("Avg Danceability", "danceability", lambda df: f"{pd.to_numeric(df['danceability'], errors='coerce').mean():.0%}"),
    ("Avg Tempo", "tempo", lambda df: f"{pd.to_numeric(df['tempo'], errors='coerce').mean():.0f} BPM"),
]

for col, (label, feat, fmt_fn) in zip(stat_cols, stat_features):
    if feat and feat not in df_working.columns:
        continue
    with col:
        st.metric(label=label, value=fmt_fn(df_working))

# Reset button — only show if working data differs from original
df_original = st.session_state["sculptor_df_original"]
has_changes = len(df_working) != len(df_original) or not df_working["id"].equals(df_original["id"])

if has_changes:
    if st.button("Reset Playlist", help="Discard changes and restore the original playlist."):
        st.session_state["sculptor_df_working"] = st.session_state["sculptor_df_original"].copy()
        st.session_state["sculptor_messages"].append(
            {"role": "assistant", "content": "Playlist reset to original."}
        )
        st.session_state["sculptor_pending_proposal"] = None
        st.session_state["sculptor_pending_df_preview"] = None
        st.session_state["sculptor_pending_comparison"] = None
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Chat interface
# ---------------------------------------------------------------------------
st.markdown("### Sculpt")
st.caption("Ask for cuts, reordering, highlights, or explanations. Nothing changes until you approve.")

# Render history
for msg in st.session_state["sculptor_messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Render pending proposal (if any)
pending = st.session_state.get("sculptor_pending_proposal")
comparison = st.session_state.get("sculptor_pending_comparison")

if not st.session_state["sculptor_messages"] and not pending:
    st.markdown(
        """
        <div class="spotify-empty-chat-shell">
            <section class="spotify-helper-panel spotify-chat-empty-panel">
                <div class="spotify-helper-kicker">Starter Prompts</div>
                <h3>Describe the change</h3>
                <p class="spotify-helper-copy">
                    Start with a mood, pacing change, or a rule for what stays and what goes.
                </p>
                <div class="spotify-helper-grid spotify-helper-grid-compact">
                    <div class="spotify-helper-card">
                        <strong>Warm the mood</strong>
                        <span>"Make this playlist feel warmer and more cohesive."</span>
                    </div>
                    <div class="spotify-helper-card">
                        <strong>Trim the intensity</strong>
                        <span>"Remove tracks that are too intense and keep the dreamiest ones."</span>
                    </div>
                    <div class="spotify-helper-card">
                        <strong>Reshape the arc</strong>
                        <span>"Reorder this so it opens softly, peaks in the middle, and lands gently."</span>
                    </div>
                </div>
                <div class="spotify-helper-footer">Changes apply only after approval.</div>
            </section>
        </div>
        """,
        unsafe_allow_html=True,
    )

if pending and comparison:
    with st.expander("Proposal Details", expanded=True):
        st.write(pending.reasoning)

        st.caption("Before / After")
        comp_rows = []
        for metric, (before, after) in comparison.items():
            if before is None and after is None:
                continue
            label = metric.replace("_", " ").title()
            comp_rows.append({"Metric": label, "Before": before, "After": after})
        if comp_rows:
            st.table(pd.DataFrame(comp_rows))

        # Show affected tracks
        all_affected_ids = set()
        for op in pending.operations:
            all_affected_ids.update(op.track_ids)
        if all_affected_ids:
            affected = df_working[df_working["id"].isin(all_affected_ids)]
            display_cols = [c for c in ["name", "artist", "energy", "valence", "tempo"] if c in affected.columns]
            if display_cols:
                st.caption("Affected tracks")
                st.dataframe(affected[display_cols], use_container_width=True, hide_index=True)

    btn_cols = st.columns(2)
    with btn_cols[0]:
        if st.button("Apply", type="primary", use_container_width=True):
            st.session_state["sculptor_do_approve"] = True
            st.rerun()
    with btn_cols[1]:
        if st.button("Discard", use_container_width=True):
            st.session_state["sculptor_do_reject"] = True
            st.rerun()

# Chat input
if prompt := st.chat_input("Describe how to reshape this playlist...", disabled=not llm_ready):
    # Find the most recent user prompt for duplicate detection
    last_prompt = next(
        (m["content"] for m in reversed(st.session_state["sculptor_messages"]) if m["role"] == "user"),
        None,
    )

    # Pre-flight checks, short-circuit on first failure
    checks = [
        validate_prompt(prompt, last_prompt),
        check_session_cap(st.session_state.get("sculptor_session_count", 0)),
        check_global_cap(),
    ]
    first_block = next((c for c in checks if not c.allowed), None)

    if first_block:
        st.session_state["sculptor_messages"].append({"role": "user", "content": prompt})
        st.session_state["sculptor_messages"].append(
            {"role": "assistant", "content": first_block.reason}
        )
        st.rerun()
    else:
        st.session_state["sculptor_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    llm = get_chat_model(groq_api_key)
                    result = generate_response(
                        llm,
                        df_working,
                        st.session_state["sculptor_messages"],
                        prompt,
                    )

                    # Increment counters only on successful Groq call
                    st.session_state["sculptor_session_count"] = (
                        st.session_state.get("sculptor_session_count", 0) + 1
                    )
                    record_request()

                    if isinstance(result, SculptorProposal):
                        df_preview = apply_proposal(df_working, result)
                        comp = compute_comparison(df_working, df_preview)

                        st.session_state["sculptor_pending_proposal"] = result
                        st.session_state["sculptor_pending_df_preview"] = df_preview
                        st.session_state["sculptor_pending_comparison"] = comp

                        st.session_state["sculptor_messages"].append(
                            {"role": "assistant", "content": result.summary}
                        )
                    else:
                        st.session_state["sculptor_messages"].append(
                            {"role": "assistant", "content": result}
                        )

                    st.rerun()
                except Exception as e:
                    error_msg = str(e)
                    error_lower = error_msg.lower()
                    if "rate_limit" in error_lower or "429" in error_lower:
                        user_msg = "Groq is rate-limiting the app right now. Please wait a moment and try again."
                    elif "quota" in error_lower or "insufficient_quota" in error_lower:
                        user_msg = "The app has hit its Groq usage quota. Please try again later."
                    else:
                        user_msg = f"Error generating response: {e}"
                    st.error(user_msg)

# ---------------------------------------------------------------------------
# Push to Spotify
# ---------------------------------------------------------------------------
# has_changes and df_original already computed above

st.markdown("### Export")

if has_changes:
    if playlist_source == "demo":
        st.info(
            "Demo playlists are local sample CSVs, so they cannot be exported. Connect Spotify to create a playlist there."
        )
        render_nav_button(
            "pages/2_Connect_and_Select.py",
            "Connect Spotify →",
            icon="🎵",
            key="sculptor_connect_spotify",
        )
    else:
        new_name = st.text_input(
            "New playlist name",
            value=f"{playlist_name} (Sculpted)",
        )

        if st.button("Create in Spotify", type="primary"):
            token_info = st.session_state.get("token_info")
            if not token_info or not SpotifyAuthManager.is_token_valid(token_info):
                st.error("Spotify authentication expired. Please reconnect on the Connect page.")
            else:
                try:
                    sp = spotipy.Spotify(auth=token_info["access_token"])
                    user_id = sp.current_user()["id"]
                    new_playlist = sp.user_playlist_create(user_id, new_name, public=False)
                    new_playlist_id = new_playlist["id"]

                    # Add tracks in batches of 100
                    uris = df_working["uri"].tolist()
                    for i in range(0, len(uris), 100):
                        sp.playlist_add_items(new_playlist_id, uris[i : i + 100])

                    playlist_url = new_playlist["external_urls"]["spotify"]
                    st.success(f"Created **{new_name}** with {len(uris)} tracks!")
                    st.link_button("Open in Spotify", playlist_url)
                except spotipy.SpotifyException as e:
                    if e.http_status == 403:
                        st.error(
                            "Your session lacks playlist write permissions. "
                            "Please disconnect and reconnect on the Connect & Select page."
                        )
                    else:
                        st.error(f"Spotify error: {e}")
                except Exception as e:
                    st.error(f"Error creating playlist: {e}")
else:
    st.info("Approve changes to unlock Spotify export.")
