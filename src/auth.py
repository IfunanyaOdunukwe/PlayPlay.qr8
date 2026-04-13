import os
import json
import time
from spotipy.oauth2 import SpotifyOAuth

SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"
DEFAULT_SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8501"


class SpotifyAuthManager:
    """
    Utility class for Spotify OAuth authentication and token cache management.
    """
    CACHE_FILENAME = ".cache"

    @classmethod
    def get_cache_path(cls):
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), cls.CACHE_FILENAME)

    @staticmethod
    def is_token_valid(token_info):
        return token_info and token_info.get('expires_at', 0) > int(time.time())

    @classmethod
    def read_token_cache(cls):
        cache_path = cls.get_cache_path()
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                try:
                    return json.load(f)
                except Exception:
                    return None
        return None

    @classmethod
    def write_token_cache(cls, token_info):
        cache_path = cls.get_cache_path()
        with open(cache_path, "w") as f:
            json.dump(token_info, f)

    @classmethod
    def create_oauth(cls, client_id, client_secret, redirect_uri):
        """Build a SpotifyOAuth instance with the given credentials."""
        return SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=SCOPES,
            cache_path=cls.get_cache_path(),
            open_browser=False,
        )

    @classmethod
    def get_auth_url(cls, client_id, client_secret, redirect_uri):
        """Return the Spotify authorization URL the user should visit."""
        oauth = cls.create_oauth(client_id, client_secret, redirect_uri)
        return oauth.get_authorize_url()

    @classmethod
    def exchange_code(cls, code, client_id, client_secret, redirect_uri):
        """Exchange an authorization code for a token and cache it."""
        oauth = cls.create_oauth(client_id, client_secret, redirect_uri)
        token_info = oauth.get_access_token(code, as_dict=True, check_cache=False)
        cls.write_token_cache(token_info)
        return token_info

    @classmethod
    def refresh_token(cls, token_info, client_id, client_secret, redirect_uri):
        oauth = cls.create_oauth(client_id, client_secret, redirect_uri)
        refreshed = oauth.refresh_access_token(token_info['refresh_token'])
        cls.write_token_cache(refreshed)
        return refreshed

    @classmethod
    def disconnect(cls, st_session_state=None):
        cache_path = cls.get_cache_path()
        if st_session_state and 'token_info' in st_session_state:
            del st_session_state['token_info']
        if os.path.exists(cache_path):
            os.remove(cache_path)


def get_spotify_credentials():
    """Resolve Spotify credentials from Streamlit secrets or manual session input.

    Returns (client_id, client_secret, redirect_uri) or (None, None, None).
    """
    import streamlit as st

    try:
        return (
            st.secrets["spotify_client_id"],
            st.secrets["spotify_client_secret"],
            st.secrets.get("spotify_redirect_uri", DEFAULT_SPOTIFY_REDIRECT_URI),
        )
    except (KeyError, FileNotFoundError):
        return (
            st.session_state.get("manual_client_id"),
            st.session_state.get("manual_client_secret"),
            st.session_state.get("manual_redirect_uri"),
        )

