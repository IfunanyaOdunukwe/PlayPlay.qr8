from __future__ import annotations

from html import escape

import streamlit as st

SPOTIFY_GREEN = "#1ED760"
SPOTIFY_GREEN_HOVER = "#18C956"
SPOTIFY_WHITE = "#FFFFFF"
SPOTIFY_BLACK = "#191414"
SPOTIFY_CANVAS = SPOTIFY_BLACK
SPOTIFY_PANEL = "#000000"
SPOTIFY_PANEL_SOFT = "#003366"
SPOTIFY_CORAL = "#FF6F61"
SPOTIFY_TEXT = SPOTIFY_WHITE
SPOTIFY_MUTED = "#B3B3B3"
SPOTIFY_BORDER = "rgba(255, 255, 255, 0.08)"
SPOTIFY_GRID = "rgba(255, 255, 255, 0.14)"
SPOTIFY_INPUT_BG = "rgba(0, 0, 0, 0.46)"
SPOTIFY_NAV = "#121A15"
SPOTIFY_NAV_HOVER = "#18231D"
SPOTIFY_FONT_STACK = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif'

SPOTIFY_PLOTLY_TEMPLATE = "plotly_dark"
SPOTIFY_PLOTLY_COLORWAY = [
    SPOTIFY_GREEN,
    SPOTIFY_PANEL_SOFT,
    SPOTIFY_CORAL,
    SPOTIFY_TEXT,
    SPOTIFY_MUTED,
]
SPOTIFY_METRIC_COLOR_MAP = {
    "Major": SPOTIFY_GREEN,
    "Minor": SPOTIFY_PANEL_SOFT,
    "Other": SPOTIFY_CORAL,
}


def apply_spotify_theme() -> None:
    st.markdown(
        f"""
        <style>
            html, body, [class*="css"], [data-testid="stAppViewContainer"],
            [data-testid="stSidebar"], [data-testid="stMarkdownContainer"],
            [data-testid="stText"], [data-testid="stCaptionContainer"],
            p, li, label, span, button, input, textarea, select, a,
            h1, h2, h3, h4, h5, h6, div {{
                font-family: {SPOTIFY_FONT_STACK};
            }}

            [data-testid="stAppViewContainer"] {{
                background: {SPOTIFY_CANVAS};
                color: {SPOTIFY_TEXT};
            }}

            [data-testid="stHeader"] {{
                background: rgba(25, 20, 20, 0.94);
                border-bottom: 1px solid {SPOTIFY_BORDER};
                backdrop-filter: blur(10px);
            }}

            [data-testid="stSidebar"] {{
                background: {SPOTIFY_PANEL};
                border-right: 1px solid {SPOTIFY_BORDER};
            }}

            [data-testid="stSidebar"] * {{
                color: {SPOTIFY_TEXT};
            }}

            .block-container {{
                padding-top: 2.1rem;
            }}

            h1, h2, h3 {{
                color: {SPOTIFY_TEXT};
                letter-spacing: -0.02em;
                font-weight: 700;
            }}

            p, li, [data-testid="stCaptionContainer"], label {{
                color: #E8E8E8;
            }}

            a {{
                color: {SPOTIFY_GREEN};
            }}

            a:hover {{
                color: {SPOTIFY_CORAL};
            }}

            hr {{
                border-color: {SPOTIFY_BORDER};
            }}

            div.stButton > button {{
                border: none;
                border-radius: 999px;
                font-weight: 700;
                padding: 0.6rem 1.15rem;
            }}

            div.stButton > button[kind="primary"],
            button[kind="primary"] {{
                background: {SPOTIFY_GREEN};
                color: #000000;
                box-shadow: 0 10px 24px rgba(30, 215, 96, 0.18);
            }}

            div.stButton > button[kind="primary"]:hover,
            button[kind="primary"]:hover {{
                background: {SPOTIFY_GREEN_HOVER};
                color: #000000;
            }}

            div.stButton > button[kind="primary"]:focus,
            button[kind="primary"]:focus {{
                box-shadow: 0 0 0 0.2rem rgba(30, 215, 96, 0.24);
            }}

            div.stButton > button[kind="secondary"],
            button[kind="secondary"],
            div.stButton > button:not([kind]) {{
                background: {SPOTIFY_NAV};
                color: {SPOTIFY_TEXT};
                border: 1px solid {SPOTIFY_GREEN};
                padding: 0.48rem 0.95rem;
                font-size: 0.92rem;
                box-shadow: 0 8px 18px rgba(0, 0, 0, 0.22);
            }}

            div.stButton > button[kind="secondary"]:hover,
            button[kind="secondary"]:hover,
            div.stButton > button:not([kind]):hover {{
                background: {SPOTIFY_NAV_HOVER};
                color: {SPOTIFY_TEXT};
                border-color: {SPOTIFY_GREEN};
            }}

            div.stButton > button[kind="secondary"]:focus,
            button[kind="secondary"]:focus,
            div.stButton > button:not([kind]):focus {{
                box-shadow: 0 0 0 0.2rem rgba(30, 215, 96, 0.2);
            }}

            .stTextInput input,
            .stTextArea textarea,
            .stNumberInput input,
            div[data-baseweb="select"] > div,
            div[data-baseweb="base-input"] > div,
            div[data-baseweb="input"] > div {{
                background: {SPOTIFY_INPUT_BG};
                color: {SPOTIFY_TEXT};
                border: 1px solid {SPOTIFY_BORDER};
                border-radius: 14px;
            }}

            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder,
            .stNumberInput input::placeholder {{
                color: {SPOTIFY_MUTED};
            }}

            [data-testid="stChatInput"] {{
                background: transparent;
            }}

            [data-testid="stBottom"],
            [data-testid="stBottom"] > div,
            [data-testid="stBottom"] > div > div,
            [data-testid="stBottomBlockContainer"] {{
                background: {SPOTIFY_CANVAS} !important;
            }}

            [data-testid="stBottomBlockContainer"] {{
                border-top: 1px solid {SPOTIFY_BORDER};
            }}

            [data-testid="stChatInput"] > div {{
                background: {SPOTIFY_INPUT_BG} !important;
                border: 1px solid {SPOTIFY_BORDER} !important;
                box-shadow: none !important;
            }}

            [data-testid="stChatInput"] > div:focus-within {{
                border-color: rgba(30, 215, 96, 0.5) !important;
            }}

            [data-testid="stChatInput"] [data-baseweb="textarea"],
            [data-testid="stChatInput"] [data-baseweb="base-input"],
            [data-testid="stChatInput"] [data-baseweb="input"],
            [data-testid="stChatInput"] [data-baseweb="textarea"] > div,
            [data-testid="stChatInput"] [data-baseweb="base-input"] > div,
            [data-testid="stChatInput"] [data-baseweb="input"] > div {{
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }}

            [data-testid="stChatInput"] textarea,
            [data-testid="stChatInput"] input,
            [data-testid="stChatInputTextArea"],
            [data-testid="stChatInput"] [data-baseweb="textarea"] > div,
            [data-testid="stChatInput"] [data-baseweb="input"] > div {{
                background: transparent !important;
                color: {SPOTIFY_TEXT} !important;
                border: none !important;
                border-radius: 18px;
                box-shadow: none !important;
                -webkit-appearance: none !important;
                appearance: none !important;
                -webkit-box-shadow: 0 0 0 1000px transparent inset !important;
            }}

            [data-testid="stChatInput"] textarea::placeholder,
            [data-testid="stChatInput"] input::placeholder,
            [data-testid="stChatInputTextArea"]::placeholder {{
                color: {SPOTIFY_MUTED};
            }}

            [data-baseweb="tag"] {{
                background: rgba(0, 51, 102, 0.35);
                color: {SPOTIFY_TEXT};
                border: 1px solid rgba(255, 111, 97, 0.24);
            }}

            [data-testid="stMetric"] {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid {SPOTIFY_BORDER};
                border-radius: 18px;
                padding: 0.85rem 1rem;
            }}

            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"] {{
                color: {SPOTIFY_TEXT};
            }}

            [data-testid="stExpander"] {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid {SPOTIFY_BORDER};
                border-radius: 16px;
            }}

            [data-baseweb="tab-list"] {{
                gap: 0.5rem;
            }}

            [data-baseweb="tab"] {{
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid transparent;
                border-radius: 999px;
                color: {SPOTIFY_MUTED};
                padding-inline: 1rem;
            }}

            [aria-selected="true"][data-baseweb="tab"] {{
                background: rgba(0, 51, 102, 0.7);
                border-color: rgba(255, 111, 97, 0.45);
                color: {SPOTIFY_TEXT};
            }}

            .spotify-metrics-panel {{
                margin-top: 0.7rem;
                margin-bottom: 0.7rem;
                padding: 0.7rem 1rem;
                border-radius: 16px;
                border: 1px solid rgba(255, 111, 97, 0.18);
                background: {SPOTIFY_PANEL_SOFT};
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.13);
                max-width: 700px;
            }}

            .spotify-metrics-kicker {{
                display: inline-block;
                margin-bottom: 0.55rem;
                padding: 0.28rem 0.72rem;
                border-radius: 999px;
                background: {SPOTIFY_CORAL};
                color: {SPOTIFY_BLACK};
                font-size: 0.82rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }}

            .spotify-metrics-panel h2 {{
                margin: 0;
                color: {SPOTIFY_TEXT};
            }}

            .spotify-metrics-intro {{
                margin-top: 0.5rem;
                margin-bottom: 1rem;
                color: #EDEDED;
                max-width: 58rem;
            }}

            .spotify-metrics-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.5rem;
            }}

            .spotify-metric-card {{
                min-height: unset;
                padding: 0.5rem 0.7rem;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                background: rgba(0, 0, 0, 0.18);
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
                min-width: 0;
            }}

            .spotify-metric-card strong {{
                display: block;
                margin-bottom: 0.35rem;
                color: {SPOTIFY_TEXT};
                font-size: 1rem;
            }}

            .spotify-metric-card span {{
                color: {SPOTIFY_MUTED};
                line-height: 1.5;
            }}

            .spotify-helper-panel {{
                margin-top: 0.4rem;
                padding: 1.2rem;
                border-radius: 24px;
                border: 1px solid rgba(30, 215, 96, 0.22);
                background: rgba(0, 51, 102, 0.42);
                box-shadow: 0 18px 48px rgba(0, 0, 0, 0.24);
            }}

            .spotify-empty-chat-shell {{
                min-height: clamp(220px, 34vh, 340px);
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0.35rem 0 1rem;
            }}

            .spotify-chat-empty-panel {{
                width: min(100%, 54rem);
                margin: 0;
            }}

            .spotify-helper-kicker {{
                display: inline-block;
                margin-bottom: 0.6rem;
                padding: 0.28rem 0.72rem;
                border-radius: 999px;
                background: rgba(255, 111, 97, 0.92);
                color: {SPOTIFY_BLACK};
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }}

            .spotify-helper-panel h3 {{
                margin: 0;
                font-size: 1.45rem;
            }}

            .spotify-helper-copy {{
                margin-top: 0.55rem;
                margin-bottom: 1rem;
                max-width: 46rem;
                color: #EDEDED;
                line-height: 1.6;
            }}

            .spotify-helper-grid {{
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.8rem;
            }}

            .spotify-helper-grid-compact {{
                grid-template-columns: 1fr;
                gap: 0.65rem;
            }}

            .spotify-helper-card {{
                min-height: 100%;
                padding: 0.95rem 1rem;
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                background: rgba(0, 0, 0, 0.28);
            }}

            .spotify-helper-card strong {{
                display: block;
                margin-bottom: 0.45rem;
                color: {SPOTIFY_TEXT};
                font-size: 0.95rem;
            }}

            .spotify-helper-card span {{
                display: block;
                color: {SPOTIFY_MUTED};
                line-height: 1.55;
                font-size: 0.95rem;
            }}

            .spotify-helper-footer {{
                margin-top: 0.85rem;
                color: {SPOTIFY_MUTED};
                font-size: 0.92rem;
            }}

            .spotify-current-playlist {{
                margin-top: 0.15rem;
                margin-bottom: 0.4rem;
                padding: 0;
                border: none;
                background: transparent;
                box-shadow: none;
                overflow: hidden;
            }}

            .spotify-current-playlist-name {{
                display: inline-flex;
                align-items: center;
                gap: 0.63rem;
                padding: 0.45rem 0.93rem;
                border-radius: 999px;
                border: 1px solid #ff2bd6;
                background: rgba(24, 8, 22, 0.92);
                box-shadow: inset 0 0 0.65rem rgba(30, 215, 96, 0.36), 0 0 0.55rem rgba(255, 43, 214, 0.32);
                color: {SPOTIFY_TEXT};
                font-size: 1.25rem;
                font-weight: 600;
                line-height: 1.15;
                max-width: 100%;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}

            .spotify-current-playlist-name::before {{
                content: "";
                width: 0.63rem;
                height: 0.63rem;
                border-radius: 999px;
                background: #1ed760;
                box-shadow: 0 0 0 0.27rem rgba(30, 215, 96, 0.34);
                flex: 0 0 auto;
            }}

            .spotify-current-playlist-kicker {{
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                margin-bottom: 0.75rem;
                padding: 0.28rem 0.72rem;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.08);
                color: {SPOTIFY_TEXT};
                font-size: 0.76rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }}

            .spotify-current-playlist-kicker::before {{
                content: "";
                width: 0.5rem;
                height: 0.5rem;
                border-radius: 999px;
                background: {SPOTIFY_GREEN};
                box-shadow: 0 0 0 0.24rem rgba(30, 215, 96, 0.18);
                flex: 0 0 auto;
            }}

            .spotify-wordmark {{
                margin: 0;
                line-height: 1.05;
                letter-spacing: -0.03em;
            }}

            .spotify-wordmark-play {{
                color: {SPOTIFY_GREEN};
                text-shadow: 0 0 0.55rem rgba(30, 215, 96, 0.35);
            }}

            .spotify-wordmark-dotqr8 {{
                color: #ff2bd6;
                text-shadow: 0 0 0.55rem rgba(255, 43, 214, 0.35);
            }}

            @media (max-width: 900px) {{
                .spotify-metrics-grid {{
                    grid-template-columns: 1fr;
                }}

                .spotify-helper-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_playlist_indicator(label: str, playlist_name: str, note: str | None = None) -> None:
    st.markdown(
        f"""
        <section class="spotify-current-playlist">
            <span class="spotify-current-playlist-name">{escape(playlist_name)}</span>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_brand_wordmark(level: int = 1) -> None:
    heading_level = min(max(level, 1), 6)
    tag = f"h{heading_level}"
    st.markdown(
        f"""
        <{tag} class="spotify-wordmark">
            <span class="spotify-wordmark-play">PlayPlay</span><span class="spotify-wordmark-dotqr8">.qr8</span>
        </{tag}>
        """,
        unsafe_allow_html=True,
    )


def render_nav_button(
    page_path: str,
    label: str,
    icon: str | None = None,
    *,
    button_type: str = "secondary",
    key: str | None = None,
    use_container_width: bool = False,
) -> None:
    button_label = f"{icon} {label}" if icon else label
    button_key = key or f"nav_{page_path.replace('/', '_').replace('.', '_')}_{label.lower().replace(' ', '_')}"
    if st.button(
        button_label,
        key=button_key,
        type=button_type,
        use_container_width=use_container_width,
    ):
        st.switch_page(page_path)