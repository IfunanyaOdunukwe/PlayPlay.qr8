import streamlit as st
import spotipy
import pandas as pd
from src.ingestion import fetch_playlist_data, load_from_cache
from src.auth import SpotifyAuthManager

st.title("Eat This Playlist")

# Display selected playlist
playlist_name = st.session_state.get('selected_playlist')
playlist_id = st.session_state.get('selected_playlist_id')

if not playlist_name or not playlist_id:
    st.error("No playlist selected. Please go back and select a playlist.")
    st.stop()

st.write(f"**Selected Playlist:** {playlist_name}")
st.write(f"**Playlist ID:** {playlist_id}")

# Button to trigger ingestion
if st.button("Eat This Playlist"):
    try:
        # Try to load from cache first
        df = load_from_cache(playlist_id)
        if df is not None:
            st.success(f"Loaded {len(df)} tracks from cache.")
        else:
            # Authenticate and fetch fresh data
            token_info = st.session_state.get('token_info')
            if not token_info or not SpotifyAuthManager.is_token_valid(token_info):
                st.error("Spotify authentication expired. Please reconnect.")
                st.stop()
            sp = spotipy.Spotify(auth=token_info['access_token'])
            # Optionally, get Reccobeats API key from session or input
            reccobeats_api_key = st.session_state.get('reccobeats_api_key')
            df = fetch_playlist_data(sp, playlist_id, force_refresh=True, reccobeats_api_key=reccobeats_api_key)
            if df is not None and not df.empty:
                st.success(f"Fetched and cached {len(df)} tracks.")
            else:
                st.warning("No tracks found or ingestion failed.")
        # Display DataFrame
        if df is not None and not df.empty:
            st.dataframe(df)
    except Exception as e:
        st.error(f"Error during ingestion: {e}")

