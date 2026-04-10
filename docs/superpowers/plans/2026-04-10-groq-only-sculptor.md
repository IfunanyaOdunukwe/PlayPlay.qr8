# Groq-Only Sculptor Implementation Plan

**Goal:** Replace multi-provider LLM config with Groq-only (Llama 4 Scout), add rate limiting and input validation.

**Architecture:** Simplify `src/llm_providers.py` to a single `get_chat_model(api_key)` returning `ChatGroq`. Add new `src/rate_limiter.py` with pure functions for input validation, session cap, and global daily cap (JSON file on disk). Rewrite the Sculptor page sidebar and chat input handler.

**Tech Stack:** langchain-groq, Streamlit, Python stdlib (json, datetime, dataclasses)

---

### Task 1: Simplify `src/llm_providers.py`

**Files:**
- Modify: `src/llm_providers.py` (full rewrite, 42 → ~15 lines)

- [ ] **Step 1: Replace file contents**

```python
"""Groq chat model factory."""
from langchain_groq import ChatGroq

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def get_chat_model(api_key: str):
    """Return a ChatGroq instance configured for the Sculptor."""
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=api_key,
        temperature=0.4,
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/llm_providers.py
git commit -m "refactor(llm): collapse multi-provider dispatch to Groq-only"
```

---

### Task 2: Create `src/rate_limiter.py`

**Files:**
- Create: `src/rate_limiter.py`

- [ ] **Step 1: Write the module**

```python
"""Rate limiting and input validation for the Sculptor.

Pure functions — no Streamlit imports. Global counter persists to a JSON file.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date

MAX_PROMPT_LENGTH = 500
SESSION_MESSAGE_CAP = 20
GLOBAL_DAILY_CAP = 500
GLOBAL_COUNTER_FILE = "cache/sculptor_global_counter.json"


@dataclass
class RateLimitResult:
    allowed: bool
    reason: str | None = None


def validate_prompt(prompt: str, last_prompt: str | None) -> RateLimitResult:
    """Check prompt length and reject identical-to-previous prompts."""
    if len(prompt) > MAX_PROMPT_LENGTH:
        return RateLimitResult(
            allowed=False,
            reason=f"Your message is too long (max {MAX_PROMPT_LENGTH} characters). Please shorten it.",
        )
    if last_prompt is not None and prompt.strip() == last_prompt.strip():
        return RateLimitResult(
            allowed=False,
            reason="You just sent that same message. Try rephrasing or asking something new.",
        )
    return RateLimitResult(allowed=True)


def check_session_cap(session_count: int) -> RateLimitResult:
    """Check whether the session has reached its per-session message cap."""
    if session_count >= SESSION_MESSAGE_CAP:
        return RateLimitResult(
            allowed=False,
            reason=(
                f"You've reached the per-session limit of {SESSION_MESSAGE_CAP} messages. "
                "Refresh the page to start a new session."
            ),
        )
    return RateLimitResult(allowed=True)


def _load_global_counter() -> dict:
    """Load the global counter file, returning a fresh dict if missing or corrupt."""
    today = date.today().isoformat()
    if not os.path.exists(GLOBAL_COUNTER_FILE):
        return {"date": today, "count": 0}
    try:
        with open(GLOBAL_COUNTER_FILE, "r") as f:
            data = json.load(f)
        if data.get("date") != today:
            return {"date": today, "count": 0}
        if not isinstance(data.get("count"), int):
            return {"date": today, "count": 0}
        return data
    except (json.JSONDecodeError, OSError):
        return {"date": today, "count": 0}


def _save_global_counter(data: dict) -> None:
    os.makedirs(os.path.dirname(GLOBAL_COUNTER_FILE), exist_ok=True)
    try:
        with open(GLOBAL_COUNTER_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass  # Best-effort; don't crash the app on counter write failure


def check_global_cap() -> RateLimitResult:
    """Check whether the global daily cap has been reached."""
    data = _load_global_counter()
    if data["count"] >= GLOBAL_DAILY_CAP:
        return RateLimitResult(
            allowed=False,
            reason="The daily usage limit for this app has been reached. Please try again tomorrow.",
        )
    return RateLimitResult(allowed=True)


def record_request() -> None:
    """Increment the global counter. Call only after a successful LLM call."""
    data = _load_global_counter()
    data["count"] += 1
    _save_global_counter(data)
```

- [ ] **Step 2: Commit**

```bash
git add src/rate_limiter.py
git commit -m "feat(sculptor): add rate limiter module with session and global caps"
```

---

### Task 3: Rewrite Sculptor page sidebar and chat handler

**Files:**
- Modify: `pages/5_Playlist_Sculptor.py`

- [ ] **Step 1: Update imports**

Replace the top import block:

```python
import streamlit as st
st.set_page_config(page_title="Playlist Sculptor | PlayPlay.qr8", layout="wide")

import spotipy
import pandas as pd
from src.ingestion import load_from_cache
from src.auth import SpotifyAuthManager
from src.llm_providers import get_available_providers, get_chat_model
from src.agent import generate_response, apply_proposal, compute_comparison, SculptorProposal
```

With:

```python
import streamlit as st
st.set_page_config(page_title="Playlist Sculptor | PlayPlay.qr8", layout="wide")

import spotipy
import pandas as pd
from src.ingestion import load_from_cache
from src.auth import SpotifyAuthManager
from src.llm_providers import get_chat_model
from src.agent import generate_response, apply_proposal, compute_comparison, SculptorProposal
from src.rate_limiter import (
    SESSION_MESSAGE_CAP,
    validate_prompt,
    check_session_cap,
    check_global_cap,
    record_request,
)
```

- [ ] **Step 2: Add `sculptor_session_count` to the reset-on-playlist-change block**

In the existing reset block, add `"sculptor_session_count": 0` initialization:

```python
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
```

- [ ] **Step 3: Replace the entire sidebar LLM configuration block**

Replace the existing `with st.sidebar:` block (the one starting with `st.subheader("LLM Configuration")` and ending with `st.caption(f"🎵 {playlist_name}")`) with:

```python
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
        st.caption("Powered by **Llama 4 Scout** via Groq")
        remaining = SESSION_MESSAGE_CAP - st.session_state.get("sculptor_session_count", 0)
        st.caption(f"Messages remaining this session: **{remaining}/{SESSION_MESSAGE_CAP}**")

    st.divider()
    st.caption(f"🎵 {playlist_name}")
```

- [ ] **Step 4: Replace the chat input handler with rate-limited version**

Replace the block starting with `if prompt := st.chat_input(...)` and ending with `st.error(f"Error generating response: {e}")` with:

```python
if prompt := st.chat_input("Ask about the playlist or tell me how to reshape it...", disabled=not llm_ready):
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
```

- [ ] **Step 5: Verify file compiles**

Run: `source .venv/bin/activate && python -m py_compile pages/5_Playlist_Sculptor.py`
Expected: no output (clean compile)

- [ ] **Step 6: Commit**

```bash
git add pages/5_Playlist_Sculptor.py
git commit -m "feat(sculptor): Groq-only with rate limits and input validation"
```

---

### Task 4: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update dependencies**

Replace:
```
langchain-openai>=1.0.0
langchain-google-genai>=4.0.0
langchain-community>=0.4.0
```

With:
```
langchain-groq>=1.0.0
```

Keep `langchain-core>=1.0.0` as-is.

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): replace openai/google/community with langchain-groq"
```

---

### Task 5: Update `.streamlit/secrets.toml.example` and CLAUDE.md

**Files:**
- Check: `.streamlit/secrets.toml.example` (if it exists)
- Modify: `CLAUDE.md`

- [ ] **Step 1: Check if secrets.toml.example exists**

Run: `ls .streamlit/secrets.toml.example 2>/dev/null`

If it exists, update it to replace openai/google keys with `groq_api_key`. If not, skip this step.

- [ ] **Step 2: Update CLAUDE.md secrets section**

In the `## Secrets / Credentials` section, replace:
```toml
spotify_client_id = "..."
spotify_client_secret = "..."
spotify_redirect_uri = "http://127.0.0.1:8501"
# Optional for Sculptor page:
openai_api_key = "..."
google_api_key = "..."
```

With:
```toml
spotify_client_id = "..."
spotify_client_secret = "..."
spotify_redirect_uri = "http://127.0.0.1:8501"
# Required for Sculptor page:
groq_api_key = "..."
```

Also update the Sculptor description in the Architecture section to reflect Groq-only with rate limiting. Replace the paragraph starting with "**Sculptor** (`pages/5_Playlist_Sculptor.py`..." with something reflecting Groq-only + rate limiter.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md .streamlit/secrets.toml.example 2>/dev/null
git commit -m "docs: update secrets and architecture for Groq-only Sculptor"
```

---

### Task 6: End-to-end verification

- [ ] **Step 1: Verify all modified files compile**

```bash
source .venv/bin/activate
python -m py_compile src/llm_providers.py src/rate_limiter.py pages/5_Playlist_Sculptor.py
echo "OK"
```

Expected: `OK`

- [ ] **Step 2: Verify rate_limiter smoke test**

```bash
source .venv/bin/activate
python -c "
from src.rate_limiter import validate_prompt, check_session_cap, check_global_cap, record_request, SESSION_MESSAGE_CAP

# Length cap
r = validate_prompt('x' * 501, None)
assert not r.allowed and 'too long' in r.reason, f'length check failed: {r}'

# Duplicate
r = validate_prompt('hello', 'hello')
assert not r.allowed and 'same message' in r.reason, f'dup check failed: {r}'

# Session cap
r = check_session_cap(SESSION_MESSAGE_CAP)
assert not r.allowed and 'per-session' in r.reason, f'session check failed: {r}'

# Global cap (should pass on fresh install)
r = check_global_cap()
assert r.allowed, f'global check failed: {r}'

print('rate_limiter OK')
"
```

Expected: `rate_limiter OK`
