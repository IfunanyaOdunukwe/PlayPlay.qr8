import streamlit as st
import pandas as pd
from src.ingestion import load_from_cache
import plotly.graph_objects as go

st.title("Inspect & Visualise")

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
    st.warning("No cached data found for this playlist. Please ingest on 'Eat This Playlist' first.")
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
if "tempo" in df.columns and pd.api.types.is_numeric_dtype(df["tempo"]):
    tempo_max = df["tempo"].max()
    if pd.isna(tempo_max) or tempo_max <= 0:
        tempo_max = 1.0
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
                try:
                    val_num = float(val) if pd.notna(val) else 0.0
                except Exception:
                    val_num = 0.0
                v = max(0.0, min(1.0, val_num / tempo_max))
            else:
                try:
                    v = float(val) if pd.notna(val) else 0.0
                except Exception:
                    v = 0.0
                # Clamp to [0,1]
                v = max(0.0, min(1.0, v))

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
    st.info("Select one or more tracks above to view the radar chart.")
