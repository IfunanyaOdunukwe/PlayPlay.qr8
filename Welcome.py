import streamlit as st

st.set_page_config(page_title="PlayPlay.qr8", layout="wide")

from src.audio_features import AUDIO_GUIDE_METRICS
from src.session_state import store_spotify_callback_payload
from src.theme import apply_spotify_theme, render_brand_wordmark, render_nav_button

apply_spotify_theme()


def render_audio_features_page() -> None:
    st.title("")
    st.caption(
        "These metrics [originate](https://developer.spotify.com/documentation/web-api/reference/get-audio-features/) from Spotify based on internal audio analysis. "
    )

    left_column, right_column = st.columns(2)
    for index, (label, description) in enumerate(AUDIO_GUIDE_METRICS):
        column = left_column if index % 2 == 0 else right_column
        with column:
            st.markdown(f"**{label}**")
            st.write(description)
            st.divider()

    st.divider()

    render_nav_button(
        "pages/2_Connect_and_Select.py",
        "Get Started →",
        icon="🎵",
        button_type="primary",
        key="guide_get_started",
    )


with st.sidebar:
    render_brand_wordmark(level=3)

about_page = st.Page("pages/1_About.py", title="About", default=True)
guide_page = st.Page(render_audio_features_page, title="Audio Features Explained")
connect_page = st.Page("pages/2_Connect_and_Select.py", title="Connect & Select")
breakdown_page = st.Page("pages/3_Playlist_Breakdown.py", title="Playlist Breakdown")
inspector_page = st.Page("pages/4_Vibe_Inspector.py", title="Vibe Inspector")
sculptor_page = st.Page("pages/5_Playlist_Sculptor.py", title="Playlist Sculptor")

pg = st.navigation(
    [about_page, connect_page, breakdown_page, inspector_page, sculptor_page, guide_page],
    position="sidebar",
)

# Handle Spotify OAuth callback — the redirect URI lands here at the app root.
# Route to Connect & Select after navigation is registered.
query_code = st.query_params.get("code")
query_state = st.query_params.get("state")
if query_code:
    store_spotify_callback_payload(st.session_state, query_code, query_state)
    st.query_params.clear()
    st.switch_page(connect_page)

pg.run()
