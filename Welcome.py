import streamlit as st
from html import escape

st.set_page_config(page_title="PlayPlay.qr8", layout="wide")

from src.audio_features import WELCOME_AUDIO_METRICS
from src.session_state import store_spotify_callback_payload
from src.theme import apply_spotify_theme, render_brand_wordmark, render_nav_button

apply_spotify_theme()

def render_about_page() -> None:
    st.title("About")
    st.write(
        "Analyze and reshape playlists with audio features and AI. Use a demo playlist or connect Spotify to inspect your own playlists and public playlist URLs."
    )

    metric_cards = "".join(
        f"<div class=\"spotify-metric-card\"><strong>{escape(label)}</strong><span>{escape(description)}</span></div>"
        for label, description in WELCOME_AUDIO_METRICS
    )

    st.markdown(
        f"""
        <section class="spotify-metrics-panel">
            <div class="spotify-metrics-kicker">Audio Features Guide</div>
            <h2>What The Key Metrics Mean</h2>
            <p class="spotify-metrics-intro">
                These metrics power the tables, summaries, and charts across the app.
            </p>
            <div class="spotify-metrics-grid">{metric_cards}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    render_nav_button(
        "pages/2_Connect_and_Select.py",
        "Get Started →",
        icon="🎵",
        button_type="primary",
        key="welcome_get_started",
    )


with st.sidebar:
    render_brand_wordmark(level=3)

about_page = st.Page(render_about_page, title="About", default=True)
connect_page = st.Page("pages/2_Connect_and_Select.py", title="Connect & Select")
breakdown_page = st.Page("pages/3_Playlist_Breakdown.py", title="Playlist Breakdown")
inspector_page = st.Page("pages/4_Vibe_Inspector.py", title="Vibe Inspector")
sculptor_page = st.Page("pages/5_Playlist_Sculptor.py", title="Playlist Sculptor")

pg = st.navigation(
    [about_page, connect_page, breakdown_page, inspector_page, sculptor_page],
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
