# ui/app.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile
import streamlit as st
from core.context import ContextBrief
from core.logger import init_db
from auth.auth import (
    verify_credentials, update_user_preference,
    change_password, create_default_admin,
)
from config.themes import THEMES, FONT_SIZES
from api.client import AnalystAPIClient

# ── Page config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Analyst Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialize ───────────────────────────────────────────────────
init_db()
create_default_admin()

# ── API client (module-level singleton) ──────────────────────────
api = AnalystAPIClient()

# ── Login gate ───────────────────────────────────────────────────
def render_login_page():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Playfair+Display:wght@600&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    .stApp {
        background: linear-gradient(135deg, #0a1628 0%, #0f1e2e 50%, #0a1a2e 100%) !important;
        background-attachment: fixed !important;
    }

    /* ── Title block above the form ───────────────────────────── */
    .login-header {
        text-align: center;
        padding: 2.5rem 1rem 1.75rem 1rem;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.09);
        border-bottom: none;
        border-radius: 16px 16px 0 0;
        margin-top: 8vh;
    }

    /* ── Form body — seamlessly below the header ──────────────── */
    [data-testid="stForm"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.09) !important;
        border-top: none !important;
        border-radius: 0 0 16px 16px !important;
        padding: 1.5rem 2rem 2rem 2rem !important;
        margin-top: 0 !important;
    }

    /* ── Credentials hint below card ──────────────────────────── */
    .login-hint {
        text-align: center;
        font-size: 0.78rem;
        color: #475569;
        margin-top: 0.75rem;
    }

    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
        font-size: 0.9rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
    }
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        box-shadow: 0 4px 14px rgba(59,130,246,0.3) !important;
        transition: all 0.2s ease !important;
    }
    .stFormSubmitButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(59,130,246,0.45) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        # Title block — pure HTML so it renders as one element
        st.markdown("""
        <div class="login-header">
            <div style="font-family:'Playfair Display',serif;font-size:2rem;
                        font-weight:600;color:#e2e8f0;letter-spacing:-0.03em;
                        margin-bottom:0.4rem;">
                Analyst Assistant
            </div>
            <div style="font-size:0.85rem;color:#94a3b8;">
                Sign in to your workspace
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Form body — styled via [data-testid="stForm"] to connect to header
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="username")
            password = st.text_input("Password", type="password", placeholder="password")
            submitted = st.form_submit_button("Sign In →", use_container_width=True)
            if submitted:
                if not username.strip() or not password:
                    st.error("Enter both username and password.")
                else:
                    user = verify_credentials(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.current_user = username.strip().lower()
                        st.session_state.user_data = user
                        st.session_state.user_theme = user.get("theme", "navy")
                        st.session_state.user_font_size = user.get("font_size", "medium")
                        st.session_state._just_logged_in = True
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        st.markdown("""
        <div class="login-hint">
            Default credentials: <code style="color:#94a3b8;">admin</code> /
            <code style="color:#94a3b8;">admin123</code>
        </div>
        """, unsafe_allow_html=True)


if not st.session_state.get("logged_in"):
    render_login_page()
    st.stop()

# ── Post-login loading overlay ───────────────────────────────────
# Injected on the first render after login. Fades out automatically
# while the real content (CSS, API health, checkpoints) loads below.
if st.session_state.pop("_just_logged_in", False):
    st.markdown("""
    <style>
    #aa-loading-overlay {
        position: fixed;
        inset: 0;
        z-index: 99999;
        background: #0a1628;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1.25rem;
        animation: aaOverlayFade 0.4s ease 1.2s forwards;
    }
    @keyframes aaOverlayFade {
        to { opacity: 0; pointer-events: none; visibility: hidden; }
    }
    .aa-loader-ring {
        width: 44px;
        height: 44px;
        border: 3px solid rgba(59, 130, 246, 0.15);
        border-top-color: #3b82f6;
        border-radius: 50%;
        animation: aaSpinRing 0.75s linear infinite;
    }
    @keyframes aaSpinRing {
        to { transform: rotate(360deg); }
    }
    .aa-loader-text {
        font-family: 'DM Sans', 'Inter', sans-serif;
        font-size: 0.85rem;
        font-weight: 500;
        color: #64748b;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .aa-loader-brand {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.5rem;
        font-weight: 600;
        color: #e2e8f0;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }
    </style>
    <div id="aa-loading-overlay">
        <div class="aa-loader-brand">Analyst Assistant</div>
        <div class="aa-loader-ring"></div>
        <div class="aa-loader-text">Loading workspace…</div>
    </div>
    """, unsafe_allow_html=True)

# ── Custom CSS — UI Polish ───────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@600&display=swap');

/* ── Root variables ───────────────────────────────────────── */
:root {
    --navy:       #0f1e2e;
    --navy-mid:   #162436;
    --navy-light: #1e3448;
    --blue:       #3b82f6;
    --blue-dim:   #1d4ed8;
    --teal:       #14b8a6;
    --amber:      #f59e0b;
    --red:        #ef4444;
    --green:      #22c55e;
    --text:       #e2e8f0;
    --text-muted: #94a3b8;
    --border:     rgba(255,255,255,0.08);
    --card:       rgba(255,255,255,0.04);
    --radius:     12px;
    --radius-sm:  8px;
}

/* ── Global reset ─────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    color: var(--text) !important;
}

/* ── Hide Streamlit chrome ────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Main background ──────────────────────────────────────── */
.stApp {
    background: linear-gradient(135deg, #0a1628 0%, #0f1e2e 50%, #0a1a2e 100%);
    background-attachment: fixed;
}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(15, 30, 46, 0.95) !important;
    border-right: 1px solid var(--border) !important;
    backdrop-filter: blur(20px);
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

/* ── Sidebar title ────────────────────────────────────────── */
[data-testid="stSidebar"] h1 {
    font-family: 'Playfair Display', serif !important;
    font-size: 1.4rem !important;
    color: var(--text) !important;
    letter-spacing: -0.02em;
}

/* ── Cards / containers ───────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    backdrop-filter: blur(8px);
    transition: border-color 0.2s ease;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(59, 130, 246, 0.3) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 500 !important;
    font-size: 0.9rem !important;
}

/* ── Page title ───────────────────────────────────────────── */
.main h1 {
    font-family: 'Playfair Display', serif !important;
    font-size: 2rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.03em !important;
    color: var(--text) !important;
    margin-bottom: 0.25rem !important;
}

/* ── Section headings ─────────────────────────────────────── */
.main h2 {
    font-size: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--blue) !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.75rem !important;
}

.main h3 {
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    margin-bottom: 0.5rem !important;
}

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: var(--radius) !important;
    padding: 4px !important;
    border: 1px solid var(--border) !important;
    gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm) !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    padding: 6px 14px !important;
    transition: all 0.15s ease !important;
    border: none !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text) !important;
    background: rgba(255,255,255,0.06) !important;
}
.stTabs [aria-selected="true"] {
    background: var(--blue) !important;
    color: white !important;
    font-weight: 600 !important;
}

/* ── Primary buttons ──────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--blue) 0%, var(--blue-dim) 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 14px rgba(59, 130, 246, 0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
}

/* ── Secondary buttons ────────────────────────────────────── */
.stButton > button:not([kind="primary"]) {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--text-muted) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: var(--blue) !important;
    color: var(--text) !important;
    background: rgba(59, 130, 246, 0.08) !important;
}

/* ── Text inputs ──────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    transition: border-color 0.2s ease !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}

/* ── Selectbox ────────────────────────────────────────────── */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
}

/* ── Metrics ──────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1rem !important;
    transition: border-color 0.2s ease;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(59, 130, 246, 0.3) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 1.6rem !important;
    font-weight: 500 !important;
    color: var(--text) !important;
}

/* ── Alerts ───────────────────────────────────────────────── */
.stAlert {
    border-radius: var(--radius-sm) !important;
    border-left-width: 3px !important;
    font-size: 0.88rem !important;
}
div[data-baseweb="notification"][kind="positive"],
.stSuccess {
    background: rgba(34, 197, 94, 0.08) !important;
    border-left-color: var(--green) !important;
}
div[data-baseweb="notification"][kind="warning"],
.stWarning {
    background: rgba(245, 158, 11, 0.08) !important;
    border-left-color: var(--amber) !important;
}
div[data-baseweb="notification"][kind="error"],
.stError {
    background: rgba(239, 68, 68, 0.08) !important;
    border-left-color: var(--red) !important;
}
div[data-baseweb="notification"][kind="info"],
.stInfo {
    background: rgba(59, 130, 246, 0.08) !important;
    border-left-color: var(--blue) !important;
}

/* ── Code blocks ──────────────────────────────────────────── */
.stCodeBlock {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
}
.stCodeBlock code {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.85rem !important;
}

/* ── Dividers ─────────────────────────────────────────────── */
hr {
    border-color: var(--border) !important;
    margin: 1rem 0 !important;
}

/* ── Caption text ─────────────────────────────────────────── */
.stCaption, small {
    color: var(--text-muted) !important;
    font-size: 0.8rem !important;
}

/* ── Spinner ──────────────────────────────────────────────── */
.stSpinner > div {
    border-top-color: var(--blue) !important;
}

/* ── Checkbox ─────────────────────────────────────────────── */
.stCheckbox label {
    font-size: 0.88rem !important;
    color: var(--text) !important;
}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.12);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255,255,255,0.2);
}

/* ── Form submit button ───────────────────────────────────── */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, var(--teal) 0%, #0d9488 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 4px 14px rgba(20, 184, 166, 0.25) !important;
    transition: all 0.2s ease !important;
}
.stFormSubmitButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(20, 184, 166, 0.4) !important;
}

/* ── Progress bar ─────────────────────────────────────────── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--blue) 0%, var(--teal) 100%) !important;
    border-radius: 4px !important;
}

/* ── JSON viewer ──────────────────────────────────────────── */
.stJson {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
}

/* ── Welcome screen ───────────────────────────────────────── */
.welcome-card {
    background: linear-gradient(135deg,
        rgba(59, 130, 246, 0.08) 0%,
        rgba(20, 184, 166, 0.05) 100%);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 16px;
    padding: 2.5rem;
    margin: 1.5rem 0;
}
.mode-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    margin: 0.5rem 0;
    transition: all 0.2s ease;
}
.mode-card:hover {
    border-color: rgba(59, 130, 246, 0.35);
    background: rgba(59, 130, 246, 0.05);
    transform: translateX(3px);
}
.mode-number {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    color: var(--blue);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.2rem;
}
.mode-title {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text);
    margin-bottom: 0.2rem;
}
.mode-desc {
    font-size: 0.82rem;
    color: var(--text-muted);
    line-height: 1.5;
}

/* ── Session header ───────────────────────────────────────── */
.session-header {
    background: linear-gradient(135deg,
        rgba(15, 30, 46, 0.9) 0%,
        rgba(22, 36, 54, 0.9) 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem 1.75rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}

/* ── Verdict badges ───────────────────────────────────────── */
.verdict-strong {
    display: inline-block;
    background: rgba(34, 197, 94, 0.15);
    border: 1px solid rgba(34, 197, 94, 0.4);
    color: #4ade80;
    border-radius: 6px;
    padding: 0.25rem 0.75rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.08em;
}
.verdict-needs-work {
    display: inline-block;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.4);
    color: #fbbf24;
    border-radius: 6px;
    padding: 0.25rem 0.75rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.08em;
}
.verdict-unsupported {
    display: inline-block;
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #f87171;
    border-radius: 6px;
    padding: 0.25rem 0.75rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.08em;
}
</style>
""", unsafe_allow_html=True)

# ── Theme override — runs after static CSS so cascade wins ───────
_tk = st.session_state.get("user_theme", "navy")
_fs = st.session_state.get("user_font_size", "medium")
_t  = THEMES[_tk]
_f  = FONT_SIZES[_fs]
st.markdown(f"""
<style>
:root {{
    --navy:       {_t['navy']};
    --navy-mid:   {_t['navy_mid']};
    --navy-light: {_t['navy_light']};
    --blue:       {_t['blue']};
    --blue-dim:   {_t['blue_dim']};
    --teal:       {_t['teal']};
    --amber:      {_t['amber']};
    --text:       {_t['text']};
    --text-muted: {_t['text_muted']};
    --border:     {_t['border']};
    --card:       {_t['card']};
}}
.stApp {{
    background: {_t['bg_gradient']} !important;
    background-attachment: fixed !important;
}}
[data-testid="stSidebar"] {{
    background: {_t['sidebar_bg']} !important;
}}
html, body, [class*="css"] {{
    font-size: {_f['base']} !important;
}}
.stCodeBlock code {{
    font-size: {_f['mono']} !important;
}}
</style>
""", unsafe_allow_html=True)

# ── Session state bootstrap ─────────────────────────────────────
if "api_session_id" not in st.session_state:
    st.session_state.api_session_id = None

if "api_state" not in st.session_state:
    st.session_state.api_state = {}

if "context_brief" not in st.session_state:
    st.session_state.context_brief = None

if "briefed" not in st.session_state:
    st.session_state.briefed = False

if "mode2_reviewed" not in st.session_state:
    st.session_state.mode2_reviewed = False

if "mode1_result" not in st.session_state:
    st.session_state.mode1_result = None

if "mode2_result" not in st.session_state:
    st.session_state.mode2_result = None

if "mode3_result" not in st.session_state:
    st.session_state.mode3_result = None

if "mode4_result" not in st.session_state:
    st.session_state.mode4_result = None

if "mode5_result" not in st.session_state:
    st.session_state.mode5_result = None

if "last_suggestions" not in st.session_state:
    st.session_state.last_suggestions = []


def checkpoint_session():
    """Persist current state via API (non-critical — silently skips on failure)."""
    if st.session_state.get("api_session_id"):
        try:
            api.save_checkpoint(st.session_state.api_session_id)
        except Exception:
            pass


def _api_state() -> dict:
    return st.session_state.get("api_state", {})


# ── Helpers ──────────────────────────────────────────────────────
def render_nudges(suggestions: list[dict]):
    if not suggestions:
        return
    st.markdown("---")
    st.markdown("**💡 Thought Partner Nudges**")
    for s in suggestions:
        icon = "🔴" if s["priority"] == "high" else "🟡" if s["priority"] == "medium" else "🟢"
        with st.expander(f"{icon} {s['action']}"):
            st.caption(s["reason"])


def render_validation_error(result: dict):
    if result is None:
        return
    if err := result.get("_validation_error"):
        st.error(f"⛔ {err}")
    if result.get("_degraded"):
        st.error(f"⛔ LLM unavailable: {result.get('_error', 'unknown error')}")


def render_warnings(result: dict):
    if result is None:
        return
    if w := result.get("_warning"):
        st.warning(f"💡 {w}")
    if ws := result.get("_session_warnings", []):
        for w in ws:
            st.warning(f"⚠️ Session: {w}")
    if cw := result.get("_code_warnings", []):
        for w in cw:
            st.warning(f"⚠️ Code: {w}")


# ════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🧠 Analyst Assistant")
    st.caption("Analytical thought partner")
    st.markdown("---")

    # ── Profile card ─────────────────────────────────────────────
    _ud = st.session_state.get("user_data", {})
    _cu = st.session_state.get("current_user", "user")
    _dn = _ud.get("display_name", _cu.title())
    _role = _ud.get("role", "user")
    _initials = "".join(w[0].upper() for w in _dn.split()[:2]) or "?"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:0.75rem;
                padding:0.75rem 1rem;
                background:var(--card);border:1px solid var(--border);
                border-radius:10px;margin-bottom:0.5rem;">
        <div style="width:36px;height:36px;border-radius:50%;flex-shrink:0;
                    background:linear-gradient(135deg,var(--blue),var(--teal));
                    display:flex;align-items:center;justify-content:center;
                    font-weight:700;font-size:0.8rem;color:white;">
            {_initials}
        </div>
        <div style="min-width:0;">
            <div style="font-weight:600;font-size:0.88rem;
                        color:var(--text);white-space:nowrap;overflow:hidden;
                        text-overflow:ellipsis;">{_dn}</div>
            <div style="font-size:0.72rem;color:var(--blue);
                        font-weight:500;letter-spacing:0.06em;
                        text-transform:uppercase;">{_role}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Settings expander ─────────────────────────────────────────
    with st.expander("⚙️ Settings"):
        st.markdown("**Appearance**")
        _theme_keys   = list(THEMES.keys())
        _theme_labels = [THEMES[k]["name"] for k in _theme_keys]
        _cur_idx = _theme_keys.index(st.session_state.get("user_theme", "navy"))
        _new_theme_label = st.selectbox(
            "Theme", _theme_labels, index=_cur_idx, key="theme_select"
        )
        _new_theme_key = _theme_keys[_theme_labels.index(_new_theme_label)]

        _font_opts = ["small", "medium", "large"]
        _cur_font  = _font_opts.index(st.session_state.get("user_font_size", "medium"))
        _new_font  = st.selectbox("Font size", _font_opts, index=_cur_font, key="font_select")

        if st.button("Save appearance", use_container_width=True):
            st.session_state.user_theme    = _new_theme_key
            st.session_state.user_font_size = _new_font
            update_user_preference(_cu, "theme", _new_theme_key)
            update_user_preference(_cu, "font_size", _new_font)
            st.toast("Appearance saved!", icon="✅")
            st.rerun()

        st.markdown("---")
        st.markdown("**Change password**")
        with st.form("change_pw_form"):
            _old_pw  = st.text_input("Current password", type="password", key="cpw_old")
            _new_pw  = st.text_input("New password",     type="password", key="cpw_new")
            _conf_pw = st.text_input("Confirm new",      type="password", key="cpw_conf")
            if st.form_submit_button("Update password", use_container_width=True):
                if not _old_pw or not _new_pw:
                    st.error("Fill in all fields.")
                elif _new_pw != _conf_pw:
                    st.error("Passwords don't match.")
                elif len(_new_pw) < 6:
                    st.error("Minimum 6 characters.")
                elif change_password(_cu, _old_pw, _new_pw):
                    st.success("Password updated!")
                else:
                    st.error("Current password is incorrect.")

    st.markdown("---")

    # ── API status indicator ──────────────────────────────────────
    try:
        _h = api.health()
        st.caption(f"🟢 API — {_h.get('sessions_active', 0)} active session(s)")
    except Exception:
        st.error("⛔ API server unreachable — run `./run.sh` or `uvicorn api.main:app`")

    st.markdown("---")
    st.subheader("📋 Session Brief")
    st.caption("Fill once. Every mode inherits it automatically.")

    with st.form("context_form"):
        company_name = st.text_input("Company / Team", value="Deliveroo Care")
        domain = st.text_input("Domain", value="customer support operations")
        primary_metric = st.text_input("Primary Metric", value="self-serve rate")
        metric_definition = st.text_area(
            "Metric Definition",
            value="percentage of customer contacts resolved without a human agent",
            height=68,
        )
        time_period = st.text_input("Time Period", value="last 30 days (May 2026)")
        audience = st.selectbox("Output Audience", ["data team", "executive", "ops manager"])
        stakes = st.text_input("Stakes", value="weekly ops review with Head of Care")
        known_context = st.text_input(
            "Known Context (one line)",
            value="a new bot deflection flow was launched on June 1st 2026",
        )
        constraints = st.text_input("Constraints", value="do not reference competitor benchmarks")

        st.markdown("---")
        st.markdown("**📝 Analyst Context Block**")
        st.caption(
            "Paste anything the agent should know — metric quirks, "
            "schema notes, business rules, past findings. "
            "Gets indexed and retrieved automatically."
        )
        analyst_context = st.text_area(
            "Your domain knowledge",
            height=200,
            placeholder="""Examples:

- Metric quirks:
  Self-serve rate on Mondays is typically 4-6% lower due to
  weekend backlog — don't flag Monday dips as anomalies.

- Schema notes:
  contacts table: date, contact_reason, resolved_self_serve (bool),
  bot_deflected (bool), handle_time_minutes, agent_id

- Business rules:
  Promotional campaigns always spike contact_volume by 30-50%.

- Past findings:
  March 2025: self-serve rate dropped to 48% during system outage.""",
            key="analyst_context_input",
        )

        submitted = st.form_submit_button(
            "Brief the Agent",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            brief_dict = dict(
                company_name=company_name,
                domain=domain,
                primary_metric=primary_metric,
                metric_definition=metric_definition,
                time_period=time_period,
                audience=audience,
                stakes=stakes,
                known_context=known_context,
                constraints=constraints,
                analyst_context=analyst_context,
            )

            # Create (or recycle) a server-side session
            if not st.session_state.get("api_session_id"):
                st.session_state.api_session_id = api.create_session()

            with st.status("Briefing agent…", expanded=False) as _s:
                resp = api.set_brief(st.session_state.api_session_id, brief_dict)
                _s.update(label="✅ Agent briefed", state="complete")

            # Keep a local ContextBrief for display purposes
            st.session_state.context_brief = ContextBrief(**brief_dict)
            st.session_state.api_state = {}
            st.session_state.briefed = True
            st.session_state.mode2_reviewed = False
            st.session_state.mode1_result = None
            st.session_state.mode2_result = None
            st.session_state.mode3_result = None
            st.session_state.mode4_result = None
            st.session_state.mode5_result = None
            st.session_state.last_suggestions = []

            chunks = resp.get("chunks_indexed", 0)
            if chunks:
                st.success(f"✅ Agent briefed. Context indexed: {chunks} chunk(s).")
            else:
                st.success("✅ Agent briefed.")

    # ── Session Status ───────────────────────────────────────────
    if st.session_state.briefed:
        _as = _api_state()
        st.markdown("---")
        st.subheader("📊 Session Status")
        col1, col2 = st.columns(2)
        col1.metric("Turns", _as.get("session_turn", 0))
        col2.metric("Hypotheses", len(_as.get("hypotheses", [])))
        col1.metric("Evidence", len(_as.get("evidence_collected", [])))
        col2.metric("Open Qs", len(_as.get("open_questions", [])))
        if _as.get("current_focus", "not yet determined") != "not yet determined":
            st.caption(f"**Focus:** {_as['current_focus']}")

    # ── Knowledge Base Panel ─────────────────────────────────────
    st.markdown("---")
    st.subheader("📚 Knowledge Base")
    st.caption("Additional documents on top of your typed context.")

    kb_tab1, kb_tab2 = st.tabs(["Domain Docs", "Method Cards"])

    with kb_tab1:
        uploaded_domain = st.file_uploader(
            "Upload metric defs, schemas, runbooks (.md or .txt)",
            type=["md", "txt"],
            accept_multiple_files=True,
            key="domain_upload",
        )
        if uploaded_domain and st.session_state.get("api_session_id"):
            total = 0
            for f in uploaded_domain:
                with tempfile.NamedTemporaryFile(suffix=f"_{f.name}", delete=False, mode="wb") as tmp:
                    tmp.write(f.read())
                    tmp_path = Path(tmp.name)
                resp = api.ingest_file(st.session_state.api_session_id, tmp_path, "domain")
                chunks = resp.get("chunks_indexed", 0)
                total += chunks
                st.caption(f"✅ {f.name} → {chunks} chunks")
            st.success(f"Indexed {total} total chunks")

    with kb_tab2:
        uploaded_methods = st.file_uploader(
            "Upload statistical method cards (.md or .txt)",
            type=["md", "txt"],
            accept_multiple_files=True,
            key="method_upload",
        )
        if uploaded_methods and st.session_state.get("api_session_id"):
            total = 0
            for f in uploaded_methods:
                with tempfile.NamedTemporaryFile(suffix=f"_{f.name}", delete=False, mode="wb") as tmp:
                    tmp.write(f.read())
                    tmp_path = Path(tmp.name)
                resp = api.ingest_file(st.session_state.api_session_id, tmp_path, "methods")
                chunks = resp.get("chunks_indexed", 0)
                total += chunks
                st.caption(f"✅ {f.name} → {chunks} chunks")
            st.success(f"Indexed {total} total chunks")

    try:
        from rag.store import get_domain_collection, get_methods_collection
        d_count = get_domain_collection().count()
        m_count = get_methods_collection().count()
        st.caption(f"📦 Domain: **{d_count}** chunks · Methods: **{m_count}** chunks")
    except Exception:
        pass

    # ── Token budget indicator (derived from turn count) ─────────
    if st.session_state.briefed:
        _turns = _api_state().get("session_turn", 0)
        _budget_pct = min(100, int(_turns * 800 / 20_000 * 100))
        _color = "🟢" if _budget_pct < 60 else "🟡" if _budget_pct < 85 else "🔴"
        st.caption(f"{_color} Token budget: **{_budget_pct}%** estimated used")

    # ── Session Resume ───────────────────────────────────────────
    st.markdown("---")
    st.subheader("💾 Checkpoints")
    try:
        checkpoints = api.list_checkpoints()
    except Exception:
        checkpoints = []

    if checkpoints:
        options = {
            f"Turn {c['turn']} — {c['updated_at'][:16]} — ID: {c['session_id']}": c['session_id']
            for c in checkpoints
        }
        selected = st.selectbox(
            "Resume a past session",
            ["— select —"] + list(options.keys()),
            key="checkpoint_select",
        )
        if st.button("▶️ Resume Session", use_container_width=True):
            if selected != "— select —":
                _sid = options[selected]
                try:
                    _resp = api.restore_checkpoint(_sid)
                    st.session_state.api_session_id = _sid
                    st.session_state.api_state = api.get_state(_sid)
                    st.session_state.mode1_result = None
                    st.session_state.mode2_result = None
                    st.session_state.mode3_result = None
                    st.session_state.mode4_result = None
                    st.session_state.mode5_result = None
                    st.success(f"✅ Resumed — {_resp['session_turn']} turns restored")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Resume failed: {exc}")
    else:
        st.caption("No saved sessions yet.")

    # ── Reset ────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("🔄 Reset Session", use_container_width=True):
        if st.session_state.get("api_session_id"):
            try:
                api.delete_session(st.session_state.api_session_id)
            except Exception:
                pass
        st.session_state.api_session_id = None
        st.session_state.api_state = {}
        st.session_state.briefed = False
        st.session_state.context_brief = None
        st.session_state.mode2_reviewed = False
        st.session_state.mode1_result = None
        st.session_state.mode2_result = None
        st.session_state.mode3_result = None
        st.session_state.mode4_result = None
        st.session_state.mode5_result = None
        st.session_state.last_suggestions = []
        st.rerun()

    # ── Sign out ──────────────────────────────────────────────────
    if st.button("🚪 Sign Out", use_container_width=True):
        _keep = {"user_theme", "user_font_size"}
        for _k in list(st.session_state.keys()):
            if _k not in _keep:
                del st.session_state[_k]
        st.rerun()


# ════════════════════════════════════════════════════════════════
# MAIN AREA
# ════════════════════════════════════════════════════════════════
if not st.session_state.briefed:
    st.markdown("""
    <div style="padding: 2rem 0 1rem 0;">
        <div style="font-family: 'Playfair Display', serif; font-size: 2.8rem;
                    font-weight: 600; letter-spacing: -0.03em; color: #e2e8f0;
                    line-height: 1.1; margin-bottom: 0.5rem;">
            Analyst Assistant
        </div>
        <div style="font-size: 1rem; color: #94a3b8; margin-bottom: 2rem;">
            A stateful analytical thought partner — not a chatbot, not a search engine.
        </div>
    </div>
    <div class="welcome-card">
        <div style="font-size: 0.75rem; font-weight: 600; letter-spacing: 0.1em;
                    text-transform: uppercase; color: #3b82f6; margin-bottom: 1rem;">
            Five modes · One session · Full memory
        </div>
        <div class="mode-card">
            <div class="mode-number">Mode 01</div>
            <div class="mode-title">💡 Hypothesis Generator</div>
            <div class="mode-desc">Ranked explanations for a metric pattern — cites only your co-moving metrics, never invents.</div>
        </div>
        <div class="mode-card">
            <div class="mode-number">Mode 02</div>
            <div class="mode-title">💻 Code Drafter</div>
            <div class="mode-desc">Investigation code targeting your highest-confidence hypothesis — with a review gate before copying.</div>
        </div>
        <div class="mode-card">
            <div class="mode-number">Mode 03</div>
            <div class="mode-title">📄 Document Synthesiser</div>
            <div class="mode-desc">Reads multiple sources, separates facts from inferences, surfaces contradictions explicitly.</div>
        </div>
        <div class="mode-card">
            <div class="mode-number">Mode 04</div>
            <div class="mode-title">🔍 Stress Tester</div>
            <div class="mode-desc">Adversarially challenges your conclusion using everything learned this session.</div>
        </div>
        <div class="mode-card">
            <div class="mode-number">Mode 05</div>
            <div class="mode-title">✍️ Narrative Writer</div>
            <div class="mode-desc">Stakeholder-ready summary with inline flags for unverified claims and contested conclusions.</div>
        </div>
    </div>
    <div style="margin-top: 1.5rem; padding: 1rem 1.5rem;
                background: rgba(255,255,255,0.03); border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.07);
                font-size: 0.85rem; color: #94a3b8;">
        👈 Fill in the <strong style="color: #e2e8f0;">Session Brief</strong> in the sidebar to begin.
        Every mode inherits your context automatically.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

context = st.session_state.context_brief
_sid = st.session_state.api_session_id or "—"

st.markdown(f"""
<div class="session-header">
    <div style="flex: 1;">
        <div style="font-family: 'Playfair Display', serif; font-size: 1.4rem;
                    font-weight: 600; color: #e2e8f0; letter-spacing: -0.02em;">
            {context.company_name}
        </div>
        <div style="font-size: 0.82rem; color: #94a3b8; margin-top: 0.2rem;">
            <span style="color: #3b82f6; font-weight: 500;">{context.primary_metric}</span>
            &nbsp;·&nbsp; {context.time_period}
            &nbsp;·&nbsp; {context.audience}
        </div>
    </div>
    <div style="font-family: 'DM Mono', monospace; font-size: 0.72rem;
                color: #475569; letter-spacing: 0.05em;">
        SESSION · {_sid.upper()}
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💡 Mode 1 — Hypotheses",
    "💻 Mode 2 — Code",
    "📄 Mode 3 — Synthesis",
    "🔍 Mode 4 — Stress Test",
    "✍️ Mode 5 — Narrative",
    "🕒 Session Timeline",
    "📋 Call History",
])


# ════════════════════════════════════════════════════════════════
# TAB 1 — MODE 1
# ════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("💡 Hypothesis Generator")
    st.caption("Describe a metric pattern. Include co-moving metrics you can observe.")

    user_input = st.text_area(
        "What pattern are you investigating?",
        height=150,
        placeholder="""e.g. Self-serve rate dropped from 68% to 54% over the last 30 days.
Co-moving metrics:
- bot_deflection_rate dropped from 71% to 49%
- avg_handle_time increased from 4.2 min to 6.8 min
- contact_volume increased 22% week-over-week""",
        key="mode1_input",
    )

    if st.button("Generate Hypotheses", type="primary", key="mode1_run"):
        if not user_input.strip():
            st.warning("Describe the pattern you're investigating first.")
        else:
            with st.status("Generating hypotheses…", expanded=False) as _s:
                resp = api.mode1(st.session_state.api_session_id, user_input)
                st.session_state.api_state = resp["state"]
                st.session_state.last_suggestions = resp["suggestions"]
                st.session_state.mode1_result = resp["result"]
                checkpoint_session()
                _s.update(label="✅ Hypotheses ready", state="complete")

    if st.session_state.mode1_result is not None:
        result = st.session_state.mode1_result
        render_validation_error(result)
        render_warnings(result)

        if result.get("contradiction_flag"):
            st.error(f"⚠️ Contradiction detected: {result['contradiction_flag']}")

        st.subheader("Ranked Hypotheses")
        for i, h in enumerate(result.get("hypotheses", []), 1):
            confidence = h.get("confidence", 0)
            with st.expander(
                f"#{i} — {h['text']} "
                f"({'⬆️' if confidence >= 0.7 else '➡️' if confidence >= 0.4 else '⬇️'} "
                f"{confidence:.0%} confidence)",
                expanded=(i == 1),
            ):
                st.caption(f"**Co-moving metric cited:** {h.get('co_moving_metric_cited', 'N/A')}")
                st.markdown(f"✅ **Confirms if:** {h.get('confirms_if', '')}")
                st.markdown(f"❌ **Rules out if:** {h.get('rules_out_if', '')}")

        if oqs := result.get("open_questions", []):
            st.subheader("Open Questions Flagged")
            for q in oqs:
                st.markdown(f"- {q}")

        render_nudges(st.session_state.last_suggestions)


# ════════════════════════════════════════════════════════════════
# TAB 2 — MODE 2
# ════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("💻 Code Drafter")
    st.caption("Describe what you want to investigate. The agent targets your highest-confidence hypothesis.")

    _hyps = _api_state().get("hypotheses", [])
    if _hyps:
        with st.expander("Active hypotheses (agent will target these)", expanded=False):
            for h in _hyps:
                icon = "🟢" if h["status"] == "confirmed" else "🔴" if h["status"] == "ruled_out" else "🔵"
                st.markdown(f"{icon} **{h['confidence']:.0%}** — {h['text']}")

    code_input = st.text_area(
        "What do you want to investigate with code?",
        height=120,
        placeholder="e.g. Write Python to compare self-serve rate before and after June 1st, segmented by contact_reason.",
        key="mode2_input",
    )

    if st.button("Draft Code", type="primary", key="mode2_run"):
        if not code_input.strip():
            st.warning("Describe what you want to investigate first.")
        else:
            with st.status("Drafting investigation code…", expanded=False) as _s:
                resp = api.mode2(st.session_state.api_session_id, code_input)
                st.session_state.api_state = resp["state"]
                st.session_state.mode2_result = resp["result"]
                st.session_state.mode2_reviewed = False
                st.session_state.last_suggestions = resp["suggestions"]
                checkpoint_session()
                _s.update(label="✅ Code ready — review before copying", state="complete")

    if st.session_state.mode2_result is not None:
        result = st.session_state.mode2_result
        render_validation_error(result)

        if result.get("refusal_reason") and result["refusal_reason"] not in ["null", None, ""]:
            st.error(f"⚠️ {result['refusal_reason']}")
        else:
            if h_tested := result.get("hypothesis_tested"):
                st.info(f"🎯 Targeting hypothesis: *{h_tested}*")

            if assumptions := result.get("assumptions", []):
                with st.expander("⚠️ Assumptions made"):
                    for a in assumptions:
                        st.markdown(f"- {a}")

            st.subheader(f"Generated {result.get('language', 'code').upper()}")
            code_str = result.get("code", "")
            st.code(code_str, language=result.get("language", "python"))

            if guide := result.get("interpretation_guide"):
                st.markdown(f"**Interpretation:** {guide}")

            st.markdown("---")
            st.markdown("### ✋ Review Gate")
            st.caption(
                "Read the code carefully before copying. "
                "Check the box to confirm you understand it before copying is enabled."
            )

            reviewed = st.checkbox(
                "I have read and understood this code. I accept responsibility for running it.",
                key="review_checkbox",
                value=st.session_state.mode2_reviewed,
            )
            if reviewed:
                st.session_state.mode2_reviewed = True

            if st.session_state.mode2_reviewed:
                st.success("✅ Review confirmed. Copy the code above to run it.")
                st.code(code_str, language=result.get("language", "python"))
            else:
                st.warning("⬆️ Check the box above to enable copying.")

        render_nudges(st.session_state.last_suggestions)


# ════════════════════════════════════════════════════════════════
# TAB 3 — MODE 3
# ════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📄 Document Synthesiser")
    st.caption("Paste 2–5 document excerpts. The agent detects contradictions and cross-references the analytical state.")

    st.markdown("**Source documents** (minimum 2 required)")

    docs = []
    for i in range(1, 4):
        doc = st.text_area(
            f"Source {i}",
            height=100,
            placeholder=f"Paste source {i} here...",
            key=f"doc_{i}",
        )
        if doc.strip():
            docs.append(doc.strip())

    if st.button("Synthesise Documents", type="primary", key="mode3_run"):
        if len(docs) < 2:
            st.warning("Provide at least 2 source documents.")
        else:
            with st.status("Synthesising documents…", expanded=False) as _s:
                resp = api.mode3(st.session_state.api_session_id, docs)
                st.session_state.api_state = resp["state"]
                st.session_state.last_suggestions = resp["suggestions"]
                st.session_state.mode3_result = resp["result"]
                checkpoint_session()
                _s.update(label="✅ Synthesis complete", state="complete")

    if st.session_state.mode3_result is not None:
        result = st.session_state.mode3_result
        render_validation_error(result)
        render_warnings(result)

        if "_error" in result:
            st.error(result["_error"])
        else:
            st.subheader(f"Synthesis ({result.get('source_count', 0)} sources)")

            if summary := result.get("synthesis_summary"):
                st.markdown(f"**Summary:** {summary}")

            col1, col2 = st.columns(2)
            with col1:
                if facts := result.get("facts", []):
                    st.markdown("**✅ Facts (explicitly stated)**")
                    for f in facts:
                        st.markdown(f"- {f}")
                if inferences := result.get("inferences", []):
                    st.markdown("**🔍 Inferences (logical conclusions)**")
                    for inf in inferences:
                        st.markdown(f"- {inf}")
            with col2:
                if gaps := result.get("gaps", []):
                    st.markdown("**❓ Gaps (missing information)**")
                    for g in gaps:
                        st.markdown(f"- {g}")

            if conflicts := result.get("conflicts", []):
                st.markdown("---")
                st.subheader("⚠️ Conflicts Detected")
                for c in conflicts:
                    severity_color = (
                        "🔴" if c["severity"] == "critical"
                        else "🟡" if c["severity"] == "moderate"
                        else "🟢"
                    )
                    with st.expander(f"{severity_color} {c['severity'].upper()} conflict"):
                        st.markdown(f"**Source A says:** {c['source_a']}")
                        st.markdown(f"**Source B says:** {c['source_b']}")
            else:
                st.success("✅ No conflicts detected between sources.")

            if sc := result.get("state_contradictions"):
                st.warning(f"⚠️ Contradicts analytical state: {sc}")

        render_nudges(st.session_state.last_suggestions)


# ════════════════════════════════════════════════════════════════
# TAB 4 — MODE 4
# ════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("🔍 Conclusion Stress-Tester")
    st.caption("State your conclusion. The agent will challenge it using everything it knows from this session.")

    _hyps = _api_state().get("hypotheses", [])
    if _hyps:
        with st.expander("Session hypotheses (agent will reference these)", expanded=False):
            for h in _hyps:
                st.markdown(f"- **{h['confidence']:.0%}** — {h['text']}")

    conclusion_input = st.text_area(
        "State your conclusion",
        height=100,
        placeholder="e.g. The self-serve rate drop is primarily caused by the bot confidence threshold being set too conservatively.",
        key="mode4_input",
    )

    if st.button("Stress Test", type="primary", key="mode4_run"):
        if not conclusion_input.strip():
            st.warning("State a conclusion to stress-test first.")
        else:
            with st.status("Stress-testing conclusion…", expanded=False) as _s:
                resp = api.mode4(st.session_state.api_session_id, conclusion_input)
                st.session_state.api_state = resp["state"]
                st.session_state.last_suggestions = resp["suggestions"]
                st.session_state.mode4_result = resp["result"]
                checkpoint_session()
                _s.update(label="✅ Stress test complete", state="complete")

    if st.session_state.mode4_result is not None:
        result = st.session_state.mode4_result
        render_validation_error(result)
        render_warnings(result)

        verdict = result.get("verdict", "UNKNOWN")
        verdict_class = (
            "verdict-strong" if verdict == "STRONG"
            else "verdict-needs-work" if verdict == "NEEDS WORK"
            else "verdict-unsupported"
        )
        st.markdown(f"""
        <div style="margin: 1rem 0 0.5rem 0;">
            <span class="{verdict_class}">{verdict}</span>
        </div>
        <div style="font-size: 0.88rem; color: #94a3b8; margin-bottom: 1rem;">
            {result.get("verdict_reason", "")}
        </div>
        """, unsafe_allow_html=True)

        if refs := result.get("hypotheses_referenced", []):
            st.subheader("Hypotheses Referenced")
            for r in refs:
                st.markdown(f"- {r}")

        if flaws := result.get("flaws", []):
            st.subheader("Flaws Identified")
            for flaw in flaws:
                severity_icon = (
                    "🔴" if flaw["severity"] == "critical"
                    else "🟡" if flaw["severity"] == "moderate"
                    else "🟢"
                )
                with st.expander(
                    f"{severity_icon} {flaw['type'].replace('_', ' ').title()} — {flaw['severity'].upper()}"
                ):
                    st.markdown(flaw["description"])

        if sa := result.get("strengthening_analysis"):
            st.info(f"💪 **To strengthen this conclusion:** {sa}")

        if ignored := result.get("ignored_ruled_out_hypotheses"):
            st.warning(f"⚠️ **Ignored ruled-out hypothesis:** {ignored}")

        render_nudges(st.session_state.last_suggestions)


# ════════════════════════════════════════════════════════════════
# TAB 5 — MODE 5
# ════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("✍️ Narrative Writer")
    st.caption(f"Writes for your briefed audience: **{context.audience}**. Draws on the full session.")

    narrative_input = st.text_area(
        "Any specific focus for the narrative? (optional)",
        height=80,
        placeholder="e.g. Focus on the bot investigation findings. Keep it to 3 paragraphs.",
        key="mode5_input",
    )

    if st.button("Draft Narrative", type="primary", key="mode5_run"):
        focus = narrative_input.strip() or f"Write a narrative for the {context.audience} summarising this investigation."
        with st.status("Drafting narrative…", expanded=False) as _s:
            resp = api.mode5(st.session_state.api_session_id, focus)
            st.session_state.api_state = resp["state"]
            st.session_state.mode5_result = resp["result"]
            checkpoint_session()
            _s.update(label="✅ Narrative ready", state="complete")

    if st.session_state.mode5_result is not None:
        result = st.session_state.mode5_result
        render_validation_error(result)
        render_warnings(result)

        st.subheader("Narrative")
        st.markdown(result.get("narrative", ""))

        if flags := result.get("flags", []):
            st.markdown("---")
            st.subheader("🚩 Flags in Narrative")
            for flag in flags:
                flag_type = flag.get("type", "")
                icon = (
                    "🔴" if flag_type == "HIGH STAKES"
                    else "🟡" if flag_type == "CONTESTED"
                    else "⚪"
                )
                with st.expander(f"{icon} [{flag_type}] — {flag['claim'][:60]}..."):
                    st.markdown(f"**Claim:** {flag['claim']}")
                    st.markdown(f"**Reason flagged:** {flag['reason']}")

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**✅ What we know:**\n{result.get('what_we_know', '')}")
        col2.markdown(f"**❓ What we don't know:**\n{result.get('what_we_dont_know', '')}")
        col3.markdown(f"**➡️ Next step:**\n{result.get('recommended_next_step', '')}")


# ════════════════════════════════════════════════════════════════
# TAB 6 — SESSION TIMELINE
# ════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("🕒 Session Timeline")
    st.caption("Every mode call this session, in order.")

    _thread = _api_state().get("thread", [])
    if not _thread:
        st.info("No mode calls yet this session. Run a mode to see the timeline.")
    else:
        for event in reversed(_thread):
            mode_label = event["mode"].replace("_", " ").title()
            with st.expander(
                f"Turn {event['turn']} — {mode_label} — {event['timestamp'][:19]}",
                expanded=False,
            ):
                st.markdown(f"**Input:** {event['user_input'][:200]}...")
                st.markdown(f"**Output preview:** {event['agent_output'][:300]}...")

    st.markdown("---")
    st.subheader("Current Analytical State")
    _as = _api_state()
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Hypotheses**")
        if _as.get("hypotheses"):
            for h in _as["hypotheses"]:
                icon = "🟢" if h["status"] == "confirmed" else "🔴" if h["status"] == "ruled_out" else "🔵"
                st.markdown(f"{icon} ({h['confidence']:.0%}) {h['text']}")
        else:
            st.caption("None yet.")

        st.markdown("**Conclusions Stated**")
        if _as.get("conclusions_stated"):
            for c in _as["conclusions_stated"]:
                st.markdown(f"- {c[:100]}...")
        else:
            st.caption("None yet.")

    with col2:
        st.markdown("**Evidence Collected**")
        if _as.get("evidence_collected"):
            for e in _as["evidence_collected"]:
                st.markdown(f"- {e}")
        else:
            st.caption("None yet.")

        st.markdown("**Open Questions**")
        if _as.get("open_questions"):
            for q in _as["open_questions"]:
                st.markdown(f"- {q}")
        else:
            st.caption("None yet.")


# ════════════════════════════════════════════════════════════════
# TAB 7 — CALL HISTORY
# ════════════════════════════════════════════════════════════════
with tab7:
    st.subheader("📋 Call History")
    st.caption("Every LLM call ever made through this tool — prompt version, latency, full output.")

    try:
        history = api.get_history(limit=50)
    except Exception:
        history = []

    if not history:
        st.info("No calls logged yet.")
    else:
        total_calls = len(history)
        avg_latency = sum(h["latency_ms"] for h in history) / total_calls
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Calls", total_calls)
        col2.metric("Avg Latency", f"{avg_latency:.0f}ms")
        col3.metric("Prompt Versions", len(set(h["prompt_version"] for h in history)))

        st.markdown("---")

        for call in history:
            with st.expander(
                f"{call['timestamp'][:19]} — {call['mode']} — {call['latency_ms']}ms — v{call['prompt_version']}",
                expanded=False,
            ):
                st.markdown(f"**Mode:** `{call['mode']}`")
                st.markdown(f"**Prompt version:** `{call['prompt_version']}`")
                st.markdown(f"**Latency:** {call['latency_ms']}ms")
                st.markdown("**Input:**")
                st.text(call["user_input"][:400])
                st.markdown("**Output:**")
                st.text(call["full_output"][:600])
