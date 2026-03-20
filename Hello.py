import streamlit as st
st.set_page_config(page_title="PlayPlay.qr8", layout="wide")

from src.auth import SpotifyAuthManager, get_spotify_credentials

# Handle OAuth callback — Spotify redirects to the root URL with ?code=
query_code = st.query_params.get("code")
if query_code and "token_info" not in st.session_state:
    creds = get_spotify_credentials()
    if all(creds):
        try:
            token_info = SpotifyAuthManager.exchange_code(query_code, *creds)
            st.session_state["token_info"] = token_info
            st.query_params.clear()
            st.switch_page("pages/2_Connect_and_Select.py")
        except Exception as e:
            st.error(f"Failed to exchange auth code: {e}")

st.title("Welcome to PlayPlay.qr8!")
st.write("""
This app helps you analyze and curate your Spotify playlists using advanced metrics and AI.\n\nNavigate to the next page to connect your Spotify account and get started!
""")