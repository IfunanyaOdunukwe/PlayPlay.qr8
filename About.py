import streamlit as st

st.set_page_config(page_title="PlayPlay.qr8", layout="wide")

from src.audio_features import AUDIO_GUIDE_METRICS
from src.auth import SpotifyAuthManager, get_spotify_credentials
from src.theme import apply_spotify_theme, render_nav_button

GUIDE_SECTIONS = [
    (
        "Feel & Mood",
        "Rhythm, intensity, and emotional tone.",
        ["Danceability", "Energy", "Valence"],
    ),
    (
        "Voice & Texture",
        "Whether a track reads as acoustic, instrumental, spoken, or live.",
        ["Speechiness", "Acousticness", "Instrumentalness", "Liveness"],
    ),
    (
        "Musical Structure",
        "Speed, overall volume, and harmonic context.",
        ["Tempo", "Loudness", "Mode", "Key"],
    ),
]

apply_spotify_theme()

# Handle Spotify OAuth callback — the redirect URI lands here at the app root.
# Exchange the code for a token before navigating, because query params don't
# survive `st.switch_page`.
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
            st.switch_page("pages/2_Connect_and_Select.py")
        except Exception as e:
            st.error(f"Failed to exchange Spotify auth code: {e}")
    else:
        st.error("Spotify credentials are missing — cannot complete login.")


def render_about_page() -> None:
    return


def render_audio_features_page() -> None:
    st.title("Audio Features Guide")
    st.caption(
        "The original definitions are grouped below to make the page easier to scan. "
        "Most metrics use a 0.0 to 1.0 scale, while tempo is BPM and loudness is dB."
    )

    metric_lookup = dict(AUDIO_GUIDE_METRICS)
    tabs = st.tabs([title for title, _, _ in GUIDE_SECTIONS])

    for tab, (title, summary, labels) in zip(tabs, GUIDE_SECTIONS):
        with tab:
            st.caption(summary)
            left_column, right_column = st.columns(2)

            for index, label in enumerate(labels):
                column = left_column if index % 2 == 0 else right_column
                with column:
                    with st.expander(label, expanded=index == 0):
                        st.write(metric_lookup[label])

    st.divider()

    render_nav_button(
        "pages/2_Connect_and_Select.py",
        "Get Started →",
        icon="🎵",
        button_type="primary",
        key="guide_get_started",
    )


with st.sidebar:
    st.title("PlayPlay.qr8")

about_page = st.Page(render_about_page, title="About", default=True)
guide_page = st.Page(render_audio_features_page, title="Audio Features Guide")
connect_page = st.Page("pages/2_Connect_and_Select.py", title="Connect & Select")
breakdown_page = st.Page("pages/3_Playlist_Breakdown.py", title="Playlist Breakdown")
inspector_page = st.Page("pages/4_Vibe_Inspector.py", title="Vibe Inspector")
sculptor_page = st.Page("pages/5_Playlist_Sculptor.py", title="Playlist Sculptor")

pg = st.navigation(
    [about_page, guide_page, connect_page, breakdown_page, inspector_page, sculptor_page],
    position="sidebar",
)
pg.run()
