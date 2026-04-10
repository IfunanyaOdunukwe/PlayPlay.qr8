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
# Optional for Sculptor page:
openai_api_key = "..."
google_api_key = "..."
```

The app falls back to manual text-input entry if secrets.toml is missing.

## Architecture

**Streamlit multi-page app** — `Welcome.py` is the entry point/landing page. Pages in `pages/` are auto-discovered and ordered by filename numeric prefix.

### Data Flow (sequential through pages)

1. **Auth** (`src/auth.py`): `SpotifyAuthManager` handles OAuth2 via spotipy. Scopes: `playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private`. Token cached in `.cache` file at project root (gitignored) and in `st.session_state['token_info']`. OAuth callback uses `?code=` query param captured via `st.query_params`.

2. **Connect & Select** (`pages/2_Connect_and_Select.py`): Resolves credentials (secrets.toml → manual input). Stores selected playlist in `st.session_state['selected_playlist']` and `st.session_state['selected_playlist_id']`.

3. **Ingest** (`src/ingestion.py` + `pages/3_Playlist_Breakdown.py`): Fetches track metadata via Spotify API and audio features via **Reccobeats API** (`api.reccobeats.com/v1/audio-features`), not Spotify's deprecated audio_features endpoint. Reccobeats response wraps features in a `content` array; track IDs are extracted from the `href` field. Batch size is 40. Data cached as JSON in `cache/{playlist_id}.json`.

4. **Visualize** (`pages/4_Vibe_Inspector.py`): Cache-only reads — no API calls. Renders statistical summary metrics, per-track radar charts (Plotly `Scatterpolar`), valence-vs-energy scatter by mode, and tempo distribution (histogram/violin toggle).

5. **Sculptor** (`pages/5_Playlist_Sculptor.py` + `src/agent.py` + `src/llm_providers.py`): AI chat interface for reshaping playlists via natural language. Multi-provider LLM support (OpenAI, Google Gemini, Ollama local) via LangChain — providers are lazy-imported so only the selected one needs to be installed. Uses a propose-then-approve workflow: LLM generates a structured `SculptorProposal` (Pydantic model with remove/reorder/highlight operations), user sees before/after comparison, then approves or rejects. Can push the sculpted result to Spotify as a new playlist.

### Key Patterns

- **LLM structured output with fallback**: `src/agent.py` first tries `llm.with_structured_output(SculptorProposal)`, then falls back to JSON parsing from raw LLM text. This two-tier approach handles providers that don't support structured output.
- **Session state as inter-page bus**: All shared state flows through `st.session_state`. Key keys: `token_info`, `selected_playlist`/`selected_playlist_id`, `developer_mode`, `sculptor_df_original`/`sculptor_df_working`, `sculptor_messages`, `sculptor_pending_proposal`.
- **Approve/reject via rerun flags**: Sculptor uses `sculptor_do_approve`/`sculptor_do_reject` boolean flags processed at the top of each Streamlit rerun cycle, since button callbacks trigger full page reruns.

## Conventions

- Plotly charts: `template="simple_white"`, color map `Major=#4C78A8`, `Minor=#F58518`, `Other=#72B7B2`.
- Audio features (0–1 scale) displayed as `st.column_config.ProgressColumn` in dataframes.
- Tempo normalized to [0,1] for radar charts by dividing by playlist max BPM.
- Cache files are JSON in `cache/`; the directory is gitignored.
- `developer_mode` toggle (sidebar) shows/hides internal columns (id, uri, spotify_id, etc.) in the Breakdown table.
