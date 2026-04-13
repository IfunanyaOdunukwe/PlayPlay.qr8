from __future__ import annotations

from typing import Any, MutableMapping

PLAYLIST_NAME_KEY = "selected_playlist"
PLAYLIST_ID_KEY = "selected_playlist_id"
PLAYLIST_SOURCE_KEY = "selected_playlist_source"
PLAYLIST_DESCRIPTION_KEY = "selected_playlist_description"
PLAYLIST_OWNER_KEY = "selected_playlist_owner"
PLAYLIST_TRACK_TOTAL_KEY = "selected_playlist_track_total"
PLAYLIST_REFERENCE_KEY = "selected_playlist_reference"

PLAYLIST_STATE_KEYS = (
    PLAYLIST_NAME_KEY,
    PLAYLIST_ID_KEY,
    PLAYLIST_SOURCE_KEY,
    PLAYLIST_DESCRIPTION_KEY,
    PLAYLIST_OWNER_KEY,
    PLAYLIST_TRACK_TOTAL_KEY,
    PLAYLIST_REFERENCE_KEY,
)

SPOTIFY_CALLBACK_PAYLOAD_KEY = "spotify_callback_payload"

DEMO_PLAYLIST_WIDGET_KEY = "demo_playlist_widget"
SPOTIFY_LIBRARY_PLAYLIST_WIDGET_KEY = "spotify_library_playlist_widget"

BREAKDOWN_LAST_PLAYLIST_KEY = "last_playlist_id_for_df"
BREAKDOWN_SHOW_DF_PREFIX = "show_playlist_df_"

SCULPTOR_STATE_KEYS = (
    "sculptor_playlist_id",
    "sculptor_df_original",
    "sculptor_df_working",
    "sculptor_messages",
    "sculptor_pending_proposal",
    "sculptor_pending_df_preview",
    "sculptor_pending_comparison",
    "sculptor_session_count",
    "sculptor_do_approve",
    "sculptor_do_reject",
)

SPOTIFY_AUTH_STATE_KEYS = (
    "token_info",
    "user_playlists",
    "spotify_user_profile",
    "spotify_auth_error",
    SPOTIFY_CALLBACK_PAYLOAD_KEY,
    "spotify_failed_exchange_key",
    "spotify_pending_auth_state",
    "spotify_pending_auth_signature",
    "spotify_validated_credentials_signature",
)

MANUAL_SPOTIFY_INPUT_KEYS = (
    "manual_client_id",
    "manual_client_secret",
    "manual_redirect_uri",
)

SessionStateLike = MutableMapping[str, Any]


def get_playlist_owner_label(playlist: dict | None) -> str | None:
    if not playlist:
        return None

    owner = playlist.get("owner")
    if isinstance(owner, dict):
        return owner.get("display_name") or owner.get("id")
    return owner


def set_selected_playlist(
    session_state: SessionStateLike,
    playlist: dict,
    source: str,
    reference: str | None = None,
) -> None:
    session_state[PLAYLIST_NAME_KEY] = playlist["name"]
    session_state[PLAYLIST_ID_KEY] = playlist["id"]
    session_state[PLAYLIST_SOURCE_KEY] = source
    session_state[PLAYLIST_DESCRIPTION_KEY] = playlist.get("description")
    session_state[PLAYLIST_OWNER_KEY] = get_playlist_owner_label(playlist)
    session_state[PLAYLIST_TRACK_TOTAL_KEY] = (playlist.get("tracks") or {}).get("total")
    session_state[PLAYLIST_REFERENCE_KEY] = reference


def get_selected_playlist_snapshot(session_state: SessionStateLike) -> dict | None:
    playlist_id = session_state.get(PLAYLIST_ID_KEY)
    playlist_name = session_state.get(PLAYLIST_NAME_KEY)
    if not playlist_id or not playlist_name:
        return None

    return {
        "id": playlist_id,
        "name": playlist_name,
        "source": session_state.get(PLAYLIST_SOURCE_KEY),
        "description": session_state.get(PLAYLIST_DESCRIPTION_KEY),
        "owner": session_state.get(PLAYLIST_OWNER_KEY),
        "tracks": {"total": session_state.get(PLAYLIST_TRACK_TOTAL_KEY)},
        "reference": session_state.get(PLAYLIST_REFERENCE_KEY),
    }


def clear_selected_playlist(session_state: SessionStateLike) -> None:
    for key in PLAYLIST_STATE_KEYS:
        session_state.pop(key, None)


def clear_keys_with_prefix(session_state: SessionStateLike, prefix: str) -> None:
    for key in list(session_state.keys()):
        if isinstance(key, str) and key.startswith(prefix):
            session_state.pop(key, None)


def clear_breakdown_state(session_state: SessionStateLike) -> None:
    session_state.pop(BREAKDOWN_LAST_PLAYLIST_KEY, None)
    clear_keys_with_prefix(session_state, BREAKDOWN_SHOW_DF_PREFIX)


def clear_sculptor_state(session_state: SessionStateLike) -> None:
    for key in SCULPTOR_STATE_KEYS:
        session_state.pop(key, None)


def clear_playlist_dependent_state(session_state: SessionStateLike) -> None:
    clear_selected_playlist(session_state)
    clear_breakdown_state(session_state)
    clear_sculptor_state(session_state)
    session_state.pop(DEMO_PLAYLIST_WIDGET_KEY, None)
    session_state.pop(SPOTIFY_LIBRARY_PLAYLIST_WIDGET_KEY, None)


def store_spotify_callback_payload(
    session_state: SessionStateLike,
    code: str,
    state: str | None,
) -> None:
    session_state[SPOTIFY_CALLBACK_PAYLOAD_KEY] = {"code": code, "state": state}


def get_spotify_callback_payload(session_state: SessionStateLike) -> dict:
    return session_state.get(SPOTIFY_CALLBACK_PAYLOAD_KEY) or {}


def clear_spotify_callback_payload(session_state: SessionStateLike) -> None:
    session_state.pop(SPOTIFY_CALLBACK_PAYLOAD_KEY, None)


def clear_spotify_auth_state(
    session_state: SessionStateLike,
    *,
    include_manual_inputs: bool = False,
) -> None:
    for key in SPOTIFY_AUTH_STATE_KEYS:
        session_state.pop(key, None)

    if include_manual_inputs:
        for key in MANUAL_SPOTIFY_INPUT_KEYS:
            session_state.pop(key, None)