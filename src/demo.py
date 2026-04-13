from __future__ import annotations

import re
from html import unescape
from pathlib import Path

import pandas as pd
import requests
import spotipy

from src.audio_features import normalize_mode_series
from src.ingestion import (
    RECCOBEATS_BATCH_SIZE,
    build_ingestion_metadata,
    fetch_audio_features_reccobeats,
    fetch_playlist_data,
    load_from_cache,
    merge_tracks_with_audio_features,
    save_to_cache,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_PLAYLIST_DIR = REPO_ROOT / "demo_playlists"
DEMO_PLAYLIST_MANIFEST = DEMO_PLAYLIST_DIR / "manifest.csv"
CANONICAL_DEMO_COLUMNS = [
    "id",
    "name",
    "artist",
    "album",
    "uri",
    "image_url",
    "external_url",
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
    "spotify_id",
]


def _load_demo_manifest() -> pd.DataFrame:
    if not DEMO_PLAYLIST_MANIFEST.exists():
        raise FileNotFoundError(f"Missing demo playlist manifest: {DEMO_PLAYLIST_MANIFEST}")
    return pd.read_csv(DEMO_PLAYLIST_MANIFEST)


def _normalize_demo_playlist_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed:")].copy()
    df = df.drop(columns=["time_signature"], errors="ignore")

    if "track_name" in df.columns and "name" not in df.columns:
        df = df.rename(columns={"track_name": "name"})

    if "id" not in df.columns and "spotify_id" in df.columns:
        df["id"] = df["spotify_id"]
    if "spotify_id" not in df.columns and "id" in df.columns:
        df["spotify_id"] = df["id"]

    if "mode" in df.columns:
        df["mode"] = normalize_mode_series(df["mode"])

    for column in CANONICAL_DEMO_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    extra_columns = [column for column in df.columns if column not in CANONICAL_DEMO_COLUMNS]
    return df[CANONICAL_DEMO_COLUMNS + extra_columns]


def get_demo_playlists() -> list[dict]:
    manifest = _load_demo_manifest()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "owner": row["owner"],
            "tracks": {"total": int(row["track_total"])},
            "file_name": row["file_name"],
        }
        for _, row in manifest.iterrows()
    ]


def get_demo_playlist(playlist_id: str) -> dict:
    manifest = _load_demo_manifest()
    matches = manifest.loc[manifest["id"] == playlist_id]
    if matches.empty:
        raise KeyError(f"Unknown demo playlist: {playlist_id}")
    row = matches.iloc[0]
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "owner": row["owner"],
        "tracks": {"total": int(row["track_total"])},
        "file_name": row["file_name"],
    }


def get_demo_playlist_df(playlist_id: str) -> pd.DataFrame:
    playlist = get_demo_playlist(playlist_id)
    csv_path = DEMO_PLAYLIST_DIR / playlist["file_name"]
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing demo playlist CSV: {csv_path}")
    return _normalize_demo_playlist_df(pd.read_csv(csv_path))


def is_demo_playlist(playlist_id: str | None) -> bool:
    if not playlist_id:
        return False
    manifest = _load_demo_manifest()
    return bool((manifest["id"] == playlist_id).any())


def extract_playlist_id(raw_value: str) -> str | None:
    value = (raw_value or "").strip()
    if not value:
        return None
    if value.startswith("https://open.spotify.com/playlist/"):
        value = value.split("/playlist/", 1)[1]
        value = value.split("?", 1)[0]
    elif value.startswith("spotify:playlist:"):
        value = value.rsplit(":", 1)[-1]
    return value or None


def _get_playlist_metadata(sp: spotipy.Spotify, playlist_id: str) -> dict:
    payload = sp.playlist(
        playlist_id,
        fields="id,name,description,owner(display_name,id),tracks(total)",
    )
    owner = payload.get("owner") or {}
    return {
        "id": payload["id"],
        "name": payload["name"],
        "description": payload.get("description") or "Spotify playlist.",
        "owner": owner.get("display_name") or owner.get("id") or "Spotify",
        "tracks": {"total": payload.get("tracks", {}).get("total", 0)},
    }


def _fetch_public_playlist_html(playlist_id: str) -> str:
    response = requests.get(
        f"https://open.spotify.com/playlist/{playlist_id}",
        timeout=20,
    )
    response.raise_for_status()
    return response.text


def _scrape_public_playlist_metadata(playlist_id: str) -> dict:
    html = _fetch_public_playlist_html(playlist_id)

    title_match = re.search(
        r'<meta\s+property="og:title"\s+content="([^"]+)"',
        html,
        re.IGNORECASE,
    )
    description_match = re.search(
        r'<meta\s+property="og:description"\s+content="([^"]+)"',
        html,
        re.IGNORECASE,
    )
    owner_match = re.search(r'https://open\.spotify\.com/user/([^"/?]+)', html)
    track_ids = list(dict.fromkeys(re.findall(r'https://open\.spotify\.com/track/([A-Za-z0-9]+)', html)))

    if not track_ids:
        raise ValueError("Could not extract tracks from that public playlist page.")

    return {
        "id": playlist_id,
        "name": unescape(title_match.group(1)) if title_match else f"Public Playlist {playlist_id}",
        "description": unescape(description_match.group(1)) if description_match else "Public Spotify playlist.",
        "owner": owner_match.group(1) if owner_match else "Spotify",
        "tracks": {"total": len(track_ids)},
        "track_ids": track_ids,
    }


def get_public_playlist(sp: spotipy.Spotify, playlist_reference: str) -> dict:
    playlist_id = extract_playlist_id(playlist_reference)
    if not playlist_id:
        raise ValueError("Enter a valid Spotify playlist URL or playlist ID.")

    try:
        return _get_playlist_metadata(sp, playlist_id)
    except Exception:
        try:
            scraped = _scrape_public_playlist_metadata(playlist_id)
        except Exception as exc:
            raise ValueError(
                "Could not load that playlist. Make sure the URL is correct and the playlist is public."
            ) from exc
        return {
            "id": scraped["id"],
            "name": scraped["name"],
            "description": scraped["description"],
            "owner": scraped["owner"],
            "tracks": scraped["tracks"],
        }


def _build_tracks_dataframe(sp: spotipy.Spotify, track_ids: list[str]) -> pd.DataFrame:
    tracks_data = []
    for start in range(0, len(track_ids), 50):
        batch_ids = track_ids[start:start + 50]
        response = sp.tracks(batch_ids)
        for track in response.get("tracks", []):
            if not track or track.get("id") is None:
                continue
            tracks_data.append(
                {
                    "id": track["id"],
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "album": track["album"]["name"],
                    "uri": track["uri"],
                    "image_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                    "external_url": track["external_urls"].get("spotify"),
                }
            )
    return pd.DataFrame(tracks_data)


def _merge_tracks_with_features(
    df_tracks: pd.DataFrame,
    reccobeats_api_key: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    if df_tracks.empty:
        empty_df = pd.DataFrame()
        return empty_df, build_ingestion_metadata(0, empty_df, empty_df, empty_df)

    track_ids = df_tracks["id"].tolist()
    audio_features: list[dict] = []
    for start in range(0, len(track_ids), RECCOBEATS_BATCH_SIZE):
        batch = track_ids[start : start + RECCOBEATS_BATCH_SIZE]
        features = fetch_audio_features_reccobeats(batch, api_key=reccobeats_api_key)
        audio_features.extend([feature for feature in features if feature is not None])

    df_features = pd.DataFrame(audio_features)
    df_final = merge_tracks_with_audio_features(df_tracks, df_features)
    metadata = build_ingestion_metadata(len(df_tracks), df_tracks, df_features, df_final)
    return df_final, metadata


def _fetch_playlist_data_from_public_page(
    sp: spotipy.Spotify,
    playlist_id: str,
    reccobeats_api_key: str | None = None,
) -> pd.DataFrame:
    scraped = _scrape_public_playlist_metadata(playlist_id)
    df_tracks = _build_tracks_dataframe(sp, scraped["track_ids"])
    df_final, metadata = _merge_tracks_with_features(df_tracks, reccobeats_api_key=reccobeats_api_key)
    metadata["playlist_item_total"] = scraped["tracks"]["total"]
    metadata["unavailable_playlist_items"] = max(scraped["tracks"]["total"] - len(df_tracks), 0)
    save_to_cache(playlist_id, df_final, metadata=metadata)
    return df_final


def fetch_spotify_playlist_data_with_fallback(
    sp: spotipy.Spotify,
    playlist_id: str,
    force_refresh: bool = False,
    reccobeats_api_key: str | None = None,
) -> pd.DataFrame:
    if not force_refresh:
        df_cached = load_from_cache(playlist_id)
        if df_cached is not None:
            return df_cached

    try:
        return fetch_playlist_data(
            sp,
            playlist_id,
            force_refresh=True,
            reccobeats_api_key=reccobeats_api_key,
        )
    except Exception:
        return _fetch_playlist_data_from_public_page(
            sp,
            playlist_id,
            reccobeats_api_key=reccobeats_api_key,
        )


def load_playlist_df(playlist_id: str, playlist_source: str) -> pd.DataFrame | None:
    """Load a playlist DataFrame from demo CSV or JSON cache.

    This is the shared entry point used by pages that need read-only
    access to an already-ingested playlist.
    """
    if playlist_source == "demo":
        return get_demo_playlist_df(playlist_id)
    return load_from_cache(playlist_id)
