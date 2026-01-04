import streamlit as st
import spotipy
import pandas as pd
from src.ingestion import fetch_playlist_data  # Applied: Singular import as per "General Code Quality Guidelines #1"
from src.auth import SpotifyAuthManager

st.title("Ingest this playlist")

# Check authentication and playlist selection prerequisites
missing_token = 'token_info' not in st.session_state or not SpotifyAuthManager.is_token_valid(st.session_state['token_info'])
missing_playlist = 'selected_playlist_id' not in st.session_state or 'selected_playlist' not in st.session_state

if missing_token or missing_playlist:
    st.warning("Select a playlist first!")
    if st.button("Go to Playlist Selection"):
        try:
            st.switch_page('pages/2_Connect_and_Select.py')  # Streamlit 1.22+
        except Exception:
            st.info("Please use the sidebar to navigate to 'Link Your Spotify Account and Select a Playlist'.")
    st.stop()

sp = spotipy.Spotify(auth=st.session_state['token_info']['access_token'])
playlist_id = st.session_state['selected_playlist_id']
playlist_name = st.session_state['selected_playlist']

# Process playlist and cache results
if st.button("Process Playlist Data"):
    with st.spinner(f"Ingesting playlist '{playlist_name}' data..."):
        try:
            # Applied: Caching and merging audio features as per requirements
            df = fetch_playlist_data(sp, playlist_id)
            if df is not None and not df.empty:
                st.success(f"Ingestion complete! Showing {len(df)} tracks.")
                st.session_state['playlist_df'] = df
                st.session_state['can_inspect_song'] = True
                st.dataframe(df.head())
            else:
                st.warning("No data found or ingestion failed. Please ensure the playlist is not empty and try again.")
                st.session_state['can_inspect_song'] = False
        except Exception as e:
            st.error(f"Exception during ingestion: {e}")
            st.session_state['can_inspect_song'] = False

# Dropdown to select a song and inspect audio features
if st.session_state.get('can_inspect_song', False) and 'playlist_df' in st.session_state:
    df = st.session_state['playlist_df']
    # Identify track name and id columns
    name_col = None
    id_col = None
    for c in df.columns:
        if c.lower() in ["track_name", "name", "title"]:
            name_col = c
        if c.lower() in ["track_id", "id", "spotify_id"]:
            id_col = c
    if name_col and id_col:
        track_names = df[name_col].tolist()
        track_ids = df[id_col].tolist()
        selected_index = st.selectbox("Select a song to inspect audio features", range(len(track_names)), format_func=lambda i: track_names[i])
        selected_track_id = track_ids[selected_index]
        selected_track_name = track_names[selected_index]
        if st.button("Show Audio Features"):
            features_row = df[df[id_col] == selected_track_id]
            if not features_row.empty:
                # Only show feature columns that are present and not all NaN for this row
                feature_cols = [col for col in df.columns if col in [
                    'danceability', 'energy', 'key', 'loudness', 'mode',
                    'speechiness', 'acousticness', 'instrumentalness',
                    'liveness', 'valence', 'tempo', 'time_signature']
                    and not pd.isna(features_row.iloc[0][col])]
                if feature_cols:
                    feature_table = features_row[feature_cols].T
                    feature_table.columns = [selected_track_name]
                    st.table(feature_table)
                else:
                    st.warning("No audio features found for this track in the playlist data.")
            else:
                st.warning("Selected track not found in playlist data.")
    else:
        st.warning(f"Expected columns for track name and id not found. Columns found: {df.columns.tolist()}")

if st.button("Back to Playlist Selection"):
    try:
        st.switch_page('pages/2_Connect_and_Select.py')
    except Exception:
        st.info("Please use the sidebar to navigate to 'Link Your Spotify Account and Select a Playlist'.")
