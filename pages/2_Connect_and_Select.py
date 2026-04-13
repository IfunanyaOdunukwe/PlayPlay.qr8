import streamlit as st
st.set_page_config(page_title="Connect & Select | PlayPlay.qr8", layout="wide")

import spotipy
from src.auth import DEFAULT_SPOTIFY_REDIRECT_URI, SpotifyAuthManager, get_spotify_credentials
from src.demo import get_demo_playlist, get_demo_playlists, get_public_playlist
from src.theme import apply_spotify_theme, render_nav_button, render_playlist_indicator

apply_spotify_theme()

st.title("Choose a Playlist")
st.write(
    "Use a demo playlist or connect Spotify to choose from your library or a public URL."
)

DEMO_MODE = "demo"
SPOTIFY_MODE = "spotify"
PLAYLIST_STATE_KEYS = [
    "selected_playlist",
    "selected_playlist_id",
    "selected_playlist_source",
    "selected_playlist_description",
    "selected_playlist_owner",
    "selected_playlist_track_total",
    "selected_playlist_reference",
]
CONNECT_MODE_WIDGET_KEY = "connect_mode_widget"
PUBLIC_PLAYLIST_FORM_KEY = "spotify_public_playlist_form"
LIBRARY_SEARCH_WIDGET_KEY = "spotify_library_search"
LIBRARY_FILTER_WIDGET_KEY = "spotify_library_filter"
LIBRARY_FILTER_OPTIONS = [
    "All playlists",
    "Owned by you",
    "Saved from others",
    "Collaborative",
]


def clear_selected_playlist():
    for key in PLAYLIST_STATE_KEYS:
        st.session_state.pop(key, None)


def get_playlist_owner_label(playlist: dict) -> str | None:
    owner = playlist.get("owner")
    if isinstance(owner, dict):
        return owner.get("display_name") or owner.get("id")
    return owner


def get_playlist_owner_id(playlist: dict) -> str | None:
    owner = playlist.get("owner")
    if isinstance(owner, dict):
        return owner.get("id")
    return None


def format_spotify_playlist_option(playlist: dict) -> str:
    owner_label = get_playlist_owner_label(playlist) or "Unknown owner"
    track_total = playlist.get("tracks", {}).get("total") or 0
    return f"{playlist['name']} - {owner_label} ({track_total} tracks)"


def filter_library_playlists(
    playlists: list[dict],
    search_query: str,
    selected_filter: str,
    current_user_id: str | None,
) -> list[dict]:
    normalized_query = (search_query or "").strip().lower()
    filtered_playlists = []

    for playlist in playlists:
        owner_id = get_playlist_owner_id(playlist)

        if selected_filter == "Owned by you" and current_user_id and owner_id != current_user_id:
            continue
        if selected_filter == "Saved from others" and current_user_id and owner_id == current_user_id:
            continue
        if selected_filter == "Collaborative" and not playlist.get("collaborative"):
            continue

        if normalized_query:
            searchable_text = " ".join(
                [
                    playlist.get("name", ""),
                    get_playlist_owner_label(playlist) or "",
                ]
            ).lower()
            if normalized_query not in searchable_text:
                continue

        filtered_playlists.append(playlist)

    return filtered_playlists


def set_selected_playlist(playlist: dict, source: str, reference: str | None = None):
    st.session_state["selected_playlist"] = playlist["name"]
    st.session_state["selected_playlist_id"] = playlist["id"]
    st.session_state["selected_playlist_source"] = source
    st.session_state["selected_playlist_description"] = playlist.get("description")
    st.session_state["selected_playlist_owner"] = get_playlist_owner_label(playlist)
    st.session_state["selected_playlist_track_total"] = playlist.get("tracks", {}).get("total")
    st.session_state["selected_playlist_reference"] = reference


def get_selected_playlist_snapshot() -> dict | None:
    playlist_id = st.session_state.get("selected_playlist_id")
    playlist_name = st.session_state.get("selected_playlist")
    if not playlist_id or not playlist_name:
        return None
    return {
        "id": playlist_id,
        "name": playlist_name,
        "description": st.session_state.get("selected_playlist_description"),
        "owner": st.session_state.get("selected_playlist_owner"),
        "tracks": {"total": st.session_state.get("selected_playlist_track_total")},
    }


def render_playlist_ready_state(playlist: dict, ready_label: str):
    render_playlist_indicator(
        ready_label,
        playlist["name"],
        note=playlist.get("description"),
    )


def disconnect_spotify():
    SpotifyAuthManager.disconnect(st.session_state)
    st.session_state.pop("user_playlists", None)
    st.session_state.pop("spotify_user_profile", None)
    if st.session_state.get("selected_playlist_source") == SPOTIFY_MODE:
        clear_selected_playlist()


def sync_connect_mode():
    new_mode = st.session_state[CONNECT_MODE_WIDGET_KEY]
    old_mode = st.session_state.get("connect_mode")
    if old_mode != new_mode:
        st.session_state["connect_mode"] = new_mode
        if old_mode is not None:
            clear_selected_playlist()


def _secrets_configured():
    try:
        return bool(
            st.secrets.get("spotify_client_id")
            and st.secrets.get("spotify_client_secret")
        )
    except FileNotFoundError:
        return False


def render_spotify_setup_help():
    with st.expander("How to set up Spotify login"):
        st.markdown(
            f"""
            1. Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
            2. Open the app settings, copy the **Client ID**, and use **View client secret** to reveal the **Client Secret**.
            3. In **Redirect URIs**, add `{DEFAULT_SPOTIFY_REDIRECT_URI}` if you run this app on the default local port. If you run Streamlit on another port, use that exact app URL instead.
            4. Save the app, then paste the values below or add them to `.streamlit/secrets.toml`.

            Official guides:
            [Getting Started](https://developer.spotify.com/documentation/web-api/tutorials/getting-started)
            and [Apps](https://developer.spotify.com/documentation/web-api/concepts/apps)
            """
        )
        st.code(
            "\n".join(
                [
                    'spotify_client_id = "..."',
                    'spotify_client_secret = "..."',
                    f'spotify_redirect_uri = "{DEFAULT_SPOTIFY_REDIRECT_URI}"',
                ]
            ),
            language="toml",
        )


# --- Handle OAuth callback (code in query params) ---
query_code = st.query_params.get("code")
if query_code and "token_info" not in st.session_state:
    st.session_state["connect_mode"] = SPOTIFY_MODE
    st.session_state[CONNECT_MODE_WIDGET_KEY] = SPOTIFY_MODE
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

default_mode = st.session_state.get("connect_mode")
if default_mode not in {DEMO_MODE, SPOTIFY_MODE}:
    default_mode = SPOTIFY_MODE if authenticated else DEMO_MODE
    st.session_state["connect_mode"] = default_mode

if st.session_state.get(CONNECT_MODE_WIDGET_KEY) not in {DEMO_MODE, SPOTIFY_MODE}:
    st.session_state[CONNECT_MODE_WIDGET_KEY] = st.session_state["connect_mode"]

mode = st.radio(
    "Start with",
    [DEMO_MODE, SPOTIFY_MODE],
    key=CONNECT_MODE_WIDGET_KEY,
    on_change=sync_connect_mode,
    horizontal=True,
    format_func=lambda value: (
        "Demo playlists" if value == DEMO_MODE else "Spotify"
    ),
)

st.caption("Choose a source, pick a playlist, then open the breakdown.")

if mode == DEMO_MODE:
    st.markdown("### Demo Playlists")
    st.caption("Included with the app. No Spotify login needed.")

    selected_demo_playlist = None
    demo_playlists = get_demo_playlists()
    demo_options = {
        playlist["id"]: f"{playlist['name']} ({playlist['tracks']['total']} tracks)"
        for playlist in demo_playlists
    }
    null_option = "__none__"
    playlist_ids = list(demo_options.keys())
    current_id = (
        st.session_state.get("selected_playlist_id", null_option)
        if st.session_state.get("selected_playlist_source") == DEMO_MODE
        else null_option
    )
    default_index = playlist_ids.index(current_id) + 1 if current_id in playlist_ids else 0

    selector_col, preview_col = st.columns([1.05, 1.45], gap="large")

    with selector_col:
        with st.container(border=True):
            selected_demo_id = st.selectbox(
                "Select a demo playlist",
                [null_option] + playlist_ids,
                index=default_index,
                format_func=lambda value: (
                    "Select a demo playlist" if value == null_option else demo_options[value]
                ),
            )

            if selected_demo_id != null_option:
                selected_demo_playlist = get_demo_playlist(selected_demo_id)
                set_selected_playlist(selected_demo_playlist, DEMO_MODE)

    with preview_col:
        st.markdown("#### Included demos")
        preview_cols = st.columns(len(demo_playlists))
        for col, playlist in zip(preview_cols, demo_playlists):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{playlist['name']}**")
                    st.caption(playlist["description"])
                    st.write(f"{playlist['tracks']['total']} tracks")

    if selected_demo_playlist is None and st.session_state.get("selected_playlist_source") == DEMO_MODE:
        selected_demo_playlist = get_demo_playlist(st.session_state["selected_playlist_id"])

    if selected_demo_playlist and selected_demo_playlist.get("id"):
        render_playlist_ready_state(selected_demo_playlist, "Demo playlist ready")
        render_nav_button(
            "pages/3_Playlist_Breakdown.py",
            "Open Breakdown →",
            icon="📊",
            key="demo_open_breakdown",
        )

    st.stop()

# --- Authenticated: show playlist selector ---
if mode == SPOTIFY_MODE and authenticated:
    token_info = st.session_state["token_info"]
    sp = spotipy.Spotify(auth=token_info["access_token"])
    st.success("Spotify connected.")
    st.markdown("### Spotify Playlists")
    st.caption("Choose one from your library or paste a public playlist URL.")

    selected_spotify_playlist = None

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

    if "spotify_user_profile" not in st.session_state:
        st.session_state["spotify_user_profile"] = sp.current_user()
    current_user_id = st.session_state["spotify_user_profile"].get("id")

    null_option = "__none__"

    current_id = st.session_state.get("selected_playlist_id", null_option)

    library_col, url_col = st.columns(2, gap="large")

    with library_col:
        with st.container(border=True):
            st.markdown("#### From your Spotify library")
            search_col, filter_col = st.columns([1.4, 1])
            with search_col:
                library_search = st.text_input(
                    "Search your library",
                    key=LIBRARY_SEARCH_WIDGET_KEY,
                    placeholder="Search by name or owner",
                )
            with filter_col:
                library_filter = st.selectbox(
                    "Filter playlists",
                    LIBRARY_FILTER_OPTIONS,
                    key=LIBRARY_FILTER_WIDGET_KEY,
                )

            filtered_playlists = filter_library_playlists(
                all_playlists,
                library_search,
                library_filter,
                current_user_id,
            )
            filtered_playlist_options = {
                playlist["id"]: format_spotify_playlist_option(playlist)
                for playlist in filtered_playlists
            }
            filtered_playlist_ids = list(filtered_playlist_options.keys())
            filtered_default_index = (
                filtered_playlist_ids.index(current_id) + 1
                if current_id in filtered_playlist_ids
                else 0
            )

            st.caption(f"{len(filtered_playlists)} playlist(s) match.")

            if filtered_playlist_ids:
                selected_id = st.selectbox(
                    "Select a playlist",
                    [null_option] + filtered_playlist_ids,
                    format_func=lambda x: "Select a playlist" if x == null_option else filtered_playlist_options[x],
                    index=filtered_default_index,
                )

                if selected_id != null_option:
                    for pl in filtered_playlists:
                        if pl["id"] == selected_id:
                            set_selected_playlist(pl, SPOTIFY_MODE)
                            selected_spotify_playlist = pl
                            break
            else:
                st.info("No playlists match the current search or filter.")

    with url_col:
        with st.container(border=True):
            st.markdown("#### Or paste a public Spotify playlist URL")
            st.caption("Use this if the playlist is not in your library.")
            with st.form(PUBLIC_PLAYLIST_FORM_KEY):
                public_playlist_reference = st.text_input(
                    "Spotify playlist URL or playlist ID",
                    value=st.session_state.get("selected_playlist_reference", ""),
                    placeholder="https://open.spotify.com/playlist/...",
                    help="Paste a public playlist URL while logged in.",
                )
                use_public_playlist = st.form_submit_button("Use Public Playlist")

    if use_public_playlist:
        try:
            selected_spotify_playlist = get_public_playlist(sp, public_playlist_reference)
            set_selected_playlist(
                selected_spotify_playlist,
                SPOTIFY_MODE,
                reference=public_playlist_reference.strip(),
            )
        except Exception as e:
            st.error(str(e))

    if selected_spotify_playlist is None and st.session_state.get("selected_playlist_source") == SPOTIFY_MODE:
        selected_spotify_playlist = get_selected_playlist_snapshot()

    if selected_spotify_playlist and selected_spotify_playlist.get("id"):
        render_playlist_ready_state(selected_spotify_playlist, "Spotify playlist ready")

    action_cols = st.columns([1, 1])
    with action_cols[0]:
        if selected_spotify_playlist and selected_spotify_playlist.get("id"):
            render_nav_button(
                "pages/3_Playlist_Breakdown.py",
                "Open Breakdown →",
                icon="📊",
                key="spotify_open_breakdown",
            )
    with action_cols[1]:
        if st.button("Disconnect"):
            disconnect_spotify()
            st.rerun()

# --- Not authenticated: show login flow ---
else:
    has_secrets = _secrets_configured()

    st.markdown("### Connect Spotify")
    st.caption("Log in to browse your playlists, use public URLs, and export sculpted playlists.")
    render_spotify_setup_help()

    if not has_secrets:
        with st.container(border=True):
            st.subheader("Spotify Credentials")
            st.caption(
                "Add credentials to `.streamlit/secrets.toml` to skip this form."
            )
            st.session_state["manual_client_id"] = st.text_input(
                "Spotify Client ID",
                value=st.session_state.get("manual_client_id", ""),
                help="Find this in your Spotify app settings in the Developer Dashboard.",
            )
            st.session_state["manual_client_secret"] = st.text_input(
                "Spotify Client Secret",
                type="password",
                value=st.session_state.get("manual_client_secret", ""),
                help="Reveal this from the same app settings page and keep it private.",
            )
            st.session_state["manual_redirect_uri"] = st.text_input(
                "Redirect URI",
                value=st.session_state.get("manual_redirect_uri", DEFAULT_SPOTIFY_REDIRECT_URI),
                help="This must exactly match one of the Redirect URIs saved in your Spotify app settings.",
            )

    client_id, client_secret, redirect_uri = get_spotify_credentials()

    if client_id and client_secret and redirect_uri:
        auth_url = SpotifyAuthManager.get_auth_url(
            client_id, client_secret, redirect_uri
        )
        st.link_button("Connect Spotify", auth_url)
    elif has_secrets:
        st.error("Spotify credentials in secrets.toml are incomplete.")
