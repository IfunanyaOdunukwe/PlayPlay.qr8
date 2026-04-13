import streamlit as st
st.set_page_config(page_title="Playlist Breakdown | PlayPlay.qr8", layout="wide")

import spotipy
from src.audio_features import AUDIO_FEATURE_DEFINITIONS, AUDIO_FEATURE_HELP, KEY_LABELS, MODE_LABELS
from src.auth import SpotifyAuthManager
from src.demo import fetch_spotify_playlist_data_with_fallback
from src.demo import get_demo_playlist_df
from src.ingestion import load_cache_metadata, load_from_cache
from src.session_state import get_selected_playlist_snapshot
from src.theme import apply_spotify_theme, render_nav_button, render_playlist_indicator

apply_spotify_theme()
st.title("")

# Developer mode toggle controls visibility of hidden columns in the table
with st.sidebar:
    developer_mode = st.toggle(
        "Developer mode",
        value=st.session_state.get("developer_mode", False),
        help="Show internal columns in the table.",
    )
st.session_state["developer_mode"] = developer_mode

selected_playlist = get_selected_playlist_snapshot(st.session_state)

if not selected_playlist:
    st.warning("No playlist selected.")
    render_nav_button(
        "pages/2_Connect_and_Select.py",
        "Open Connect & Select →",
        icon="🔗",
        key="breakdown_open_connect",
    )
    st.stop()

playlist_name = selected_playlist["name"]
playlist_id = selected_playlist["id"]
playlist_source = selected_playlist.get("source") or "spotify"
playlist_track_total = (selected_playlist.get("tracks") or {}).get("total")

render_playlist_indicator(
    "Current Playlist",
    playlist_name,
    note="Using local demo CSV data. No Spotify login needed." if playlist_source == "demo" else None,
)
st.write(
    "Load the playlist, review the track table, then open the Vibe Inspector."
)
if st.session_state.get("developer_mode", False):
    st.caption(f"Playlist ID: {playlist_id}")


# --- DataFrame display persistence logic ---
show_df_key = f"show_playlist_df_{playlist_id}"
last_playlist_key = "last_playlist_id_for_df"

if playlist_source == "demo":
    load_pressed = st.button("Load Data")
    force_refresh = False
else:
    col_btn, col_refresh = st.columns([1, 1])
    with col_btn:
        load_pressed = st.button("Load Data")
    with col_refresh:
        force_refresh = st.toggle("Force refresh from Spotify", value=False, help="Fetch fresh data even if cache exists.")

# If playlist changes, reset the flag
if st.session_state.get(last_playlist_key) != playlist_id:
    st.session_state[show_df_key] = False
    st.session_state[last_playlist_key] = playlist_id

if load_pressed:
    st.session_state[show_df_key] = True

show_df = st.session_state.get(show_df_key, False)


def render_load_notices(df, metadata=None, loaded_from_cache=False):
    loaded_count = len(df)
    if playlist_source == "demo" or loaded_count == 0:
        return

    if metadata and metadata.get("tracks_missing_audio_features"):
        st.warning(
            f"Reccobeats did not return audio features for {metadata['tracks_missing_audio_features']} track(s), "
            f"so they were excluded from analysis."
        )

    unavailable_playlist_items = metadata.get("unavailable_playlist_items") if metadata else None
    if unavailable_playlist_items:
        st.info(
            f"{unavailable_playlist_items} playlist item(s) could not be loaded from Spotify and were also excluded. "
            "This can happen with unavailable or local tracks."
        )

    if (not metadata or metadata.get("tracks_missing_audio_features") is None) and playlist_track_total and loaded_count < playlist_track_total:
        st.info(
            f"Spotify reports {playlist_track_total} playlist items, but only {loaded_count} are available for analysis."
        )

if show_df or load_pressed:
    try:
        if playlist_source == "demo":
            with st.spinner("Loading demo playlist..."):
                df = get_demo_playlist_df(playlist_id)
            cache_metadata = None
            st.success(f"Loaded {len(df)} demo tracks.")
        else:
            df = None
            loaded_from_cache = False
            cache_metadata = None
            if not force_refresh:
                df = load_from_cache(playlist_id)
            if df is not None:
                loaded_from_cache = True
                cache_metadata = load_cache_metadata(playlist_id)
                st.success(f"Loaded {len(df)} tracks with audio features from cache.")
            else:
                token_info = st.session_state.get('token_info')
                if not token_info or not SpotifyAuthManager.is_token_valid(token_info):
                    st.error("Spotify authentication expired. Please reconnect.")
                    st.stop()
                sp = spotipy.Spotify(auth=token_info['access_token'])
                reccobeats_api_key = st.session_state.get('reccobeats_api_key')
                with st.spinner("Fetching tracks and audio features..."):
                    df = fetch_spotify_playlist_data_with_fallback(
                        sp,
                        playlist_id,
                        force_refresh=True,
                        reccobeats_api_key=reccobeats_api_key,
                    )
                cache_metadata = load_cache_metadata(playlist_id)
                if df is not None and not df.empty:
                    st.success(f"Fetched and cached {len(df)} tracks with audio features.")
                else:
                    if cache_metadata and cache_metadata.get("tracks_missing_audio_features"):
                        st.warning("No tracks with audio features were available for this playlist.")
                    else:
                        st.warning("No tracks found or ingestion failed.")
        if df is not None and not df.empty:
            st.session_state[f"_cached_df_{playlist_id}"] = df
            render_load_notices(
                df,
                metadata=cache_metadata,
                loaded_from_cache=playlist_source != "demo" and loaded_from_cache,
            )
            st.markdown("### Track Breakdown")
            st.caption("Track metadata and audio features for the selected playlist.")
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
                    help=AUDIO_FEATURE_DEFINITIONS["tempo"],
                )
            if "loudness" in df.columns:
                column_config["loudness"] = st.column_config.NumberColumn(
                    label="loudness (dB)",
                    help=AUDIO_FEATURE_DEFINITIONS["loudness"],
                )
            if "key" in df_display.columns:
                column_config["key"] = st.column_config.TextColumn(
                    label="key",
                    help=AUDIO_FEATURE_DEFINITIONS["key"],
                )
            if "mode" in df_display.columns:
                column_config["mode"] = st.column_config.TextColumn(
                    label="mode",
                    help=AUDIO_FEATURE_DEFINITIONS["mode"],
                )
            if "time_signature" in df_display.columns:
                column_config["time_signature"] = st.column_config.NumberColumn(
                    label="time_signature",
                    help=AUDIO_FEATURE_DEFINITIONS["time_signature"],
                )

            if "image_url" in df_display.columns:
                column_config["image_url"] = st.column_config.ImageColumn(
                    label="Cover",
                    help="Album or track cover art.",
                    width="small",
                )

            with st.container(border=True):
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    column_config=column_config if column_config else None,
                )

            render_nav_button(
                "pages/4_Vibe_Inspector.py",
                "Open Inspector →",
                icon="🎛️",
                key="breakdown_open_inspector",
            )
    except Exception as e:
        st.error(f"Error during ingestion: {e}")
