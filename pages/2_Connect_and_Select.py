import streamlit as st
st.set_page_config(page_title="Connect & Select | PlayPlay.qr8", layout="wide")

import spotipy
from src.auth import SpotifyAuthManager, get_spotify_credentials

st.title("Connect Spotify and Select a Playlist")


def _secrets_configured():
    try:
        return bool(
            st.secrets.get("spotify_client_id")
            and st.secrets.get("spotify_client_secret")
        )
    except FileNotFoundError:
        return False


# --- Handle OAuth callback (code in query params) ---
query_code = st.query_params.get("code")
if query_code and "token_info" not in st.session_state:
    client_id, client_secret, redirect_uri = get_spotify_credentials()
    if client_id and client_secret and redirect_uri:
        try:
            token_info = SpotifyAuthManager.exchange_code(
                query_code, client_id, client_secret, redirect_uri
            )
            st.session_state["token_info"] = token_info
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Failed to exchange auth code: {e}")

# --- Check for existing valid token ---
token_info = st.session_state.get("token_info") or SpotifyAuthManager.read_token_cache()
authenticated = False

if token_info and SpotifyAuthManager.is_token_valid(token_info):
    st.session_state["token_info"] = token_info
    authenticated = True
elif token_info and not SpotifyAuthManager.is_token_valid(token_info):
    # Try refreshing
    client_id, client_secret, redirect_uri = get_spotify_credentials()
    if client_id and client_secret and redirect_uri:
        try:
            token_info = SpotifyAuthManager.refresh_token(
                token_info, client_id, client_secret, redirect_uri
            )
            st.session_state["token_info"] = token_info
            authenticated = True
        except Exception:
            pass  # Fall through to login flow

# --- Authenticated: show playlist selector ---
if authenticated:
    token_info = st.session_state["token_info"]
    sp = spotipy.Spotify(auth=token_info["access_token"])
    # Cache playlists to avoid hitting Spotify API on every rerun
    if "user_playlists" not in st.session_state:
        all_playlists = []
        results = sp.current_user_playlists(limit=50)
        all_playlists.extend(results["items"])
        while results["next"]:
            results = sp.next(results)
            all_playlists.extend(results["items"])
        st.session_state["user_playlists"] = all_playlists
    all_playlists = st.session_state["user_playlists"]

    playlist_options = {
        pl["id"]: f"{pl['name']} ({pl['tracks']['total']} tracks)"
        for pl in all_playlists
    }
    playlist_ids = list(playlist_options.keys())
    null_option = "__none__"

    current_id = st.session_state.get("selected_playlist_id", null_option)
    default_index = (
        playlist_ids.index(current_id) + 1
        if current_id in playlist_ids
        else 0
    )

    selected_id = st.selectbox(
        "Select a playlist you want to inspect",
        [null_option] + playlist_ids,
        format_func=lambda x: "-- Select a playlist --" if x == null_option else playlist_options[x],
        index=default_index,
    )

    if selected_id != null_option:
        for pl in all_playlists:
            if pl["id"] == selected_id:
                st.session_state["selected_playlist"] = pl["name"]
                st.session_state["selected_playlist_id"] = pl["id"]
                break
        st.success(f"Connected! Selected playlist: {st.session_state['selected_playlist']}")
        st.page_link("pages/3_Playlist_Breakdown.py", label="Continue to Playlist Breakdown →", icon="📊")

    if st.button("Disconnect"):
        SpotifyAuthManager.disconnect(st.session_state)
        st.rerun()

# --- Not authenticated: show login flow ---
else:
    has_secrets = _secrets_configured()

    if not has_secrets:
        st.subheader("Enter Spotify Credentials")
        st.caption(
            "Tip: add credentials to `.streamlit/secrets.toml` to skip this step."
        )
        st.session_state["manual_client_id"] = st.text_input(
            "Spotify Client ID", value=st.session_state.get("manual_client_id", "")
        )
        st.session_state["manual_client_secret"] = st.text_input(
            "Spotify Client Secret",
            type="password",
            value=st.session_state.get("manual_client_secret", ""),
        )
        st.session_state["manual_redirect_uri"] = st.text_input(
            "Redirect URI",
            value=st.session_state.get("manual_redirect_uri", "http://127.0.0.1:8501"),
        )

    client_id, client_secret, redirect_uri = get_spotify_credentials()

    if client_id and client_secret and redirect_uri:
        auth_url = SpotifyAuthManager.get_auth_url(
            client_id, client_secret, redirect_uri
        )
        st.link_button("Connect with Spotify", auth_url)
    elif has_secrets:
        st.error("Spotify credentials in secrets.toml are incomplete.")
