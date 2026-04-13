import streamlit as st

st.set_page_config(page_title="PlayPlay.qr8", layout="wide")

from src.audio_features import AUDIO_GUIDE_METRICS
from src.session_state import store_spotify_callback_payload
from src.theme import apply_spotify_theme, render_brand_wordmark, render_nav_button

apply_spotify_theme()


def render_about_page() -> None:
    render_brand_wordmark(level=1)
    st.caption("Thanks for checking out this app!")

    st.markdown(
        """
        ### But Why 🎧
        I made PlayPlay.qr8 because I find Spotify's internal metrics really interesting, and I wanted to try to crunch that data to critique my own playlists.

        You might like this app if:
        - you want to see into the (data) guts of your music
        - you want to experiment with AI-assisted playlist editing
        - you like looking at numbers
        
        Spotify has since deprecated [the audio features endpoint this app relies on and limited many others](https://spotify.leemartin.com/)🥲 . 

        Thankfully, the [Reccobeats API](https://reccobeats.com/docs/documentation/introduction) was able to fill the gap - thanks Reccobeats!  

        The recent changes does also mean that connecting to Spotify is no longer as [smooth](https://developer.spotify.com/documentation/web-api/concepts/quota-modes), and so it does require a little setup to unlock the main value of this app - sorry! I hope that the coolness of exploring your playlists is worth the initial effort, but if you're not sure, just use the demo playlists to check it out first.
        """
    )

    st.markdown(
        """
        ### How To Use 👨‍💻
        1. Use the sidebar to navigate through the app.
        2. Start at **Connect & Select**.
        3. Move down the flow page by page.
        4. If any metric names are unclear, open **Audio Features Explained**.
        """
    )

    st.markdown(
        """
        ### Features
        - **Demo or Spotify flow:** Try bundled demo playlists instantly, or connect Spotify for a better experience (short guide included).
        - **Playlist Breakdown:** View track-level metadata and audio features in a sortable table.
        - **Vibe Inspector:** Explore playlist patterns with summary stats, radar views, valence-vs-energy scatter, and tempo distribution.
        - **Playlist Sculptor:** Use AI prompts to propose removals, reorder tracks, and highlight candidates before applying changes.
        - **Export options:** Refine your playlist in the app, then send the new playlist right back to Spotify!
        """
    )

    st.markdown(
        """
        ### Feedback 📨
        Feedback always welcome. If you find a bug, have ideas for improvements, or want to contribute, please open an issue in the project repository.
        """
    )

    st.markdown(
        """
        ### Acknowledgements 👨‍🏫
        Special thanks to Reccobeats for providing an alternate Audio Features endpoint.
        """
    )

    st.markdown(
        """
        ### Support The Project ⭐
        If you like PlayPlay.qr8, please star the project on GitHub.
        """
    )

    st.markdown(
        """
        <a href="https://github.com/IfunanyaOdunukwe/PlayPlay.qr8" target="_blank" rel="noopener noreferrer" style="font-size: 2rem; text-decoration: none;" aria-label="Open PlayPlay.qr8 on GitHub">🐙</a>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """

        ~ Ify
        """
    )

    st.divider()

    render_nav_button(
        "pages/2_Connect_and_Select.py",
        "Start Exploring →",
        icon="🎵",
        button_type="primary",
        key="about_start_exploring",
    )


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

about_page = st.Page(render_about_page, title="About", default=True)
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
