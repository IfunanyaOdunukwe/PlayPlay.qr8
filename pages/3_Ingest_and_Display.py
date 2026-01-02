import streamlit as st
import spotipy
import pandas as pd
from src.ingestion import fetch_playlist_data  # Applied: Singular import as per "General Code Quality Guidelines #1"
from src.auth import SpotifyAuthManager

st.title("Ingest and Display Playlist Data")

# Check authentication and playlist selection prerequisites
missing_token = 'token_info' not in st.session_state or not SpotifyAuthManager.is_token_valid(st.session_state['token_info'])
missing_playlist = 'selected_playlist_id' not in st.session_state or 'selected_playlist' not in st.session_state

if missing_token or missing_playlist:
    st.warning("You must connect your Spotify account and select a playlist before ingesting data.")
    if st.button("Go to Playlist Selection"):
        try:
            st.switch_page('pages/2_Connect_and_Select.py')  # Streamlit 1.22+
        except Exception:
            st.info("Please use the sidebar to navigate to 'Link Your Spotify Account and Select a Playlist'.")
    st.stop()

sp = spotipy.Spotify(auth=st.session_state['token_info']['access_token'])
playlist_id = st.session_state['selected_playlist_id']
playlist_name = st.session_state['selected_playlist']

# Optional: Remove debug info for production, or keep for troubleshooting
# st.info(f"Debug: Playlist Name: {playlist_name}, Playlist ID: {playlist_id}")

if st.button("Ingest Playlist"):
    with st.spinner(f"Ingesting playlist '{playlist_name}' data..."):
        try:
            df = fetch_playlist_data(sp, playlist_id)
            if df is not None and not df.empty:
                st.success(f"Ingestion complete! Showing {len(df)} tracks.")
                st.dataframe(df)
            else:
                st.warning("No data found or ingestion failed. Please ensure the playlist is not empty and try again.")
        except Exception as e:
            st.error(f"Exception during ingestion: {e}")

if st.button("Back to Playlist Selection"):
    try:
        st.switch_page('pages/2_Connect_and_Select.py')
    except Exception:
        st.info("Please use the sidebar to navigate to 'Link Your Spotify Account and Select a Playlist'.")
