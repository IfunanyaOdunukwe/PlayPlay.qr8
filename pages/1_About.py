import streamlit as st

from src.theme import apply_spotify_theme, render_brand_wordmark, render_nav_button

apply_spotify_theme()

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
