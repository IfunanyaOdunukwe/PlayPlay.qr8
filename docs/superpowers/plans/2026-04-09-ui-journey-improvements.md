# UI Journey Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix dead-ends, data bugs, and UX friction across all 5 pages of the PlayPlay.qr8 Streamlit app.

**Architecture:** All changes are to existing Streamlit page files. No new modules. Changes are independent per-page and can be implemented in any order. Cross-cutting concerns (consistent playlist indicator in sidebar, `set_page_config`) are applied per-file.

**Tech Stack:** Streamlit (multi-page app), spotipy, pandas, plotly

---

## File Map

All changes modify existing files — no new files created.

| File | Changes |
|------|---------|
| `Welcome.py` | Remove duplicate OAuth handler, add navigation button, add `set_page_config` improvements |
| `pages/2_Connect_and_Select.py` | Paginate playlist fetch, fix duplicate-name bug (match by ID), add playlist context (track count), add forward navigation button, add `set_page_config` |
| `pages/3_Playlist_Breakdown.py` | Rename "Ingest" button, gate playlist ID behind developer mode, add spinner, add force-refresh toggle, add `set_page_config`, add sidebar playlist indicator, add navigation link in error guard |
| `pages/4_Vibe_Inspector.py` | Default-select first 3 tracks for radar, simplify tempo caption, add `set_page_config`, add sidebar playlist indicator, add navigation link in error guard |
| `pages/5_Playlist_Sculptor.py` | Add "Reset to Original" button, add `set_page_config`, add sidebar playlist indicator, add navigation link in error guard |

---

### Task 1: Welcome Page — Remove Duplicate OAuth & Add Navigation

**Files:**
- Modify: `Welcome.py:1-21`

- [ ] **Step 1: Rewrite Welcome.py**

Replace the entire file content with:

```python
import streamlit as st

st.set_page_config(page_title="PlayPlay.qr8", layout="wide")

st.title("Welcome to PlayPlay.qr8!")
st.write("""
I built this app to help you analyze and curate your Spotify playlists using advanced metrics and AI. Spotify has internal analysis for its most popular songs, so I wanted to visualise it and allow users to explore their own playlists in a similar way.
""")

st.page_link("pages/2_Connect_and_Select.py", label="Connect your Spotify account →", icon="🎵")
```

The OAuth callback handling is removed here because `pages/2_Connect_and_Select.py` already handles it identically. The redirect URI points to root, but Streamlit serves all pages from the same origin — the Connect page's handler will catch the `?code=` param when the user navigates there. However, since the OAuth redirect may land on root with `?code=`, we need to keep a minimal redirect that sends the user to Connect with the code param preserved. Updated version:

```python
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
```

- [ ] **Step 2: Verify the page loads**

Run: `source .venv/bin/activate && streamlit run Welcome.py --server.headless true &` then check `curl -s http://127.0.0.1:8501 | head -20` returns HTML. Kill the process after.

- [ ] **Step 3: Commit**

```bash
git add Welcome.py
git commit -m "fix(welcome): remove duplicate OAuth handler, add navigation button to Connect page"
```

---

### Task 2: Connect & Select — Paginate Playlists, Fix Duplicate Names, Add Context & Navigation

**Files:**
- Modify: `pages/2_Connect_and_Select.py:1-122`

- [ ] **Step 1: Add `set_page_config` at the top**

Add as the very first lines of the file (before any other imports):

```python
import streamlit as st
st.set_page_config(page_title="Connect & Select | PlayPlay.qr8", layout="wide")
```

Remove the existing `import streamlit as st` line lower in the file (currently line 1).

- [ ] **Step 2: Replace playlist fetching with paginated version**

Replace lines 58-60:

```python
    if "user_playlists" not in st.session_state:
        st.session_state["user_playlists"] = sp.current_user_playlists()
    playlists = st.session_state["user_playlists"]
```

With:

```python
    if "user_playlists" not in st.session_state:
        all_playlists = []
        results = sp.current_user_playlists(limit=50)
        all_playlists.extend(results["items"])
        while results["next"]:
            results = sp.next(results)
            all_playlists.extend(results["items"])
        st.session_state["user_playlists"] = all_playlists
    all_playlists = st.session_state["user_playlists"]
```

- [ ] **Step 3: Replace name-based matching with ID-based matching**

Replace lines 61-86 (the selectbox + matching logic) with:

```python
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
```

- [ ] **Step 4: Commit**

```bash
git add pages/2_Connect_and_Select.py
git commit -m "fix(connect): paginate playlists, match by ID, show track counts, add forward nav"
```

---

### Task 3: Playlist Breakdown — Rename Button, Spinner, Force Refresh, Guard Fix

**Files:**
- Modify: `pages/3_Playlist_Breakdown.py:1-151`

- [ ] **Step 1: Add `set_page_config` and sidebar playlist indicator**

Replace line 1 (`import streamlit as st`) with:

```python
import streamlit as st
st.set_page_config(page_title="Playlist Breakdown | PlayPlay.qr8", layout="wide")
```

- [ ] **Step 2: Fix the error guard to include navigation**

Replace lines 51-53:

```python
if not playlist_name or not playlist_id:
    st.error("No playlist selected. Please go back and select a playlist.")
    st.stop()
```

With:

```python
if not playlist_name or not playlist_id:
    st.warning("No playlist selected.")
    st.page_link("pages/2_Connect_and_Select.py", label="Go to Connect & Select →", icon="🔗")
    st.stop()
```

- [ ] **Step 3: Gate playlist ID behind developer mode and add sidebar indicator**

Replace lines 55-56:

```python
st.write(f"**Selected Playlist:** {playlist_name}")
st.write(f"**Playlist ID:** {playlist_id}")
```

With:

```python
with st.sidebar:
    st.caption(f"🎵 {playlist_name}")

st.write(f"**Selected Playlist:** {playlist_name}")
if st.session_state.get("developer_mode", False):
    st.write(f"**Playlist ID:** {playlist_id}")
```

- [ ] **Step 4: Rename button and add force-refresh toggle**

Replace line 63:

```python
eat_pressed = st.button("Ingest")
```

With:

```python
col_btn, col_refresh = st.columns([1, 1])
with col_btn:
    eat_pressed = st.button("Load Playlist Data")
with col_refresh:
    force_refresh = st.toggle("Force refresh from Spotify", value=False, help="Re-fetch from Spotify even if cached data exists.")
```

- [ ] **Step 5: Add spinner and wire up force_refresh**

Replace lines 76-91 (the `if show_df or eat_pressed:` block, up through the success messages) with:

```python
if show_df or eat_pressed:
    try:
        df = None
        if not force_refresh:
            df = load_from_cache(playlist_id)
        if df is not None:
            st.success(f"Loaded {len(df)} tracks from cache.")
        else:
            token_info = st.session_state.get('token_info')
            if not token_info or not SpotifyAuthManager.is_token_valid(token_info):
                st.error("Spotify authentication expired. Please reconnect.")
                st.stop()
            sp = spotipy.Spotify(auth=token_info['access_token'])
            reccobeats_api_key = st.session_state.get('reccobeats_api_key')
            with st.spinner("Fetching tracks and audio features from Spotify..."):
                df = fetch_playlist_data(sp, playlist_id, force_refresh=True, reccobeats_api_key=reccobeats_api_key)
            if df is not None and not df.empty:
                st.success(f"Fetched and cached {len(df)} tracks.")
            else:
                st.warning("No tracks found or ingestion failed.")
```

The rest of the file (from `if df is not None and not df.empty:` onwards displaying the dataframe) stays the same.

- [ ] **Step 6: Commit**

```bash
git add pages/3_Playlist_Breakdown.py
git commit -m "fix(breakdown): rename Ingest, add spinner, force-refresh, navigation guard"
```

---

### Task 4: Vibe Inspector — Default Tracks, Simpler Caption, Guard Fix

**Files:**
- Modify: `pages/4_Vibe_Inspector.py:1-366`

- [ ] **Step 1: Add `set_page_config` at top**

Add as the very first lines:

```python
import streamlit as st
st.set_page_config(page_title="Vibe Inspector | PlayPlay.qr8", layout="wide")
```

Remove the existing `import streamlit as st` (currently line 1).

- [ ] **Step 2: Fix error guard with navigation**

Replace lines 97-99:

```python
if not playlist_name or not playlist_id:
    st.error("No playlist selected. Please go back and select a playlist.")
    st.stop()
```

With:

```python
if not playlist_name or not playlist_id:
    st.warning("No playlist selected.")
    st.page_link("pages/2_Connect_and_Select.py", label="Go to Connect & Select →", icon="🔗")
    st.stop()
```

- [ ] **Step 3: Add sidebar playlist indicator**

After the cache-loading block (after line 109, after `st.stop()`), add:

```python
with st.sidebar:
    st.caption(f"🎵 {playlist_name}")
```

- [ ] **Step 4: Default-select first 3 tracks in radar chart**

Replace lines 151-156:

```python
selected_ids = st.multiselect(
    "Select tracks to visualize",
    options=list(track_display.keys()),
    format_func=lambda x: track_display.get(x, x),
    help="Search and select one or more tracks to plot on the radar chart.",
)
```

With:

```python
default_ids = list(track_display.keys())[:3]
selected_ids = st.multiselect(
    "Select tracks to visualize",
    options=list(track_display.keys()),
    default=default_ids,
    format_func=lambda x: track_display.get(x, x),
    help="Search and select one or more tracks to plot on the radar chart.",
)
```

- [ ] **Step 5: Simplify tempo normalization caption**

Replace lines 177-179:

```python
st.caption(
    "Tempo normalization: each track's BPM is divided by the highest BPM in the current playlist and clamped to [0, 1] so it can be plotted alongside 0–1 metrics."
)
```

With:

```python
st.caption(
    "Tempo is scaled relative to the fastest track in this playlist so it fits the 0–1 radar scale."
)
```

- [ ] **Step 6: Commit**

```bash
git add pages/4_Vibe_Inspector.py
git commit -m "fix(inspector): default track selection, simpler caption, navigation guard"
```

---

### Task 5: Playlist Sculptor — Reset Button, Guard Fix, Page Config

**Files:**
- Modify: `pages/5_Playlist_Sculptor.py:1-263`

- [ ] **Step 1: Add `set_page_config` at top**

Add as the very first lines:

```python
import streamlit as st
st.set_page_config(page_title="Playlist Sculptor | PlayPlay.qr8", layout="wide")
```

Remove the existing `import streamlit as st` (currently line 1).

- [ ] **Step 2: Fix error guard with navigation**

Replace lines 17-19:

```python
if not playlist_name or not playlist_id:
    st.error("No playlist selected. Please go back and select a playlist.")
    st.stop()
```

With:

```python
if not playlist_name or not playlist_id:
    st.warning("No playlist selected.")
    st.page_link("pages/2_Connect_and_Select.py", label="Go to Connect & Select →", icon="🔗")
    st.stop()
```

- [ ] **Step 3: Add sidebar playlist indicator**

After the LLM configuration sidebar block (after line 107, after `st.warning("Enter an API key to enable the sculptor.")`), add inside the `with st.sidebar:` block, before it closes:

Actually, add a new sidebar block right after the existing `with st.sidebar:` block ends (after line 108):

```python
with st.sidebar:
    st.divider()
    st.caption(f"🎵 {playlist_name}")
```

- [ ] **Step 4: Add "Reset to Original" button**

After the stats bar and divider (after line 129, after `st.divider()`), add:

```python
# Reset button — only show if working data differs from original
df_original = st.session_state["sculptor_df_original"]
has_changes = len(df_working) != len(df_original) or not df_working["id"].equals(df_original["id"])

if has_changes:
    if st.button("Reset to Original", help="Discard all sculpting changes and restore the original playlist."):
        st.session_state["sculptor_df_working"] = st.session_state["sculptor_df_original"].copy()
        st.session_state["sculptor_messages"].append(
            {"role": "assistant", "content": "Playlist reset to original."}
        )
        st.session_state["sculptor_pending_proposal"] = None
        st.session_state["sculptor_pending_df_preview"] = None
        st.session_state["sculptor_pending_comparison"] = None
        st.rerun()
```

Then update the existing `has_changes` check near the bottom of the file (around line 222-223) to reuse the already-computed values. Replace:

```python
df_original = st.session_state["sculptor_df_original"]
has_changes = len(df_working) != len(df_original) or not df_working["id"].equals(df_original["id"])
```

With just (since `df_original` and `has_changes` are already defined above):

```python
# has_changes and df_original already computed above
```

- [ ] **Step 5: Commit**

```bash
git add pages/5_Playlist_Sculptor.py
git commit -m "fix(sculptor): add reset button, navigation guard, page config"
```

---

## Verification

After all tasks, run the app and walk through the full journey:

1. Welcome page shows navigation button, no OAuth handling errors
2. Connect page fetches all playlists, shows track counts, no duplicate-name issues
3. After selecting a playlist, "Continue to Playlist Breakdown" link appears
4. Breakdown page shows spinner during fetch, "Load Playlist Data" button, force-refresh toggle
5. Vibe Inspector loads with 3 tracks pre-selected on radar, simplified tempo caption
6. Sculptor shows "Reset to Original" button after applying changes
7. All error guards show navigation links instead of bare error messages
8. All pages show playlist name in sidebar when a playlist is selected
