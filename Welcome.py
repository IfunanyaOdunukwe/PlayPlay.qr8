import streamlit as st

st.set_page_config(page_title="PlayPlay.qr8", layout="wide")

# If OAuth redirect lands here with ?code=, forward to Connect page for handling
if st.query_params.get("code"):
    st.switch_page("pages/2_Connect_and_Select.py")

st.title("Welcome to PlayPlay.qr8!")
st.write("""
I built this app to help you analyze and curate your Spotify playlists using advanced metrics and AI. Spotify has internal analysis for its most popular songs, so I wanted to visualise it and allow users to explore their own playlists in a similar way.
""")

st.page_link("pages/2_Connect_and_Select.py", label="Connect your Spotify account →", icon="🎵")
