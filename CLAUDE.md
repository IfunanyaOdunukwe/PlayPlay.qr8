# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
source .venv/bin/activate
streamlit run Welcome.py
```

Runs on port 8501. Install dependencies with `pip install -r requirements.txt`. No test suite exists.

## Secrets / Credentials

Spotify credentials go in `.streamlit/secrets.toml` (gitignored):

```toml
spotify_client_id = "..."
spotify_client_secret = "..."
spotify_redirect_uri = "http://127.0.0.1:8501"
# Required for Sculptor page:
groq_api_key = "..."
```

Spotify credentials fall back to manual text-input entry if secrets.toml is missing. The Sculptor page is disabled with an error banner if `groq_api_key` is not configured on the server.

Bundled demo playlists are local CSV files under `demo_playlists/` and are available without Spotify login. Spotify credentials are needed for the authenticated flow, which supports both the user's own library and pasted public Spotify playlist URLs, as well as Spotify export.

## Architecture

**Streamlit multi-page app** — `Welcome.py` is the entry point/landing page. Pages in `pages/` are auto-discovered and ordered by filename numeric prefix.

### Data Flow (sequential through pages)

1. **Auth** (`src/auth.py`): `SpotifyAuthManager` handles OAuth2 via spotipy for the personal-account path only. Scopes: `playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private`. Token cached in `.cache` file at project root (gitignored) and in `st.session_state['token_info']`. OAuth callback uses `?code=` query param captured via `st.query_params`.

2. **Connect & Select** (`pages/2_Connect_and_Select.py` + `src/demo.py`): Users choose between a local CSV demo flow and the Spotify OAuth flow. The authenticated Spotify flow supports both playlists from the user's library and pasted public playlist URLs. Stores selected playlist in `st.session_state['selected_playlist']`, `st.session_state['selected_playlist_id']`, `st.session_state['selected_playlist_source']`, and `st.session_state['selected_playlist_reference']`.

3. **Ingest** (`src/ingestion.py` + `pages/3_Playlist_Breakdown.py` + `src/demo.py`): Demo playlists load from CSV files in `demo_playlists/`. Authenticated Spotify playlists fetch track metadata via Spotify API and audio features via **Reccobeats API** (`api.reccobeats.com/v1/audio-features`), not Spotify's deprecated audio_features endpoint. Public playlist URLs in the authenticated flow first try the normal Spotify playlist API and fall back to scraping the public playlist web page for track links if Spotify returns 404. Reccobeats response wraps features in a `content` array; track IDs are extracted from the `href` field. Batch size is 40. Remote playlist data is cached as JSON in `cache/{playlist_id}.json`.

4. **Visualize** (`pages/4_Vibe_Inspector.py`): Cache-only reads — no API calls. Renders statistical summary metrics, per-track radar charts (Plotly `Scatterpolar`), valence-vs-energy scatter by mode, and tempo distribution (histogram/violin toggle).

5. **Sculptor** (`pages/5_Playlist_Sculptor.py` + `src/agent.py` + `src/llm_providers.py` + `src/rate_limiter.py`): AI chat interface for reshaping playlists via natural language, backed exclusively by Groq (`meta-llama/llama-4-scout-17b-16e-instruct`) via LangChain. The server-side `groq_api_key` is the only supported credential — users never enter a key. Uses a propose-then-approve workflow: LLM generates a structured `SculptorProposal` (Pydantic model with remove/reorder/highlight operations), user sees before/after comparison, then approves or rejects. Spotify export is available only for user-authenticated playlists; local demo playlists are read-only. Rate limiting (`src/rate_limiter.py`) enforces a 500-char prompt cap, rejects duplicate back-to-back prompts, caps each session at 20 messages, and caps app-wide usage at 500 calls/day via a JSON counter in `cache/sculptor_global_counter.json`.

### Key Patterns

- **LLM structured output with fallback**: `src/agent.py` first tries `llm.with_structured_output(SculptorProposal)`, then falls back to JSON parsing from raw LLM text. This two-tier approach handles providers that don't support structured output.
- **Session state as inter-page bus**: All shared state flows through `st.session_state`. Key keys: `token_info`, `selected_playlist`/`selected_playlist_id`/`selected_playlist_source`/`selected_playlist_reference`, `developer_mode`, `sculptor_df_original`/`sculptor_df_working`, `sculptor_messages`, `sculptor_pending_proposal`.
- **Approve/reject via rerun flags**: Sculptor uses `sculptor_do_approve`/`sculptor_do_reject` boolean flags processed at the top of each Streamlit rerun cycle, since button callbacks trigger full page reruns.

## Conventions

- Plotly charts: `template="simple_white"`, color map `Major=#4C78A8`, `Minor=#F58518`, `Other=#72B7B2`.
- Audio features (0–1 scale) displayed as `st.column_config.ProgressColumn` in dataframes.
- Tempo normalized to [0,1] for radar charts by dividing by playlist max BPM.
- Cache files are JSON in `cache/`; the directory is gitignored.
- `developer_mode` toggle (sidebar) shows/hides internal columns (id, uri, spotify_id, etc.) in the Breakdown table.
