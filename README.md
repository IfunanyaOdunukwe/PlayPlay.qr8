# PlayPlay.qr8

A Streamlit app for analyzing and curating your Spotify playlists. Connect your Spotify account, ingest playlist data with audio features, visualize your playlist's "vibe", and reshape it with an AI-powered chat interface.

## Features

- **Connect & Select** — Authenticate with Spotify OAuth and pick a playlist
- **Playlist Breakdown** — View track metadata and audio features in an interactive table
- **Vibe Inspector** — Statistical summaries, radar charts, valence-vs-energy scatter plots, and tempo distribution
- **Playlist Sculptor** — Chat with an AI to reshape your playlist (remove tracks, reorder, highlight), then push the result back to Spotify as a new playlist

## Prerequisites

- Python 3.11+
- A [Spotify Developer](https://developer.spotify.com/dashboard) app with:
  - A Client ID and Client Secret
  - `http://127.0.0.1:8501` added as a Redirect URI

## Setup

```bash
# Clone the repo
git clone https://github.com/<your-username>/PlayPlay.qr8.git
cd PlayPlay.qr8

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Spotify credentials

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` and fill in your `spotify_client_id` and `spotify_client_secret`.

Alternatively, you can enter credentials manually in the app's Connect page.

### Optional: LLM for Playlist Sculptor

The Sculptor page supports three LLM providers. Add the relevant API key to `secrets.toml` or enter it in the app sidebar:

| Provider | Key in secrets.toml | Notes |
|----------|-------------------|-------|
| OpenAI | `openai_api_key` | Uses GPT-4o |
| Google Gemini | `google_api_key` | Uses Gemini Flash |
| Ollama | *(none needed)* | Requires [Ollama](https://ollama.com) running locally |

## Run

```bash
streamlit run Welcome.py
```

Open **http://127.0.0.1:8501** in your browser.

## How it works

1. **Connect** — Authenticate via Spotify OAuth on the Connect & Select page
2. **Select** — Pick a playlist from your library
3. **Ingest** — On the Playlist Breakdown page, click "Ingest" to fetch track metadata and audio features (sourced from the [Reccobeats API](https://reccobeats.com))
4. **Explore** — Switch to the Vibe Inspector to see charts and stats
5. **Sculpt** — Use natural language on the Playlist Sculptor page to reshape your playlist, then push the result to Spotify

## Project structure

```
Welcome.py                     # Entry point / landing page
pages/
  2_Connect_and_Select.py    # Spotify OAuth + playlist picker
  3_Playlist_Breakdown.py    # Data ingestion + feature table
  4_Vibe_Inspector.py        # Visualizations and stats
  5_Playlist_Sculptor.py     # AI chat interface for playlist curation
src/
  auth.py                    # Spotify OAuth token management
  ingestion.py               # Spotify API + Reccobeats audio features
  agent.py                   # LLM-powered sculptor agent
  llm_providers.py           # Multi-provider LLM factory
```
