# Groq-Only Sculptor Design

**Date:** 2026-04-10
**Goal:** Replace the multi-provider LLM selector with a single Groq-backed Sculptor, with rate limiting and input validation suitable for a public-but-obscure hosted deployment.

## Threat Model

**Level B — public-but-obscure.** The app will be shared publicly (portfolio, social posts) but is not expected to attract determined adversaries. The realistic threats are:
- Casual users spamming the chat
- Bots or curious strangers trying to use the app as a free LLM proxy
- Accidental runaway loops in normal use

We are **not** protecting against determined attackers extracting the API key, coordinated scraping, or sophisticated jailbreaks.

## Design Decisions

| Concern | Decision |
|---|---|
| Access control | Spotify OAuth is the only gate — no allowlist, no password |
| Rate limits | Per-session message cap (20) + global daily cap (500) |
| Input validation | 500-char length cap + reject identical back-to-back prompts |
| Observability | None — rely on Groq dashboard |
| User feedback | Clear in-chat messages when any limit is hit |

## Architecture Changes

### 1. `src/llm_providers.py` — simplified to ~15 lines
Remove the `PROVIDERS` list, `get_available_providers()`, and multi-provider dispatch. Single function returning a `ChatGroq` instance configured for `meta-llama/llama-4-scout-17b-16e-instruct` at temperature 0.4.

### 2. `src/rate_limiter.py` — new module
Pure functions (no Streamlit imports) with a `RateLimitResult` dataclass for structured pass/fail. Public API:
- `validate_prompt(prompt, last_prompt) -> RateLimitResult`
- `check_session_cap(session_count) -> RateLimitResult`
- `check_global_cap() -> RateLimitResult`
- `record_request() -> None`

**Constants:**
```python
MAX_PROMPT_LENGTH = 500
SESSION_MESSAGE_CAP = 20
GLOBAL_DAILY_CAP = 500
GLOBAL_COUNTER_FILE = "cache/sculptor_global_counter.json"
```

**Global counter storage:** Single JSON file with `{"date": "YYYY-MM-DD", "count": N}`. Resets when date changes. Read-modify-write without locking — acceptable because worst case is losing a count or two, corruption guarded by try/except-and-reset.

**User-facing rejection messages:**
| Trigger | Message |
|---|---|
| Prompt > 500 chars | "Your message is too long (max 500 characters). Please shorten it." |
| Duplicate of previous prompt | "You just sent that same message. Try rephrasing or asking something new." |
| Session cap hit | "You've reached the per-session limit of 20 messages. Refresh the page to start a new session." |
| Global cap hit | "The daily usage limit for this app has been reached. Please try again tomorrow." |

### 3. `pages/5_Playlist_Sculptor.py` — sidebar rewrite and chat input guarding
- Sidebar removes provider radio, API key input, model name expander
- Reads `st.secrets["groq_api_key"]`; if missing, disables Sculptor with an error message
- Shows "Messages remaining this session: N/20" caption in sidebar
- Chat handler calls `validate_prompt → check_session_cap → check_global_cap` in order, short-circuits on first failure
- Blocked prompts still appear in chat history as user message + assistant rejection
- Session count and global count increment **only on successful Groq calls**
- Groq-specific error handling: 429 / rate_limit → friendly "Groq is rate-limiting the app" message; quota errors → "app has hit its Groq usage quota"

### 4. Session state additions
- `sculptor_session_count` (int) — reset when playlist changes (already part of the existing reset block)

### 5. `requirements.txt`
- Add: `langchain-groq`
- Remove: `langchain-openai`, `langchain-google-genai`, `langchain-community`

### 6. `.streamlit/secrets.toml` contract
`groq_api_key = "..."` is now **required** for the Sculptor to function. Fallback to user-entered keys is removed entirely.

## Out of Scope

- Per-Spotify-user tracking (requires persistent user database)
- Structured logging or metrics
- Prompt-injection defenses beyond what the existing propose-then-approve workflow provides
- Atomic/locked file writes for the global counter
- Environment variable fallback for the Groq key

## Self-Review Notes

- No TBDs or placeholders
- Rate limit values (20 session / 500 global / 500 char) are documented as constants, easy to tune later
- The known gap (session count is client-side, global counter is not locked) is called out explicitly in the design
- Scope is focused on one feature, implementable in a single plan
