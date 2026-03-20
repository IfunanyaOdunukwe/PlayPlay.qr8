import streamlit as st
import spotipy
import pandas as pd
from src.ingestion import load_from_cache
from src.auth import SpotifyAuthManager
from src.llm_providers import get_available_providers, get_chat_model
from src.agent import generate_response, apply_proposal, compute_comparison, SculptorProposal

st.title("Playlist Sculptor")

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
playlist_name = st.session_state.get("selected_playlist")
playlist_id = st.session_state.get("selected_playlist_id")

if not playlist_name or not playlist_id:
    st.error("No playlist selected. Please go back and select a playlist.")
    st.stop()

_cache_key = f"_cached_df_{playlist_id}"
if _cache_key not in st.session_state:
    st.session_state[_cache_key] = load_from_cache(playlist_id)
df_cached = st.session_state[_cache_key]
if df_cached is None or df_cached.empty:
    st.warning("No cached data found. Please ingest on the Playlist Breakdown page first.")
    st.stop()

# ---------------------------------------------------------------------------
# Session state initialisation (resets when playlist changes)
# ---------------------------------------------------------------------------
if (
    "sculptor_df_original" not in st.session_state
    or st.session_state.get("sculptor_playlist_id") != playlist_id
):
    st.session_state["sculptor_df_original"] = df_cached.copy()
    st.session_state["sculptor_df_working"] = df_cached.copy()
    st.session_state["sculptor_messages"] = []
    st.session_state["sculptor_pending_proposal"] = None
    st.session_state["sculptor_pending_df_preview"] = None
    st.session_state["sculptor_pending_comparison"] = None
    st.session_state["sculptor_playlist_id"] = playlist_id

df_working: pd.DataFrame = st.session_state["sculptor_df_working"]

# ---------------------------------------------------------------------------
# Process approve / reject from previous rerun
# ---------------------------------------------------------------------------
def _resolve_pending(apply: bool):
    """Clear pending proposal state; optionally apply the preview."""
    if apply:
        st.session_state["sculptor_df_working"] = st.session_state["sculptor_pending_df_preview"]
    msg = "Changes applied." if apply else "Changes discarded."
    st.session_state["sculptor_messages"].append({"role": "assistant", "content": msg})
    st.session_state["sculptor_pending_proposal"] = None
    st.session_state["sculptor_pending_df_preview"] = None
    st.session_state["sculptor_pending_comparison"] = None

if st.session_state.get("sculptor_do_approve"):
    _resolve_pending(apply=True)
    st.session_state["sculptor_do_approve"] = False
    df_working = st.session_state["sculptor_df_working"]

if st.session_state.get("sculptor_do_reject"):
    _resolve_pending(apply=False)
    st.session_state["sculptor_do_reject"] = False

# ---------------------------------------------------------------------------
# Sidebar — LLM configuration
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("LLM Configuration")

    providers = get_available_providers()
    provider_labels = [p["label"] for p in providers]
    provider_ids = [p["id"] for p in providers]

    selected_label = st.selectbox("Provider", provider_labels)
    selected_provider = provider_ids[provider_labels.index(selected_label)]
    provider_info = providers[provider_labels.index(selected_label)]

    api_key = None
    model_name = None

    if provider_info["needs_key"]:
        secret_key_name = (
            "openai_api_key" if selected_provider == "openai" else "google_api_key"
        )
        # Try secrets first
        try:
            api_key = st.secrets.get(secret_key_name)
        except FileNotFoundError:
            api_key = None

        if not api_key:
            api_key = st.text_input(
                f"{selected_label} API Key",
                type="password",
                help=f"Or add `{secret_key_name}` to `.streamlit/secrets.toml`.",
            )
    else:
        model_name = st.text_input("Ollama Model Name", value="llama3")

    llm_ready = bool(api_key) if provider_info["needs_key"] else True

    if not llm_ready:
        st.warning("Enter an API key to enable the sculptor.")

# ---------------------------------------------------------------------------
# Working playlist stats bar
# ---------------------------------------------------------------------------
st.subheader(f"Working Playlist: {playlist_name}")

stat_cols = st.columns(5)
stat_features = [
    ("Tracks", None, lambda df: str(len(df))),
    ("Avg Energy", "energy", lambda df: f"{pd.to_numeric(df['energy'], errors='coerce').mean():.0%}"),
    ("Avg Valence", "valence", lambda df: f"{pd.to_numeric(df['valence'], errors='coerce').mean():.0%}"),
    ("Avg Danceability", "danceability", lambda df: f"{pd.to_numeric(df['danceability'], errors='coerce').mean():.0%}"),
    ("Avg Tempo", "tempo", lambda df: f"{pd.to_numeric(df['tempo'], errors='coerce').mean():.0f} BPM"),
]

for col, (label, feat, fmt_fn) in zip(stat_cols, stat_features):
    if feat and feat not in df_working.columns:
        continue
    with col:
        st.metric(label=label, value=fmt_fn(df_working))

st.divider()

# ---------------------------------------------------------------------------
# Chat interface
# ---------------------------------------------------------------------------
# Render history
for msg in st.session_state["sculptor_messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Render pending proposal (if any)
pending = st.session_state.get("sculptor_pending_proposal")
comparison = st.session_state.get("sculptor_pending_comparison")

if pending and comparison:
    with st.expander("View proposal details", expanded=True):
        st.write(pending.reasoning)

        st.caption("Before / After comparison")
        comp_rows = []
        for metric, (before, after) in comparison.items():
            if before is None and after is None:
                continue
            label = metric.replace("_", " ").title()
            comp_rows.append({"Metric": label, "Before": before, "After": after})
        if comp_rows:
            st.table(pd.DataFrame(comp_rows))

        # Show affected tracks
        all_affected_ids = set()
        for op in pending.operations:
            all_affected_ids.update(op.track_ids)
        if all_affected_ids:
            affected = df_working[df_working["id"].isin(all_affected_ids)]
            display_cols = [c for c in ["name", "artist", "energy", "valence", "tempo"] if c in affected.columns]
            if display_cols:
                st.caption("Affected tracks")
                st.dataframe(affected[display_cols], use_container_width=True, hide_index=True)

    btn_cols = st.columns(2)
    with btn_cols[0]:
        if st.button("Approve", type="primary", use_container_width=True):
            st.session_state["sculptor_do_approve"] = True
            st.rerun()
    with btn_cols[1]:
        if st.button("Reject", use_container_width=True):
            st.session_state["sculptor_do_reject"] = True
            st.rerun()

# Chat input
if prompt := st.chat_input("Ask about the playlist or tell me how to reshape it...", disabled=not llm_ready):
    # Add user message
    st.session_state["sculptor_messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                llm = get_chat_model(selected_provider, api_key, model_name)
                result = generate_response(
                    llm,
                    df_working,
                    st.session_state["sculptor_messages"],
                    prompt,
                )

                if isinstance(result, SculptorProposal):
                    df_preview = apply_proposal(df_working, result)
                    comp = compute_comparison(df_working, df_preview)

                    # Store pending
                    st.session_state["sculptor_pending_proposal"] = result
                    st.session_state["sculptor_pending_df_preview"] = df_preview
                    st.session_state["sculptor_pending_comparison"] = comp

                    st.session_state["sculptor_messages"].append(
                        {"role": "assistant", "content": result.summary}
                    )
                else:
                    # Conversational response
                    st.session_state["sculptor_messages"].append(
                        {"role": "assistant", "content": result}
                    )

                st.rerun()
            except Exception as e:
                st.error(f"Error generating response: {e}")

# ---------------------------------------------------------------------------
# Push to Spotify
# ---------------------------------------------------------------------------
df_original = st.session_state["sculptor_df_original"]
has_changes = len(df_working) != len(df_original) or not df_working["id"].equals(df_original["id"])

if has_changes:
    st.divider()
    st.subheader("Push to Spotify")

    new_name = st.text_input(
        "New playlist name",
        value=f"{playlist_name} (Sculpted)",
    )

    if st.button("Create Playlist on Spotify", type="primary"):
        token_info = st.session_state.get("token_info")
        if not token_info or not SpotifyAuthManager.is_token_valid(token_info):
            st.error("Spotify authentication expired. Please reconnect on the Connect page.")
        else:
            try:
                sp = spotipy.Spotify(auth=token_info["access_token"])
                user_id = sp.current_user()["id"]
                new_playlist = sp.user_playlist_create(user_id, new_name, public=False)
                new_playlist_id = new_playlist["id"]

                # Add tracks in batches of 100
                uris = df_working["uri"].tolist()
                for i in range(0, len(uris), 100):
                    sp.playlist_add_items(new_playlist_id, uris[i : i + 100])

                playlist_url = new_playlist["external_urls"]["spotify"]
                st.success(f"Created **{new_name}** with {len(uris)} tracks!")
                st.link_button("Open in Spotify", playlist_url)
            except spotipy.SpotifyException as e:
                if e.http_status == 403:
                    st.error(
                        "Your session lacks playlist write permissions. "
                        "Please disconnect and reconnect on the Connect & Select page."
                    )
                else:
                    st.error(f"Spotify error: {e}")
            except Exception as e:
                st.error(f"Error creating playlist: {e}")
