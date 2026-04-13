from html import escape

import streamlit as st
st.set_page_config(page_title="Connect & Select | PlayPlay.qr8", layout="wide")

import spotipy
from src.auth import (
    DEFAULT_SPOTIFY_REDIRECT_URI,
    SpotifyAuthManager,
    clear_pending_spotify_auth,
    create_pending_spotify_auth,
    format_spotify_auth_error,
    get_runtime_redirect_uri,
    get_spotify_credentials,
    get_spotify_credentials_signature,
    validate_spotify_credentials,
)
from src.demo import get_demo_playlist, get_demo_playlists, get_public_playlist
from src.session_state import (
    DEMO_PLAYLIST_WIDGET_KEY,
    SPOTIFY_LIBRARY_PLAYLIST_WIDGET_KEY,
    clear_playlist_dependent_state,
    clear_spotify_auth_state,
    clear_spotify_callback_payload,
    get_playlist_owner_label,
    get_selected_playlist_snapshot,
    get_spotify_callback_payload,
    set_selected_playlist,
    store_spotify_callback_payload,
)
from src.theme import apply_spotify_theme, render_nav_button, render_playlist_indicator

apply_spotify_theme()
st.title("")
playlist_indicator_slot = st.empty()
st.write(
    "Connect Spotify for the full experience and choose your own playlists, or try out the included demo playlists with no login required."
)

DEMO_MODE = "demo"
SPOTIFY_MODE = "spotify"
CONNECT_MODE_WIDGET_KEY = "connect_mode_widget"
PUBLIC_PLAYLIST_FORM_KEY = "spotify_public_playlist_form"
LIBRARY_SEARCH_WIDGET_KEY = "spotify_library_search"
LIBRARY_FILTER_WIDGET_KEY = "spotify_library_filter"
SPOTIFY_FAILED_EXCHANGE_KEY = "spotify_failed_exchange_key"
SPOTIFY_PENDING_AUTH_STATE_KEY = "spotify_pending_auth_state"
SPOTIFY_PENDING_AUTH_SIGNATURE_KEY = "spotify_pending_auth_signature"
SPOTIFY_VALIDATED_SIGNATURE_KEY = "spotify_validated_credentials_signature"
LIBRARY_FILTER_OPTIONS = [
    "All playlists",
    "Owned by you",
    "Saved from others",
    "Collaborative",
]


def clear_selected_playlist():
    clear_playlist_dependent_state(st.session_state)


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


def update_playlist_indicator(playlist: dict | None):
    if playlist and playlist.get("name"):
        with playlist_indicator_slot.container():
            render_playlist_indicator("Current Playlist", playlist["name"])
    else:
        playlist_indicator_slot.empty()


def sync_spotify_library_selection():
    selected_id = st.session_state.get(SPOTIFY_LIBRARY_PLAYLIST_WIDGET_KEY)
    if not selected_id or selected_id == "__none__":
        if not st.session_state.get("selected_playlist_reference"):
            clear_selected_playlist()
        return

    for playlist in st.session_state.get("user_playlists", []):
        if playlist.get("id") == selected_id:
            set_selected_playlist(st.session_state, playlist, SPOTIFY_MODE)
            return


def disconnect_spotify():
    pending_auth_state = st.session_state.get(SPOTIFY_PENDING_AUTH_STATE_KEY)
    clear_spotify_auth_state(st.session_state, include_manual_inputs=True)
    clear_pending_spotify_auth(pending_auth_state)
    if st.session_state.get("selected_playlist_source") == SPOTIFY_MODE:
        clear_selected_playlist()


def sync_connect_mode():
    new_mode = st.session_state[CONNECT_MODE_WIDGET_KEY]
    old_mode = st.session_state.get("connect_mode")
    if old_mode != new_mode:
        st.session_state["connect_mode"] = new_mode
        if old_mode is not None:
            clear_selected_playlist()


def render_spotify_setup_help():
    current_redirect_uri = get_runtime_redirect_uri()
    with st.expander("How to set up Spotify login"):
        st.markdown(
            f"""
            1. Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
            2. Open the app settings, copy the **Client ID**, and use **View client secret** to reveal the **Client Secret**.
            3. In **APIs used**, choose **Web API**.
            4. In **Redirect URIs**, add the following:
                - `https://playplayqr8.streamlit.app`
                - `http://127.0.0.1:8501` (add this one if you plan to run the app locally)
            5. Save the app, then paste the **Client ID** and **Client Secret** into the form below.

            Official guides:
            [Getting Started](https://developer.spotify.com/documentation/web-api/tutorials/getting-started)
            and [Apps](https://developer.spotify.com/documentation/web-api/concepts/apps)
            """
        )


def render_spotify_continue_link(auth_url: str):
    st.markdown(
        f"""
        <style>
        .spotify-auth-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.7rem 1.1rem;
            border-radius: 999px;
            background: #1db954;
            color: #04130a !important;
            font-weight: 700;
            text-decoration: none;
        }}
        .spotify-auth-link:hover {{
            background: #18a349;
            color: #04130a !important;
        }}
        </style>
        <a class="spotify-auth-link" href="{escape(auth_url, quote=True)}" target="_self">
            Continue to Spotify
        </a>
        """,
        unsafe_allow_html=True,
    )


# --- Handle OAuth callback (code in query params) ---
query_code = st.query_params.get("code")
query_state = st.query_params.get("state")
if query_code:
    store_spotify_callback_payload(st.session_state, query_code, query_state)
    st.query_params.clear()

callback_payload = get_spotify_callback_payload(st.session_state)
callback_code = callback_payload.get("code")
callback_state = callback_payload.get("state")

if callback_code and "token_info" not in st.session_state:
    st.session_state["connect_mode"] = SPOTIFY_MODE
    st.session_state[CONNECT_MODE_WIDGET_KEY] = SPOTIFY_MODE
    client_id, client_secret, redirect_uri = get_spotify_credentials(auth_state=callback_state)
    credentials_signature = get_spotify_credentials_signature(client_id, client_secret)
    failed_exchange_key = f"{callback_code}:{callback_state or credentials_signature}"
    if client_id and client_secret and redirect_uri:
        if st.session_state.get(SPOTIFY_FAILED_EXCHANGE_KEY) != failed_exchange_key:
            try:
                token_info = SpotifyAuthManager.exchange_code(
                    callback_code, client_id, client_secret, redirect_uri
                )
                st.session_state["token_info"] = token_info
                st.session_state.pop("spotify_auth_error", None)
                clear_spotify_callback_payload(st.session_state)
                st.session_state.pop(SPOTIFY_FAILED_EXCHANGE_KEY, None)
                pending_auth_state = st.session_state.pop(SPOTIFY_PENDING_AUTH_STATE_KEY, None)
                st.session_state.pop(SPOTIFY_PENDING_AUTH_SIGNATURE_KEY, None)
                clear_pending_spotify_auth(callback_state or pending_auth_state)
                st.rerun()
            except Exception as e:
                st.session_state["spotify_auth_error"] = format_spotify_auth_error(e)
                st.session_state[SPOTIFY_FAILED_EXCHANGE_KEY] = failed_exchange_key

# --- Check for existing valid token ---
token_info = st.session_state.get("token_info")
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
    "Choose your experience",
    [SPOTIFY_MODE, DEMO_MODE],
    key=CONNECT_MODE_WIDGET_KEY,
    on_change=sync_connect_mode,
    horizontal=True,
    format_func=lambda value: (
        "Spotify" if value == SPOTIFY_MODE else "Demo Playlists"
    ),
)

if mode == DEMO_MODE:
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
    demo_select_options = [null_option] + playlist_ids

    if DEMO_PLAYLIST_WIDGET_KEY not in st.session_state:
        st.session_state[DEMO_PLAYLIST_WIDGET_KEY] = (
            current_id if current_id in playlist_ids else null_option
        )
    elif st.session_state[DEMO_PLAYLIST_WIDGET_KEY] not in demo_select_options:
        st.session_state[DEMO_PLAYLIST_WIDGET_KEY] = (
            current_id if current_id in playlist_ids else null_option
        )

    selector_col, preview_col = st.columns([1.05, 1.45], gap="large")

    with selector_col:
        with st.container(border=True):
            selected_demo_id = st.selectbox(
                "Select a demo playlist",
                demo_select_options,
                key=DEMO_PLAYLIST_WIDGET_KEY,
                format_func=lambda value: (
                    "Select a demo playlist" if value == null_option else demo_options[value]
                ),
            )

            if selected_demo_id != null_option:
                selected_demo_playlist = get_demo_playlist(selected_demo_id)
                set_selected_playlist(st.session_state, selected_demo_playlist, DEMO_MODE)
            elif st.session_state.get("selected_playlist_source") == DEMO_MODE:
                clear_selected_playlist()

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
        selected_demo_playlist = get_selected_playlist_snapshot(st.session_state)

    update_playlist_indicator(selected_demo_playlist)

    if selected_demo_playlist and selected_demo_playlist.get("id"):
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
    current_reference = st.session_state.get("selected_playlist_reference")
    current_source = st.session_state.get("selected_playlist_source")

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
            library_select_options = [null_option] + filtered_playlist_ids
            preferred_library_id = (
                current_id
                if current_source == SPOTIFY_MODE and not current_reference and current_id in filtered_playlist_ids
                else null_option
            )
            if st.session_state.get(SPOTIFY_LIBRARY_PLAYLIST_WIDGET_KEY) != preferred_library_id:
                st.session_state[SPOTIFY_LIBRARY_PLAYLIST_WIDGET_KEY] = preferred_library_id

            st.caption(f"{len(filtered_playlists)} playlist(s) match.")

            if filtered_playlist_ids:
                selected_id = st.selectbox(
                    "Select a playlist",
                    library_select_options,
                    key=SPOTIFY_LIBRARY_PLAYLIST_WIDGET_KEY,
                    on_change=sync_spotify_library_selection,
                    format_func=lambda x: "Select a playlist" if x == null_option else filtered_playlist_options[x],
                )

                if selected_id != null_option:
                    selected_spotify_playlist = next(
                        (pl for pl in filtered_playlists if pl["id"] == selected_id),
                        None,
                    )
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
                st.session_state,
                selected_spotify_playlist,
                SPOTIFY_MODE,
                reference=public_playlist_reference.strip(),
            )
        except Exception as e:
            st.error(str(e))

    if selected_spotify_playlist is None and st.session_state.get("selected_playlist_source") == SPOTIFY_MODE:
        selected_spotify_playlist = get_selected_playlist_snapshot(st.session_state)

    update_playlist_indicator(selected_spotify_playlist)

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
    update_playlist_indicator(None)
    current_redirect_uri = get_runtime_redirect_uri()
    st.session_state["manual_redirect_uri"] = current_redirect_uri

    st.markdown("### Connect Spotify")
    st.caption("Log in to browse your playlists, use public URLs, and export sculpted playlists.")
    render_spotify_setup_help()

    with st.container(border=True):
        st.subheader("Spotify Credentials")
        st.caption(
            "Paste your Client ID and Client Secret. None of this info is saved in the app — tokens are kept in session only and you can disconnect at any time to clear them."
        )

        with st.form("spotify_credentials_form"):
            st.text_input(
                "Spotify Client ID",
                key="manual_client_id",
                help="Find this in your Spotify app settings in the Developer Dashboard.",
            )
            st.text_input(
                "Spotify Client Secret",
                key="manual_client_secret",
                type="password",
                help="Reveal this from the same app settings page and keep it private. Tokens are kept in session only.",
            )
            submitted_credentials = st.form_submit_button(
                "Finish Spotify Login" if callback_code else "Validate Credentials"
            )

    if submitted_credentials:
        client_id, client_secret, _ = get_spotify_credentials()
        credentials_signature = get_spotify_credentials_signature(client_id, client_secret)
        credentials_valid, validation_message = validate_spotify_credentials(
            client_id,
            client_secret,
        )
        if credentials_valid:
            previous_pending_state = st.session_state.get(SPOTIFY_PENDING_AUTH_STATE_KEY)
            clear_pending_spotify_auth(previous_pending_state)
            pending_auth_state = create_pending_spotify_auth(
                client_id,
                client_secret,
                current_redirect_uri,
            )
            st.session_state[SPOTIFY_PENDING_AUTH_STATE_KEY] = pending_auth_state
            st.session_state[SPOTIFY_PENDING_AUTH_SIGNATURE_KEY] = credentials_signature
            st.session_state[SPOTIFY_VALIDATED_SIGNATURE_KEY] = credentials_signature
            st.session_state.pop("spotify_auth_error", None)
            st.session_state.pop(SPOTIFY_FAILED_EXCHANGE_KEY, None)
            if callback_code:
                st.rerun()
        else:
            previous_pending_state = st.session_state.pop(SPOTIFY_PENDING_AUTH_STATE_KEY, None)
            st.session_state.pop(SPOTIFY_PENDING_AUTH_SIGNATURE_KEY, None)
            clear_pending_spotify_auth(previous_pending_state)
            st.session_state.pop(SPOTIFY_VALIDATED_SIGNATURE_KEY, None)
            st.session_state["spotify_auth_error"] = validation_message

    client_id, client_secret, redirect_uri = get_spotify_credentials()
    credentials_signature = get_spotify_credentials_signature(client_id, client_secret)
    pending_auth_state = st.session_state.get(SPOTIFY_PENDING_AUTH_STATE_KEY)
    credentials_validated = (
        credentials_signature
        and st.session_state.get(SPOTIFY_VALIDATED_SIGNATURE_KEY) == credentials_signature
        and st.session_state.get(SPOTIFY_PENDING_AUTH_SIGNATURE_KEY) == credentials_signature
    )

    if callback_code and not (client_id and client_secret):
        st.info(
            "Spotify sent you back with an authorization code. Enter your Client ID and Client Secret above to finish the login."
        )

    auth_error = st.session_state.get("spotify_auth_error")
    if auth_error:
        st.error(auth_error)

    if (
        client_id
        and client_secret
        and redirect_uri
        and credentials_validated
        and pending_auth_state
        and not callback_code
    ):
        auth_url = SpotifyAuthManager.get_auth_url(
            client_id,
            client_secret,
            redirect_uri,
            state=pending_auth_state,
        )
        st.success("Credentials look good. Continue to Spotify and approve access.")
        render_spotify_continue_link(auth_url)
