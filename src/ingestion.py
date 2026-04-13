import os  # Applied: Singular import as per "General Code Quality Guidelines #1"
import json
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import requests  # Applied: Singular import as per "General Code Quality Guidelines #1"

CACHE_DIR = "cache"
CACHE_METADATA_SUFFIX = ".meta.json"
AUDIO_FEATURE_COLUMNS = [
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "time_signature",
]


def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def get_cache_path(playlist_id):
    return os.path.join(CACHE_DIR, f"{playlist_id}.json")


def get_cache_metadata_path(playlist_id):
    return os.path.join(CACHE_DIR, f"{playlist_id}{CACHE_METADATA_SUFFIX}")


def load_from_cache(playlist_id):
    """Try to load playlist data from local JSON."""
    ensure_cache_dir()
    path = get_cache_path(playlist_id)
    if os.path.exists(path):
        # Check if cache is older than 24 hours (optional logic)
        # for now, just load it
        try:
            df = pd.read_json(path)
            print(f"Loaded {len(df)} tracks from cache: {playlist_id}")
            return df
        except Exception as e:
            print(f"Error loading cache: {e}")
            return None
    return None


def load_cache_metadata(playlist_id):
    """Load playlist ingestion metadata from local JSON."""
    ensure_cache_dir()
    path = get_cache_metadata_path(playlist_id)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache metadata: {e}")
            return None
    return None


def save_to_cache(playlist_id, df, metadata=None):
    """Save dataframe and optional ingestion metadata to local JSON."""
    ensure_cache_dir()
    path = get_cache_path(playlist_id)
    df.to_json(path)
    print(f"Cached {len(df)} tracks to {path}")
    if metadata is not None:
        metadata_path = get_cache_metadata_path(playlist_id)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)


def fetch_audio_features_reccobeats(track_ids, api_key=None):
    """
    Fetch audio features from Reccobeats API for a list of Spotify track IDs.
    """
    # Build comma-separated list for GET request
    ids_param = ','.join(track_ids)
    url = f"https://api.reccobeats.com/v1/audio-features?ids={ids_param}"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    print(f"[DEBUG] Requesting Reccobeats audio features for IDs: {ids_param}")
    print(f"[DEBUG] Request URL: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response text: {response.text[:500]}")  # Print first 500 chars for brevity
        response.raise_for_status()
        data = response.json()
        features = data.get("content", [])
        # Extract Spotify track ID from 'href' and add as 'spotify_id'
        for f in features:
            href = f.get("href", "")
            if "open.spotify.com/track/" in href:
                f["spotify_id"] = href.split("/track/")[-1]
        print(f"[DEBUG] Parsed features: {features}")
        return features
    except Exception as e:
        print(f"Error fetching audio features from Reccobeats: {e}")
        return []


def merge_tracks_with_audio_features(df_tracks, df_features):
    """Keep only tracks with Reccobeats audio features."""
    if df_tracks.empty or df_features.empty or 'spotify_id' not in df_features.columns:
        return df_tracks.iloc[0:0].copy()

    feature_cols = [
        col for col in df_features.columns if col in ['spotify_id', *AUDIO_FEATURE_COLUMNS]
    ]
    if 'spotify_id' not in feature_cols:
        return df_tracks.iloc[0:0].copy()

    df_features = df_features[feature_cols].drop_duplicates(subset='spotify_id', keep='first')
    return pd.merge(df_tracks, df_features, left_on='id', right_on='spotify_id', how='inner')


def build_ingestion_metadata(playlist_item_total, df_tracks, df_features, df_final):
    """Summarize which playlist items were excluded during ingestion."""
    spotify_track_total = len(df_tracks)
    audio_feature_track_total = 0
    if not df_features.empty and 'spotify_id' in df_features.columns:
        audio_feature_track_total = int(df_features['spotify_id'].dropna().nunique())

    kept_track_total = len(df_final)
    expected_total = playlist_item_total if playlist_item_total is not None else spotify_track_total
    unavailable_playlist_items = max(expected_total - spotify_track_total, 0)
    tracks_missing_audio_features = max(spotify_track_total - kept_track_total, 0)

    return {
        "playlist_item_total": expected_total,
        "spotify_track_total": spotify_track_total,
        "audio_feature_track_total": audio_feature_track_total,
        "kept_track_total": kept_track_total,
        "unavailable_playlist_items": unavailable_playlist_items,
        "tracks_missing_audio_features": tracks_missing_audio_features,
    }


def fetch_playlist_data(sp, playlist_id, force_refresh=False, reccobeats_api_key=None):
    """
    Main orchestration function.
    1. Check Cache.
    2. If no cache, fetch Tracks.
    3. Fetch Audio Features (Batched).
    4. Merge and Save.
    """
    if not force_refresh:
        df_cached = load_from_cache(playlist_id)
        if df_cached is not None:
            return df_cached

    print(f"Fetching fresh data for {playlist_id}...")

    # 1. Fetch all tracks (Pagination)
    tracks_data = []
    # Explicitly set limit to 100 to avoid limit=0 bug
    results = sp.playlist_items(playlist_id, additional_types=['track'], limit=100)
    playlist_item_total = results.get('total')
    tracks = results['items']

    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    # Parse track metadata
    for item in tracks:
        track = item.get('track')
        if not track or track['id'] is None:
            continue  # Skip local files or bad data
        tracks_data.append({
            'id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'uri': track['uri'],
            'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'external_url': track['external_urls'].get('spotify')
        })

    df_tracks = pd.DataFrame(tracks_data)

    if df_tracks.empty:
        return pd.DataFrame()  # Return empty if no tracks found

    # 2. Fetch Audio Features from Reccobeats (Batching 100 at a time)
    track_ids = df_tracks['id'].tolist()
    audio_features = []
    batch_size = 40
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i + batch_size]
        print(f"Requesting audio features for batch: {batch}")  # Debug: show batch
        features = fetch_audio_features_reccobeats(batch, api_key=reccobeats_api_key)
        print(f"Reccobeats response for batch: {features}")  # Debug: show response
        audio_features.extend([f for f in features if f is not None])

    df_features = pd.DataFrame(audio_features)
    print(f"Fetched {len(df_features)} audio features. Columns: {df_features.columns.tolist()}")  # Debug: show features DataFrame
    if not df_features.empty:
        print(df_features.head())  # Debug: show first few rows

    # 3. Merge
    # Merge on Spotify track ID (df_tracks['id'] <-> df_features['spotify_id'])
    df_final = merge_tracks_with_audio_features(df_tracks, df_features)
    metadata = build_ingestion_metadata(playlist_item_total, df_tracks, df_features, df_final)

    # 4. Cache
    save_to_cache(playlist_id, df_final, metadata=metadata)

    return df_final
