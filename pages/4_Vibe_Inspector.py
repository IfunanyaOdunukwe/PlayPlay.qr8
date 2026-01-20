import streamlit as st
import pandas as pd
from src.ingestion import load_from_cache
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt

st.title("Vibe Inspector")

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

# Ensure a playlist is selected
playlist_name = st.session_state.get('selected_playlist')
playlist_id = st.session_state.get('selected_playlist_id')

if not playlist_name or not playlist_id:
    st.error("No playlist selected. Please go back and select a playlist.")
    st.stop()

st.write(f"**Selected Playlist:** {playlist_name}")
st.write(f"**Playlist ID:** {playlist_id}")

# Load cached data for the selected playlist
df = load_from_cache(playlist_id)
if df is None or df.empty:
    st.warning("No cached data found for this playlist. Please ingest on Playlist Breakdown first.")
    st.stop()

# Prepare track options (use ID for uniqueness, display as "name — artist")
if not {'id', 'name', 'artist'}.issubset(df.columns):
    st.error("Cached data is missing required columns ('id', 'name', 'artist').")
    st.stop()

track_display = {row['id']: f"{row['name']} — {row['artist']}" for _, row in df[['id', 'name', 'artist']].iterrows()}
selected_ids = st.multiselect(
    "Select tracks to visualize",
    options=list(track_display.keys()),
    format_func=lambda x: track_display.get(x, x),
    help="Search and select one or more tracks to plot on the radar chart.",
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
    "Tempo normalization: each track's BPM is divided by the highest BPM in the current playlist and clamped to [0, 1] so it can be plotted alongside 0–1 metrics."
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
        height=520,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
            ),
            angularaxis=dict(
                rotation=90,
                tickfont=dict(size=12),
            ),
        ),
        showlegend=True,
        margin=dict(l=60, r=60, t=40, b=60),
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select one or more tracks to view the radar chart.")

# Additional visualisation: Playlist's Tempo Distribution (Seaborn)
st.subheader("Tempo Distribution For Playlist")

# Extract and sanitize tempo values; exclude invalid zeros
tempo_series = pd.to_numeric(df["tempo"], errors="coerce") if "tempo" in df.columns else pd.Series(dtype="float64")
tempo_series = tempo_series.dropna()
tempo_series = tempo_series[tempo_series > 0]

if tempo_series.empty:
    st.info("Tempo data unavailable or non-numeric in this playlist.")
else:
    # Toggle: False -> Histogram, True -> Violin (fallback to checkbox if toggle not available)
    try:
        show_violin = st.toggle("Show as violin", value=False, help="Toggle to switch between histogram and violin plot")
    except Exception:
        show_violin = st.checkbox("Show as violin", value=False, help="Toggle to switch between histogram and violin plot")

    # Prepare figure (smaller, screen-friendly)
    sns.set_theme(style="whitegrid")
    sns.set_context("paper", font_scale=0.8)
    fig, ax = plt.subplots(figsize=(5, 2.6))

    if show_violin:
        sns.violinplot(data=pd.DataFrame({"tempo": tempo_series}), y="tempo", inner="box", cut=0, ax=ax, color="#4C78A8")
        ax.set_title("Tempo Distribution (Violin)")
    else:
        sns.histplot(tempo_series, bins=30, kde=True, ax=ax, color="#4C78A8")
        ax.set_title("Tempo Distribution (Histogram)")

    if show_violin:
        ax.set_ylabel("Tempo (BPM)")
    else:
        ax.set_ylabel("Count")
    ax.set_xlabel("Tempo (BPM)")
    plt.tight_layout(pad=0.4)

    st.pyplot(fig, use_container_width=False, clear_figure=True)
