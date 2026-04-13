import streamlit as st
st.set_page_config(page_title="Vibe Inspector | PlayPlay.qr8", layout="wide")

import pandas as pd
from src.ingestion import load_from_cache
from src.demo import get_demo_playlist_df
from src.theme import (
    SPOTIFY_GREEN,
    SPOTIFY_GRID,
    SPOTIFY_METRIC_COLOR_MAP,
    SPOTIFY_PLOTLY_COLORWAY,
    SPOTIFY_PLOTLY_TEMPLATE,
    SPOTIFY_TEXT,
    apply_spotify_theme,
    render_nav_button,
    render_playlist_indicator,
)
import plotly.graph_objects as go
import plotly.express as px

apply_spotify_theme()

st.title("Vibe Inspector")
st.write(
    "Review the playlist summary, compare tracks, and spot broader patterns before sculpting."
)

PLOTLY_TEMPLATE = SPOTIFY_PLOTLY_TEMPLATE
METRIC_COLOR_MAP = SPOTIFY_METRIC_COLOR_MAP
PRIMARY_COLOR = SPOTIFY_GREEN

# Utility helpers
def _to_float(val):
    try:
        return float(val)
    except Exception:
        return None

def sanitize_numeric_series(series: pd.Series, zero_invalid: bool = False) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    s = s.dropna()
    if zero_invalid:
        s = s[s > 0]
    return s

def sanitize_value(val, zero_invalid: bool = False):
    num = _to_float(val)
    if num is None:
        return None
    if zero_invalid and num == 0:
        return None
    return num


def normalize_mode_numeric_series(series: pd.Series) -> pd.Series:
    mode_text = series.astype("string").str.strip().str.lower()
    mode_numeric = pd.to_numeric(series, errors="coerce")
    mode_from_text = mode_text.map({"minor": 0, "major": 1})
    return mode_from_text.where(mode_from_text.notna(), mode_numeric)


def describe_valence(mean: float) -> str:
    pct = mean * 100
    if mean >= 0.65:
        return f"Signals a predominantly cheerful, uplifting mood (~{pct:.0f}% valence)."
    if mean <= 0.35:
        return f"Skews toward moody or introspective vibes (~{pct:.0f}% valence)."
    return f"Maintains a balanced emotional tone (~{pct:.0f}% valence)."


def describe_danceability(mean: float) -> str:
    pct = mean * 100
    if mean >= 0.70:
        return f"Built for the dance floor with a strong groove (~{pct:.0f}% danceability)."
    if mean <= 0.45:
        return f"More suited to listening than dancing (~{pct:.0f}% danceability)."
    return f"Offers a comfortable groove without being hyper-dancey (~{pct:.0f}% danceability)."


def describe_energy(mean: float) -> str:
    pct = mean * 100
    if mean >= 0.70:
        return f"Carries high intensity and drive (~{pct:.0f}% energy)."
    if mean <= 0.40:
        return f"Feels more relaxed and subdued (~{pct:.0f}% energy)."
    return f"Balances energetic and mellow moments (~{pct:.0f}% energy)."


def describe_tempo(mean_bpm: float) -> str:
    if mean_bpm >= 120:
        return f"Leans into driving, high-energy tempos (~{mean_bpm:.0f} BPM)."
    if mean_bpm <= 90:
        return f"Stays relaxed at slower BPMs (~{mean_bpm:.0f} BPM)."
    return f"Settles into a mid-tempo groove (~{mean_bpm:.0f} BPM)."


def describe_mode(share_major: float) -> str:
    pct = share_major * 100
    if share_major >= 0.60:
        return f"Major keys dominate (~{pct:.0f}% Major), keeping things uplifting."
    if share_major <= 0.40:
        return f"Minor keys lead (~{pct:.0f}% Major), adding moodiness."
    return f"Balanced blend of Major and Minor modes (~{pct:.0f}% Major)."


def describe_acousticness(mean: float) -> str:
    pct = mean * 100
    if mean >= 0.60:
        return f"Leans acoustic and organic (~{pct:.0f}% acousticness)."
    if mean <= 0.30:
        return f"Mostly electric or produced textures (~{pct:.0f}% acousticness)."
    return f"Mixes acoustic and electronic elements (~{pct:.0f}% acousticness)."


# Ensure a playlist is selected
playlist_name = st.session_state.get('selected_playlist')
playlist_id = st.session_state.get('selected_playlist_id')
playlist_source = st.session_state.get("selected_playlist_source", "spotify")
playlist_owner = st.session_state.get("selected_playlist_owner") or "Unknown"

if not playlist_name or not playlist_id:
    st.warning("No playlist selected.")
    render_nav_button(
        "pages/2_Connect_and_Select.py",
        "Open Connect & Select →",
        icon="🔗",
        key="inspector_open_connect",
    )
    st.stop()


# Load cached data (use session state to avoid re-reading JSON on every rerun)
_cache_key = f"_cached_df_{playlist_id}"
if _cache_key not in st.session_state:
    try:
        if playlist_source == "demo":
            st.session_state[_cache_key] = get_demo_playlist_df(playlist_id)
        else:
            st.session_state[_cache_key] = load_from_cache(playlist_id)
    except Exception as e:
        st.error(f"Failed to load playlist data: {e}")
        st.stop()
df = st.session_state[_cache_key]
if df is None or df.empty:
    st.warning("No cached data found. Load the playlist on Breakdown first.")
    render_nav_button(
        "pages/3_Playlist_Breakdown.py",
        "Open Breakdown →",
        icon="📊",
        key="inspector_open_breakdown",
    )
    st.stop()

with st.sidebar:
    st.caption(f"🎵 {playlist_name}")
    if playlist_source == "demo":
        st.caption("Demo playlist")

st.markdown("### Playlist Overview")
render_playlist_indicator("Current Playlist", playlist_name)

st.markdown("#### Summary")

summary_specs = [
    ("Valence", "valence", describe_valence, lambda series: sanitize_numeric_series(series, zero_invalid=False), lambda mean: f"{mean * 100:.0f}%"),
    ("Danceability", "danceability", describe_danceability, lambda series: sanitize_numeric_series(series, zero_invalid=False), lambda mean: f"{mean * 100:.0f}%"),
    ("Energy", "energy", describe_energy, lambda series: sanitize_numeric_series(series, zero_invalid=False), lambda mean: f"{mean * 100:.0f}%"),
    ("Tempo", "tempo", describe_tempo, lambda series: sanitize_numeric_series(series, zero_invalid=True), lambda mean: f"{mean:.0f} BPM"),
    ("Mode", "mode", describe_mode, lambda series: normalize_mode_numeric_series(series).dropna(), lambda mean: f"{mean * 100:.0f}% Major"),
    ("Acousticness", "acousticness", describe_acousticness, lambda series: sanitize_numeric_series(series, zero_invalid=False), lambda mean: f"{mean * 100:.0f}%"),
]

summary_entries = []
for label, column, describe_fn, sanitize_fn, format_fn in summary_specs:
    if column not in df.columns:
        continue
    series_clean = sanitize_fn(df[column])
    if series_clean.empty:
        continue
    mean_value = float(series_clean.mean())
    summary_entries.append((label, format_fn(mean_value), describe_fn(mean_value)))

if summary_entries:
    for idx in range(0, len(summary_entries), 3):
        cols = st.columns(3)
        for col, (label, formatted_value, narrative) in zip(cols, summary_entries[idx: idx + 3]):
            with col:
                st.metric(label=label, value=formatted_value)
                st.caption(narrative)
else:
    st.info("Summary metrics are unavailable because required columns are missing or empty.")

st.divider()
st.markdown("### Track Comparison")
st.caption("Compare tracks across the core vibe metrics.")
st.markdown("#### Vibe Radar")

# Prepare track options (use ID for uniqueness, display as "name — artist")
if not {'id', 'name', 'artist'}.issubset(df.columns):
    st.error("Cached data is missing required columns ('id', 'name', 'artist').")
    st.stop()

track_display = {row['id']: f"{row['name']} — {row['artist']}" for _, row in df[['id', 'name', 'artist']].iterrows()}
default_ids = list(track_display.keys())[:3]
selected_ids = st.multiselect(
    "Select tracks to visualize",
    options=list(track_display.keys()),
    default=default_ids,
    format_func=lambda x: track_display.get(x, x),
    help="Search and select tracks for the radar chart.",
)

# Metrics to visualize (order matters for the radar)
# Removed 'mode' from the radar per request
metrics = ["valence", "energy", "tempo", "danceability", "acousticness"]

missing_metrics = [m for m in metrics if m not in df.columns]
if missing_metrics:
    st.warning(f"The following metrics are missing from cached data and will be skipped: {', '.join(missing_metrics)}")

# Compute normalization for tempo to bring onto 0–1 scale
if "tempo" in df.columns:
    tempo_clean = sanitize_numeric_series(df["tempo"], zero_invalid=True)
    if tempo_clean.empty:
        tempo_max = 1.0
    else:
        tempo_max = tempo_clean.max()
else:
    tempo_max = 1.0

# Note about tempo normalization shown on the page
st.caption(
    "Tempo is scaled against the fastest track so it fits the 0-1 radar scale."
)

if selected_ids:
    fig = go.Figure()

    for track_id in selected_ids:
        row = df.loc[df['id'] == track_id]
        if row.empty:
            continue
        row = row.iloc[0]

        values = []
        for m in metrics:
            if m not in df.columns:
                values.append(0.0)
                continue

            val = row[m]
            # Normalize and coerce values
            if m == "tempo":
                val_num = sanitize_value(val, zero_invalid=True)
                if val_num is None:
                    v = None  # exclude invalid zero/NaN tempos from radar
                else:
                    v = max(0.0, min(1.0, val_num / tempo_max))
            else:
                v_num = sanitize_value(val, zero_invalid=False)
                if v_num is None:
                    v = None
                else:
                    # Clamp to [0,1]
                    v = max(0.0, min(1.0, v_num))

            values.append(v)

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=metrics,
                fill='toself',
                name=track_display.get(track_id, str(track_id)),
            )
        )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        colorway=SPOTIFY_PLOTLY_COLORWAY,
        height=500,
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(color=SPOTIFY_TEXT),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickfont=dict(size=12),
                gridcolor=SPOTIFY_GRID,
                showgrid=True,
                gridwidth=1,
            ),
            angularaxis=dict(
                rotation=90,
                tickfont=dict(size=12),
                gridcolor=SPOTIFY_GRID,
                showgrid=True,
                gridwidth=1,
            ),
        ),
        legend=dict(title="Tracks", orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=40, r=40, t=40, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select one or more tracks to view the radar chart.")

# Playlist-level mapping of valence, energy, and mode
st.markdown("### Playlist Patterns")
st.caption("Use these charts to see how the full playlist clusters and moves.")
st.markdown("#### Valence vs. Energy by Mode")

required_cols = {"valence", "energy", "mode"}
if not required_cols.issubset(df.columns):
    st.info("Valence, energy, or mode metrics are missing for this playlist.")
else:
    trio_df = pd.DataFrame(
        {
            "valence": pd.to_numeric(df["valence"], errors="coerce"),
            "energy": pd.to_numeric(df["energy"], errors="coerce"),
            "mode": normalize_mode_numeric_series(df["mode"]),
        },
        index=df.index,
    )
    trio_df = trio_df.dropna(subset=["valence", "energy", "mode"])

    # Keep mode==0 (minor); only drop rows where valence or energy are exactly zero
    zero_mask = (trio_df["valence"] == 0) | (trio_df["energy"] == 0)
    trio_df = trio_df[~zero_mask]

    if trio_df.empty:
        st.info("No valence, energy, and mode values remain after filtering out zero entries.")
    else:
        mode_labels = trio_df["mode"].round().astype("Int64").map({0: "Minor", 1: "Major"}).fillna("Other")
        trio_df = trio_df.assign(mode_label=mode_labels)

        # Add song info to hover
        # Try to join name/artist from df if available
        hover_cols = []
        if {'name', 'artist'}.issubset(df.columns):
            trio_df = trio_df.join(df[['name', 'artist']], how='left')
            hover_cols = ['name', 'artist']
        fig = px.scatter(
            trio_df,
            x="valence",
            y="energy",
            color="mode_label",
            color_discrete_map=METRIC_COLOR_MAP,
            range_x=(0, 1),
            range_y=(0, 1),
            labels={"valence": "Valence", "energy": "Energy", "mode_label": "Mode"},
            hover_data=hover_cols
        )

        fig.update_traces(marker=dict(size=12, opacity=0.85, line=dict(width=0)))
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            paper_bgcolor="rgba(0, 0, 0, 0)",
            plot_bgcolor="rgba(0, 0, 0, 0)",
            font=dict(color=SPOTIFY_TEXT),
            height=420,
            margin=dict(l=40, r=20, t=60, b=40),
            legend=dict(
                title="Mode",
                orientation="h",
                yanchor="top",
                y=-0.25,
                x=0.5,
                xanchor="center"
            ),
            xaxis=dict(showgrid=True, gridcolor=SPOTIFY_GRID, gridwidth=1),
            yaxis=dict(showgrid=True, gridcolor=SPOTIFY_GRID, gridwidth=1),
        )

        st.plotly_chart(fig, use_container_width=True)

# Additional visualisation: Playlist's Tempo Distribution (Plotly)
st.markdown("#### Tempo Distribution")

# Extract and sanitize tempo values; exclude invalid zeros
tempo_series = pd.to_numeric(df["tempo"], errors="coerce") if "tempo" in df.columns else pd.Series(dtype="float64")
tempo_series = tempo_series.dropna()
tempo_series = tempo_series[tempo_series > 0]

if tempo_series.empty:
    st.info("Tempo data unavailable or non-numeric in this playlist.")
else:
    # Toggle: False -> Histogram, True -> Violin (fallback to checkbox if toggle not available)
    try:
        show_violin = st.toggle("Violin view", value=False, help="Switch between histogram and violin plot")
    except Exception:
        show_violin = st.checkbox("Violin view", value=False, help="Switch between histogram and violin plot")


    # Add song info to hover for tempo plots
    if {'name', 'artist', 'tempo'}.issubset(df.columns):
        valid_tempo_mask = pd.to_numeric(df['tempo'], errors='coerce').notna() & (pd.to_numeric(df['tempo'], errors='coerce') > 0)
        tempo_df = df.loc[valid_tempo_mask, ['tempo', 'name', 'artist']].copy()
        tempo_df['tempo'] = pd.to_numeric(tempo_df['tempo'], errors='coerce')
    else:
        tempo_df = pd.DataFrame({"tempo": tempo_series})

    hover_cols = [c for c in ['name', 'artist'] if c in tempo_df.columns]

    if show_violin:
        fig = px.violin(
            tempo_df,
            y="tempo",
            box=True,
            color_discrete_sequence=[PRIMARY_COLOR],
            hover_data=hover_cols
        )
        fig.update_yaxes(title="Tempo (BPM)")
        fig.update_xaxes(title="Density", showticklabels=False)
    else:
        fig = px.histogram(
            tempo_df,
            x="tempo",
            nbins=30,
            color_discrete_sequence=[PRIMARY_COLOR],
            hover_data=hover_cols
        )
        fig.update_traces(marker_line_color="#FFFFFF", marker_line_width=1)
        fig.update_yaxes(title="Count")
        fig.update_xaxes(title="Tempo (BPM)")

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(color=SPOTIFY_TEXT),
        height=420,
        margin=dict(l=40, r=20, t=60, b=40),
        xaxis=dict(showgrid=True, gridcolor=SPOTIFY_GRID, gridwidth=1),
        yaxis=dict(showgrid=True, gridcolor=SPOTIFY_GRID, gridwidth=1),
    )

    st.plotly_chart(fig, use_container_width=True)

render_nav_button(
    "pages/5_Playlist_Sculptor.py",
    "Open Sculptor →",
    icon="🪄",
    key="inspector_open_sculptor",
)