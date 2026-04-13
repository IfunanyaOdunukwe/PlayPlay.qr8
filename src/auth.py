from __future__ import annotations

import hashlib
import secrets
import time
from urllib.parse import urlsplit, urlunsplit

import requests
from requests.auth import HTTPBasicAuth
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth

SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"
DEFAULT_SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8501"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
PENDING_SPOTIFY_AUTH_TTL_SECONDS = 600
INVALID_SPOTIFY_CREDENTIALS_MESSAGE = (
    "Spotify rejected that Client ID / Client Secret. Check both values and try again."
)
_PENDING_SPOTIFY_AUTH: dict[str, dict] = {}


class NoTokenCacheHandler(CacheHandler):
    """Disable Spotipy's default file cache for stateless deployments."""

    def get_cached_token(self) -> None:
        return None

    def save_token_to_cache(self, token_info: dict) -> None:
        return None


def normalize_redirect_uri(redirect_uri: str | None) -> str | None:
    """Strip query params and fragments from a redirect URI."""
    if not redirect_uri:
        return None

    cleaned = redirect_uri.strip()
    if not cleaned:
        return None

    parsed = urlsplit(cleaned)
    if not parsed.scheme or not parsed.netloc:
        return cleaned

    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "", "", ""))


def canonicalize_local_redirect_uri(redirect_uri: str | None) -> str | None:
    """Normalize local development redirect URIs to 127.0.0.1."""
    normalized_url = normalize_redirect_uri(redirect_uri)
    if not normalized_url:
        return None

    parsed = urlsplit(normalized_url)
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"localhost", "127.0.0.1"}:
        return normalized_url

    port = f":{parsed.port}" if parsed.port else ""
    return urlunsplit((parsed.scheme, f"127.0.0.1{port}", parsed.path or "", "", ""))


def _cleanup_pending_spotify_auth() -> None:
    now = int(time.time())
    expired_states = [
        state
        for state, context in _PENDING_SPOTIFY_AUTH.items()
        if context.get("expires_at", 0) <= now
    ]
    for state in expired_states:
        _PENDING_SPOTIFY_AUTH.pop(state, None)


def create_pending_spotify_auth(client_id: str, client_secret: str, redirect_uri: str) -> str:
    """Store credentials briefly so OAuth callbacks can complete in a new session."""
    _cleanup_pending_spotify_auth()
    state = secrets.token_urlsafe(24)
    _PENDING_SPOTIFY_AUTH[state] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": canonicalize_local_redirect_uri(redirect_uri),
        "expires_at": int(time.time()) + PENDING_SPOTIFY_AUTH_TTL_SECONDS,
    }
    return state


def get_pending_spotify_auth(state: str | None) -> dict | None:
    """Retrieve a short-lived Spotify auth context by OAuth state."""
    if not state:
        return None

    _cleanup_pending_spotify_auth()
    context = _PENDING_SPOTIFY_AUTH.get(state)
    if not context:
        return None

    return {
        "client_id": context["client_id"],
        "client_secret": context["client_secret"],
        "redirect_uri": context["redirect_uri"],
    }


def clear_pending_spotify_auth(state: str | None) -> None:
    """Delete a short-lived Spotify auth context."""
    if state:
        _PENDING_SPOTIFY_AUTH.pop(state, None)


def get_runtime_redirect_uri() -> str:
    """Use the app root URL as the default redirect URI."""
    import streamlit as st

    try:
        current_url = st.context.url
    except AttributeError:
        current_url = None

    normalized_url = canonicalize_local_redirect_uri(current_url)
    if not normalized_url:
        return DEFAULT_SPOTIFY_REDIRECT_URI

    parsed = urlsplit(normalized_url)
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


class SpotifyAuthManager:
    """
    Utility class for Spotify OAuth authentication without persistent token caching.
    """

    @staticmethod
    def is_token_valid(token_info: dict | None) -> bool:
        return bool(
            token_info
            and token_info.get("access_token")
            and token_info.get('expires_at', 0) > int(time.time())
        )

    @classmethod
    def create_oauth(cls, client_id: str, client_secret: str, redirect_uri: str, state: str | None = None) -> SpotifyOAuth:
        """Build a SpotifyOAuth instance with the given credentials."""
        return SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            state=state,
            scope=SCOPES,
            cache_handler=NoTokenCacheHandler(),
            open_browser=False,
        )

    @classmethod
    def get_auth_url(cls, client_id: str, client_secret: str, redirect_uri: str, state: str | None = None) -> str:
        """Return the Spotify authorization URL the user should visit."""
        oauth = cls.create_oauth(client_id, client_secret, redirect_uri, state=state)
        return oauth.get_authorize_url()

    @classmethod
    def exchange_code(cls, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        """Exchange an authorization code for a token."""
        oauth = cls.create_oauth(client_id, client_secret, redirect_uri)
        token_info = oauth.get_access_token(code, as_dict=True, check_cache=False)
        return token_info

    @classmethod
    def refresh_token(cls, token_info: dict, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        oauth = cls.create_oauth(client_id, client_secret, redirect_uri)
        refreshed = oauth.refresh_access_token(token_info['refresh_token'])
        return refreshed

    @classmethod
    def disconnect(cls, st_session_state: dict | None = None) -> None:
        if st_session_state and "token_info" in st_session_state:
            del st_session_state["token_info"]


def get_spotify_credentials(auth_state: str | None = None) -> tuple[str | None, str | None, str | None]:
    """Resolve Spotify credentials from manual session input.

    Returns (client_id, client_secret, redirect_uri) or (None, None, None).
    """
    import streamlit as st

    if auth_state:
        pending_auth = get_pending_spotify_auth(auth_state)
        if pending_auth:
            return (
                pending_auth["client_id"],
                pending_auth["client_secret"],
                pending_auth["redirect_uri"],
            )

    return (
        st.session_state.get("manual_client_id"),
        st.session_state.get("manual_client_secret"),
        canonicalize_local_redirect_uri(st.session_state.get("manual_redirect_uri"))
        or get_runtime_redirect_uri(),
    )


def get_spotify_credentials_signature(client_id: str | None, client_secret: str | None) -> str | None:
    """Create a stable fingerprint for the currently entered Spotify credentials."""
    if not client_id or not client_secret:
        return None

    raw = f"{client_id}\0{client_secret}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_spotify_credentials(client_id: str | None, client_secret: str | None) -> tuple[bool, str | None]:
    """Validate the Spotify app credentials before starting OAuth."""
    if not client_id or not client_secret:
        return False, "Enter both your Spotify Client ID and Client Secret."

    try:
        response = requests.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(client_id, client_secret),
            timeout=10,
        )
    except requests.RequestException:
        return False, "Spotify could not be reached. Check your connection and try again."

    if response.ok:
        return True, None

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code in {400, 401} or payload.get("error") == "invalid_client":
        return False, INVALID_SPOTIFY_CREDENTIALS_MESSAGE

    details = payload.get("error_description") or payload.get("error")
    if details:
        return False, f"Spotify could not validate those credentials: {details}."

    return False, f"Spotify could not validate those credentials (HTTP {response.status_code})."


def format_spotify_auth_error(error: Exception) -> str:
    """Turn Spotipy auth exceptions into user-facing login guidance."""
    message = str(error).lower()

    if "invalid_client" in message or "invalid client" in message:
        return INVALID_SPOTIFY_CREDENTIALS_MESSAGE

    if "redirect_uri" in message or "invalid_grant" in message:
        return (
            "Spotify couldn't finish the login. Make sure the app home URL shown on this page "
            "is added to your Spotify app settings as a Redirect URI."
        )

    return (
        "Spotify couldn't finish the login. Check your Client ID, Client Secret, "
        "and registered redirect URI, then try again."
    )

