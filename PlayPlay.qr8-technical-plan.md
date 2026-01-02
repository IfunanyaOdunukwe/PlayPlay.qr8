
***

# PlayPlay.qr8: Technical Implementation Plan

## 1. Project Overview
**PlayPlay.qr8** is a self-hostable Python/Streamlit tool for advanced Spotify playlist analysis and curation. It allows users to:
1.  **Visualize** playlist metrics (Audio Features).
2.  **Detect Outliers** using statistical models (Z-Score & Isolation Forest).
3.  **Filter by Vibe** using Vector Math (Similarity to a model song).
4.  **Filter by Natural Language** using LLMs to translate intent into mathematical thresholds.

## 2. Tech Stack
*   **Language:** Python 3.10+
*   **Web Framework:** Streamlit
*   **Spotify Client:** `spotipy`
*   **Data Manipulation:** `pandas`
*   **Math/ML:** `scikit-learn` (IsolationForest, MinMaxScaler), `scipy` (stats)
*   **LLM Integration:** `langchain` or direct `requests` (OpenAI-compatible endpoints for Ollama/Gemini).

## 3. Directory Structure
```text
PlayPlay.qr8/
├── .streamlit/
│   └── secrets.toml         # Spotify API Keys & LLM Credentials
├── cache/                   # Local JSON storage for playlist data
├── src/
│   ├── __init__.py
│   ├── auth.py              # Spotify OAuth2Manager logic
│   ├── ingestion.py         # Fetch tracks, audio features, batching, caching
│   ├── analysis.py          # Z-score, Isolation Forest, Visualization
│   ├── curator.py           # Vector math, Similarity calculations
│   └── agent.py             # LLM Prompting and JSON parsing
├── app.py                   # Main Streamlit UI entry point
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## 4. Module Implementation Details

### A. Data Ingestion (`src/ingestion.py`)
**Goal:** Fetch playlist data efficiently and respect API rate limits.

1.  **Authentication:**
    *   Use `spotipy.oauth2.SpotifyOAuth`.
    *   **Scopes:** `playlist-read-private`, `playlist-modify-public`, `playlist-modify-private`.
2.  **Fetching Logic:**
    *   Get Tracks: `sp.playlist_items()` (handle pagination).
    *   Get Audio Features: `sp.audio_features()`.
    *   **CRITICAL:** `audio_features` accepts max 100 IDs. You must batch the track IDs.
3.  **Data Structure (Pandas DataFrame):**
    *   **Metadata:** `id`, `name`, `artist`, `album`, `uri`, `cover_url`.
    *   **Features:** `danceability`, `energy`, `valence`, `tempo`, `loudness`, `acousticness`, `instrumentalness`, `liveness`, `speechiness`.
4.  **Caching Strategy:**
    *   Generate a filename hash or use Playlist ID: `cache/{playlist_id}.json`.
    *   On load: Check if file exists.
    *   If yes: Load JSON -> DataFrame.
    *   If no: Fetch API -> Save JSON -> DataFrame.

### B. Module A: The Inspector (`src/analysis.py`)
**Goal:** Identify outliers and visualize the dataset.

1.  **Z-Score Outlier Detection (Parametric):**
    *   Iterate through specific columns: `['tempo', 'energy', 'valence', 'danceability']`.
    *   Calculate Z-score: $z = (x - \mu) / \sigma$.
    *   **Logic:** Flag if $|z| > 2$ (Standard deviation threshold).
    *   Return: A list of song IDs and the specific reason (e.g., "Tempo extremely high").

2.  **Isolation Forest (Unsupervised):**
    *   Use `sklearn.ensemble.IsolationForest`.
    *   **Inputs:** All audio features.
    *   **Contamination:** `auto` or `0.05` (assuming ~5% outliers).
    *   Return: Binary flag (-1 for outlier, 1 for inlier).

### C. Module B: The Curator (`src/curator.py`)
**Goal:** Filter based on similarity to a "Model Song".

1.  **Normalization (Crucial):**
    *   Tempo (0-200) overwhelms Danceability (0-1).
    *   Apply `sklearn.preprocessing.MinMaxScaler` to all feature columns before math operations.
2.  **Distance Calculation:**
    *   User selects `model_track_id`.
    *   Get vector $V_{model}$.
    *   Calculate **Cosine Similarity** against all other vectors $V_{n}$.
3.  **Filtering Modes:**
    *   **Strict:** Filter where similarity > 0.95.
    *   **Loose:** Filter where similarity > 0.80.

### D. Module C: The Agent (`src/agent.py`)
**Goal:** Translate natural language into Pandas filters.

1.  **System Prompt:**
    ```text
    You are a Spotify Data Assistant.
    User Input: Description of a vibe.
    Task: Convert the vibe into numerical thresholds for Spotify Audio Features.
    Available Features:
    - valence (0.0 sad - 1.0 happy)
    - energy (0.0 low - 1.0 high)
    - danceability, acousticness, instrumentalness, loudness, tempo.

    Output format: JSON ONLY.
    Example: {"filters": [{"column": "valence", "op": ">", "val": 0.6}, {"column": "tempo", "op": ">", "val": 120}]}
    ```
2.  **Processing:**
    *   Parse JSON response.
    *   Iteratively apply filters to the DataFrame:
    ```python
    # Pseudo-code
    for f in filters:
        if f['op'] == '>': df = df[df[f['column']] > f['val']]
        elif f['op'] == '<': df = df[df[f['column']] < f['val']]
    ```

## 5. UI/UX Workflow (`app.py`)

The UI relies heavily on **Streamlit Session State** to hold the data between button clicks.

1.  **State Management:**
    *   `st.session_state['df_master']`: The original playlist.
    *   `st.session_state['df_working']`: The filtered version (currently being edited).
    *   `st.session_state['removal_list']`: IDs marked for removal.

2.  **The Staging Area (Safety Mechanism):**
    *   **Never delete immediately.**
    *   When an outlier is detected or LLM filters are applied, add those songs to a "Proposed Removal" list.
    *   Display this list in a `st.dataframe` with a checkbox column `Keep?`.
    *   **Final Action:** "Create New Playlist" button. This takes `df_master` minus `removal_list` and pushes to Spotify.

## 6. Setup & Deployment

**`requirements.txt`**
```text
streamlit
spotipy
pandas
scikit-learn
scipy
python-dotenv
langchain
openai # (Optional, depending on LLM choice)
```

**`docker-compose.yml`**
```yaml
version: '3.8'
services:
  PlayPlay.qr8:
    build: .
    ports:
      - "8501:8501"
    env_file:
      - .env
    volumes:
      - ./cache:/app/cache
```