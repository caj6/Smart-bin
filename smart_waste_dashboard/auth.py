"""
auth.py
-------
Authentication module for Smart Waste Admin Dashboard.
Currently uses hardcoded credentials — designed for easy JWT/API swap later.

To add a new admin:  add an entry to ADMIN_USERS below.
To go live with JWT: replace check_credentials() with a FastAPI /auth/token call.
"""

import streamlit as st
import hashlib
import hmac
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# ADMIN CREDENTIALS
# Passwords are SHA-256 hashed for basic safety.
# Generate hash: hashlib.sha256("yourpassword".encode()).hexdigest()
# ─────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

ADMIN_USERS = {
    "admin": {
        "password_hash": _hash("admin123"),
        "display_name":  "System Administrator",
        "role":          "SUPER_ADMIN",
        "avatar":        "🛡️",
    },
    "operator": {
        "password_hash": _hash("waste2026"),
        "display_name":  "Bin Operator",
        "role":          "OPERATOR",
        "avatar":        "🗑️",
    },
}

SESSION_TIMEOUT_MINUTES = 60


# ─────────────────────────────────────────────
# AUTH LOGIC
# ─────────────────────────────────────────────

def check_credentials(username: str, password: str) -> bool:
    """Validate username + password. Returns True if valid."""
    # TODO: replace with httpx.post(f"{API_BASE_URL}/auth/token") for JWT
    user = ADMIN_USERS.get(username.lower().strip())
    if not user:
        return False
    return hmac.compare_digest(user["password_hash"], _hash(password))


def get_user_info(username: str) -> dict:
    return ADMIN_USERS.get(username.lower().strip(), {})


def is_session_valid() -> bool:
    """Check if the current session is authenticated and not timed out."""
    if not st.session_state.get("authenticated", False):
        return False
    login_time = st.session_state.get("login_time")
    if login_time is None:
        return False
    elapsed = datetime.utcnow() - login_time
    if elapsed > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        logout()
        return False
    return True


def login(username: str):
    """Set session state on successful login."""
    info = get_user_info(username)
    st.session_state.authenticated   = True
    st.session_state.username        = username.lower().strip()
    st.session_state.display_name    = info.get("display_name", username)
    st.session_state.role            = info.get("role", "OPERATOR")
    st.session_state.avatar          = info.get("avatar", "👤")
    st.session_state.login_time      = datetime.utcnow()
    st.session_state.login_attempts  = 0


def logout():
    """Clear all auth session state."""
    for key in ["authenticated", "username", "display_name", "role",
                "avatar", "login_time"]:
        st.session_state.pop(key, None)


# ─────────────────────────────────────────────
# LOGIN PAGE RENDERER
# ─────────────────────────────────────────────

def render_login_page():
    """Render the full-page login UI. Returns True if just logged in."""

    # Init attempt counter
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
        background-color: #0f172a;
        color: #e2e8f0;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse at 20% 50%, #0ea5e920 0%, transparent 50%),
            radial-gradient(ellipse at 80% 20%, #7c3aed15 0%, transparent 50%),
            #0f172a;
        min-height: 100vh;
    }
    [data-testid="block-container"] {
        max-width: 440px !important;
        margin: 0 auto;
        padding-top: 8vh;
    }
    #MainMenu, footer, header { visibility: hidden; }

    /* Input fields */
    [data-testid="stTextInput"] input {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.9rem !important;
        padding: 0.6rem 1rem !important;
        transition: border-color 0.2s;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 3px rgba(56,189,248,0.15) !important;
    }
    [data-testid="stTextInput"] label {
        color: #94a3b8 !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        font-family: 'IBM Plex Mono', monospace !important;
    }

    /* Login button */
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #0ea5e9, #38bdf8) !important;
        color: #0f172a !important;
        font-weight: 700 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.1em !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.65rem !important;
        width: 100% !important;
        transition: opacity 0.2s, transform 0.1s !important;
    }
    [data-testid="stFormSubmitButton"] button:hover {
        opacity: 0.9 !important;
        transform: translateY(-1px) !important;
    }
    [data-testid="stFormSubmitButton"] button:active {
        transform: translateY(0) !important;
    }

    .login-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 20px;
        padding: 2.5rem 2rem;
        box-shadow: 0 25px 50px rgba(0,0,0,0.5);
    }
    .login-logo {
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .login-icon {
        font-size: 3rem;
        display: block;
        margin-bottom: 0.5rem;
        filter: drop-shadow(0 0 20px rgba(56,189,248,0.4));
    }
    .login-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.15rem;
        font-weight: 600;
        color: #f8fafc;
        letter-spacing: -0.01em;
    }
    .login-sub {
        font-size: 0.7rem;
        color: #64748b;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 0.2rem;
    }
    .login-divider {
        border: none;
        border-top: 1px solid #334155;
        margin: 1.5rem 0 1.2rem;
    }
    .hint-box {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        color: #64748b;
        margin-top: 1rem;
        line-height: 1.7;
    }
    .hint-box span { color: #38bdf8; }
    .lockout-box {
        background: #450a0a;
        border: 1px solid #dc262655;
        border-radius: 10px;
        padding: 0.6rem 1rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: #fca5a5;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .footer-note {
        text-align: center;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.6rem;
        color: #334155;
        margin-top: 2rem;
        letter-spacing: 0.08em;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Login Card ──
    st.markdown("""
    <div class="login-card">
        <div class="login-logo">
            <span class="login-icon">🗑️</span>
            <div class="login-title">SmartBin Admin</div>
            <div class="login-sub">Waste Management System</div>
        </div>
        <hr class="login-divider">
    </div>
    """, unsafe_allow_html=True)

    # Lockout after 5 failed attempts
    locked = st.session_state.login_attempts >= 5

    with st.container():
        if locked:
            st.markdown('<div class="lockout-box">🔒 Too many failed attempts. Restart the app to try again.</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", placeholder="Enter your password", type="password")
            submitted = st.form_submit_button("→  Sign In", disabled=locked, use_container_width=True)

        if submitted and not locked:
            if check_credentials(username, password):
                login(username)
                st.rerun()
            else:
                st.session_state.login_attempts += 1
                remaining = 5 - st.session_state.login_attempts
                if remaining > 0:
                    st.error(f"❌ Invalid username or password. {remaining} attempt{'s' if remaining != 1 else ''} remaining.")
                else:
                    st.rerun()

    # Dev hint box (remove in production)
    st.markdown("""
    <div class="hint-box">
        🔑 <b style="color:#94a3b8;">DEV CREDENTIALS</b><br>
        Admin &nbsp;&nbsp;→ &nbsp;<span>admin</span> / <span>admin123</span><br>
        Operator → <span>operator</span> / <span>waste2026</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="footer-note">SMARTBIN v1.0 · ADMIN ACCESS ONLY · © 2026</div>', unsafe_allow_html=True)
