import streamlit as st
import spotipy
from src.ingestion import fetch_playlist_data, load_from_cache
from src.auth import SpotifyAuthManager

st.title("Playlist Breakdown")

# Developer mode toggle controls visibility of hidden columns in the table
with st.sidebar:
    developer_mode = st.toggle(
        "Developer mode",
        value=st.session_state.get("developer_mode", False),
        help="When on, include hidden/internal columns in the table.",
    )
st.session_state["developer_mode"] = developer_mode

AUDIO_FEATURE_HELP = {
    "acousticness": "Acousticness (0–100%): confidence the track is acoustic. Higher = more acoustic.",
    "danceability": "Danceability (0–100%): how suitable the track is for dancing. Higher = more danceable.",
    "energy": "Energy (0–100%): perceived intensity and activity. Higher = more energetic.",
    "instrumentalness": "Instrumentalness (0–100%): likelihood the track has no vocals. >50% ≈ instrumental.",
    "liveness": "Liveness (0–100%): likelihood of a live audience. >80% ≈ live recording.",
    "speechiness": "Speechiness (0–100%): proportion of spoken words. Higher = more speech-like.",
    "valence": "Valence (0–100%): musical positivity. Higher = happier/more uplifting.",
}

KEY_LABELS = {
    -1: "(no key)",
    0: "C",
    1: "C♯/D♭",
    2: "D",
    3: "D♯/E♭",
    4: "E",
    5: "F",
    6: "F♯/G♭",
    7: "G",
    8: "G♯/A♭",
    9: "A",
    10: "A♯/B♭",
    11: "B",
}

MODE_LABELS = {
    0: "Minor",
    1: "Major",
}

playlist_name = st.session_state.get('selected_playlist')
playlist_id = st.session_state.get('selected_playlist_id')

if not playlist_name or not playlist_id:
    st.error("No playlist selected. Please go back and select a playlist.")
    st.stop()

st.write(f"**Selected Playlist:** {playlist_name}")
st.write(f"**Playlist ID:** {playlist_id}")


# --- DataFrame display persistence logic ---
show_df_key = f"show_playlist_df_{playlist_id}"
last_playlist_key = "last_playlist_id_for_df"

eat_pressed = st.button("Ingest")

# If playlist changes, reset the flag
if st.session_state.get(last_playlist_key) != playlist_id:
    st.session_state[show_df_key] = False
    st.session_state[last_playlist_key] = playlist_id

if eat_pressed:
    st.session_state[show_df_key] = True

show_df = st.session_state.get(show_df_key, False)

if show_df or eat_pressed:
    try:
        df = load_from_cache(playlist_id)
        if df is not None:
            st.success(f"Loaded {len(df)} tracks from cache.")
        else:
            token_info = st.session_state.get('token_info')
            if not token_info or not SpotifyAuthManager.is_token_valid(token_info):
                st.error("Spotify authentication expired. Please reconnect.")
                st.stop()
            sp = spotipy.Spotify(auth=token_info['access_token'])
            reccobeats_api_key = st.session_state.get('reccobeats_api_key')
            df = fetch_playlist_data(sp, playlist_id, force_refresh=True, reccobeats_api_key=reccobeats_api_key)
            if df is not None and not df.empty:
                st.success(f"Fetched and cached {len(df)} tracks.")
            else:
                st.warning("No tracks found or ingestion failed.")
        if df is not None and not df.empty:
            df_display = df.copy()
            hidden_cols = [
                "id",
                "album",
                "uri",
                "external_url",
                "spotify_id",
            ]
            existing_hidden = [col for col in hidden_cols if col in df_display.columns]
            # Only drop hidden columns when developer mode is OFF
            if not st.session_state.get("developer_mode", False):
                if existing_hidden:
                    df_display = df_display.drop(columns=existing_hidden)

            if "key" in df_display.columns:
                df_display["key"] = df_display["key"].map(KEY_LABELS).fillna(df_display["key"].astype(str))
            if "mode" in df_display.columns:
                df_display["mode"] = df_display["mode"].map(MODE_LABELS).fillna(df_display["mode"].astype(str))
            if "name" in df_display.columns:
                df_display = df_display.rename(columns={"name": "track_name"})

            column_config = {}

            for feature, help_text in AUDIO_FEATURE_HELP.items():
                if feature in df.columns:
                    column_config[feature] = st.column_config.ProgressColumn(
                        label=feature,
                        help=help_text,
                        min_value=0.0,
                        max_value=1.0,
                    )

            if "tempo" in df.columns:
                column_config["tempo"] = st.column_config.NumberColumn(
                    label="tempo (BPM)",
                    help="Estimated tempo of the track in beats per minute (BPM).",
                )
            if "loudness" in df.columns:
                column_config["loudness"] = st.column_config.NumberColumn(
                    label="loudness (dB)",
                    help="Average loudness of the track in decibels (dB), typically between -60 and 0.",
                )

            if "image_url" in df_display.columns:
                column_config["image_url"] = st.column_config.ImageColumn(
                    label="Cover",
                    help="Album or track cover art.",
                    width="small",
                )

            st.dataframe(
                df_display,
                use_container_width=True,
                column_config=column_config if column_config else None,
            )
            # (Hide Playlist Table button removed)
    except Exception as e:
        st.error(f"Error during ingestion: {e}")
