# PlayPlay.qr8

A Streamlit app for analyzing and curating playlists. Try local CSV demo playlists without Spotify, or log into Spotify to analyze your own private/public playlists and any public Spotify playlist URL.

## Features

- **Connect & Select** — Choose between local CSV demo playlists and an authenticated Spotify flow for your library or pasted public playlist URLs
- **Playlist Breakdown** — View track metadata and audio features in an interactive table
- **Vibe Inspector** — Statistical summaries, radar charts, valence-vs-energy scatter plots, and tempo distribution
- **Playlist Sculptor** — Chat with an AI to reshape your playlist (remove tracks, reorder, highlight), then push the result back to Spotify as a new playlist

## Prerequisites

- Python 3.11+
- A [Spotify Developer](https://developer.spotify.com/dashboard) app with:
  - A Client ID and Client Secret
  - Your app URL added as a Redirect URI. Use `http://127.0.0.1:8501` locally or your deployed Streamlit Cloud URL when hosted.

Spotify credentials are required to browse your own library, analyze pasted public playlist URLs, or push a sculpted playlist back to Spotify. The demo flow uses bundled CSV playlists and does not call the Spotify API.

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

#### Spotify Developer setup

To use your own Spotify login, create a Spotify app first:

1. Open the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create an app.
2. On the app page, open Settings or Edit Settings.
3. Copy the Client ID and use View client secret to reveal the Client Secret.
4. Add your app home URL to Redirect URIs. For local development, use `http://127.0.0.1:8501` unless you changed the port. For Streamlit Cloud, use your deployed app root URL.
5. Save the app settings.
6. Open Connect & Select in the app and paste the Client ID and Client Secret into the Spotify form. No Spotify values are required in `.streamlit/secrets.toml`.

Spotify's official setup references:

- [Getting started with the Web API](https://developer.spotify.com/documentation/web-api/tutorials/getting-started)
- [Apps](https://developer.spotify.com/documentation/web-api/concepts/apps)

The Connect page shows the exact app home URL to register as the Redirect URI, validates the Client ID and Client Secret before OAuth starts, and keeps Spotify tokens in session only.

### Optional: Server API key for Playlist Sculptor

If you want to use the Sculptor page, add your Groq API key to `.streamlit/secrets.toml`:

```toml
groq_api_key = "..."
```

Without `groq_api_key`, the Sculptor page stays disabled.

## Run

```bash
streamlit run Welcome.py
```

Open **http://127.0.0.1:8501** in your browser.

## How it works

1. **Choose a flow** — Stay in local demo mode with CSV sample playlists, or authenticate via Spotify OAuth
2. **Select** — Choose a demo CSV playlist, select a playlist from your Spotify account, or paste a public Spotify playlist URL after logging in
3. **Ingest** — On the Playlist Breakdown page, load demo CSV data or fetch Spotify track metadata and Reccobeats audio features
4. **Explore** — Switch to the Vibe Inspector to see charts and stats
5. **Sculpt** — Use natural language on the Playlist Sculptor page to reshape your playlist; Spotify export is available only for playlists loaded from your own account

## Project structure

```
Welcome.py                     # Entry point / landing page
pages/
  2_Connect_and_Select.py    # Demo-vs-Spotify chooser + playlist picker
  3_Playlist_Breakdown.py    # Demo CSV loading or Spotify/Reccobeats ingestion + feature table
  4_Vibe_Inspector.py        # Visualizations and stats
  5_Playlist_Sculptor.py     # AI chat interface for playlist curation
src/
  auth.py                    # Spotify OAuth token management
  demo.py                    # Demo CSV loading and public playlist helper logic
  ingestion.py               # Spotify API + Reccobeats audio features
  agent.py                   # LLM-powered sculptor agent
  llm_providers.py           # Multi-provider LLM factory
```
