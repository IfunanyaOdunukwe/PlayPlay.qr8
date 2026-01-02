import os
import json
import time
from spotipy.oauth2 import SpotifyOAuth

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
    def refresh_token(cls, token_info, client_id, client_secret, redirect_uri):
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-read-private playlist-read-collaborative",
            cache_path=cls.get_cache_path()
        )
        refreshed = auth_manager.refresh_access_token(token_info['refresh_token'])
        cls.write_token_cache(refreshed)
        return refreshed

    @classmethod
    def disconnect(cls, st_session_state=None):
        cache_path = cls.get_cache_path()
        if st_session_state and 'token_info' in st_session_state:
            del st_session_state['token_info']
        if os.path.exists(cache_path):
            os.remove(cache_path)

