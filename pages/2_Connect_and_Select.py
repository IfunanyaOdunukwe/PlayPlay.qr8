import streamlit as st
import spotipy
from src.auth import SpotifyAuthManager  # Applied: Modularized auth logic as per "Code Reusability #1"

try:
    st.title("Connect Spotify and Select a Playlist")

    # Try to load token from .cache first
    token_info = SpotifyAuthManager.read_token_cache()
    authenticated = False
    if token_info and SpotifyAuthManager.is_token_valid(token_info):
        st.session_state['token_info'] = token_info
        authenticated = True
    elif 'token_info' in st.session_state and SpotifyAuthManager.is_token_valid(st.session_state['token_info']):
        authenticated = True

    if authenticated:
        token_info = st.session_state['token_info']
        sp = spotipy.Spotify(auth=token_info['access_token'])
        playlists = sp.current_user_playlists()
        playlist_options = [pl['name'] for pl in playlists['items']]
        # Insert a null/default option at the top to force selection
        playlist_options_with_null = ["-- Select a playlist --"] + playlist_options
        # Use session state for default selection if available, else null
        default_playlist = st.session_state.get('selected_playlist', "-- Select a playlist --")
        selected_playlist = st.selectbox(
            "Select a playlist you want to inspect",
            playlist_options_with_null,
            index=playlist_options_with_null.index(default_playlist) if default_playlist in playlist_options_with_null else 0
        )
        # Only update session state if a real playlist is selected
        if selected_playlist != "-- Select a playlist --" and st.session_state.get('selected_playlist') != selected_playlist:
            for pl in playlists['items']:
                if pl['name'] == selected_playlist:
                    st.session_state['selected_playlist'] = pl['name']
                    st.session_state['selected_playlist_id'] = pl['id']
                    break  # Applied: Store both name and ID only on change for robustness
        # Only show success if a real playlist is selected
        if selected_playlist != "-- Select a playlist --":
            st.success(f"Connected! Selected playlist: {selected_playlist}")
        if st.button("Disconnect"):
            SpotifyAuthManager.disconnect(st.session_state)
            st.rerun()
    else:
        # Always show connect prompt if not authenticated or token is expired
        st.subheader("Connect with New Spotify Credentials")
        client_id = st.text_input("Spotify Client ID", key="connect_client_id")
        client_secret = st.text_input("Spotify Client Secret", type="password", key="connect_client_secret")
        redirect_uri = st.text_input("Redirect URI", value="http://127.0.0.1:3000", key="connect_redirect_uri")
        if st.button("Connect"):
            if client_id and client_secret and redirect_uri:
                try:
                    from spotipy.oauth2 import SpotifyOAuth  # Only import here to avoid unused import if not needed
                    auth_manager = SpotifyOAuth(
                        client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=redirect_uri,
                        scope="playlist-read-private playlist-read-collaborative",
                        cache_path=SpotifyAuthManager.get_cache_path()
                    )
                    token_info = auth_manager.get_cached_token()
                    if not token_info:
                        auth_manager.get_access_token()
                        token_info = auth_manager.get_cached_token()
                    st.session_state['token_info'] = token_info
                    SpotifyAuthManager.write_token_cache(token_info)
                    st.rerun()  # Rerun to hide inputs and show disconnect
                except Exception as e:
                    st.error(f"Failed to connect: {e}")
            else:
                st.warning("Please fill in all fields.")
except Exception as page_error:
    st.error(f"Page failed to load: {page_error}")
# Applied: Only connect prompt is shown when token is expired, as per "Code Structure #1" and "Code Cleanliness #2"
# Applied: Removed 'Go to Ingestion' button and navigation as per 'Code Cleanliness #2' and 'Code Structure #1'.
