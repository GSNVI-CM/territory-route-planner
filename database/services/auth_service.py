"""Streamlit authentication and role-access shell.

Version 1 has Consultant and Leadership roles. In development, when no users
are configured, the app grants a local Consultant session so the project can be
run without committing credentials. Hosted deployment should configure users
through Streamlit secrets.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

import streamlit as st


CONSULTANT = "Consultant"
LEADERSHIP = "Leadership"
VALID_ROLES = {CONSULTANT, LEADERSHIP}


@dataclass(frozen=True)
class AuthenticatedUser:
    email: str
    display_name: str
    role: str


def _configured_users() -> list[dict[str, Any]]:
    try:
        auth = st.secrets.get("auth", {})
        users = auth.get("users", [])
        return [dict(user) for user in users]
    except Exception:
        return []


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _password_matches(password: str, configured: dict[str, Any]) -> bool:
    expected_hash = str(configured.get("password_hash", ""))
    if expected_hash:
        return hmac.compare_digest(_hash_password(password), expected_hash)
    # Plain passwords are supported only to make initial setup manageable.
    expected_password = str(configured.get("password", ""))
    return bool(expected_password) and hmac.compare_digest(password, expected_password)


def _set_session(user: AuthenticatedUser) -> None:
    st.session_state["authenticated_user"] = {
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }


def current_user() -> AuthenticatedUser | None:
    value = st.session_state.get("authenticated_user")
    if not value:
        return None
    return AuthenticatedUser(**value)


def require_authentication() -> AuthenticatedUser:
    users = _configured_users()

    # Local development fallback. It is disabled automatically when users exist.
    if not users:
        user = AuthenticatedUser(
            email="local-consultant@development.invalid",
            display_name="Misty",
            role=CONSULTANT,
        )
        _set_session(user)
        return user

    existing = current_user()
    if existing:
        return existing

    st.title("Professional Relations Platform")
    st.subheader("Sign in")
    with st.form("sign_in_form", clear_on_submit=False):
        email = st.text_input("Email").strip().lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        configured = next(
            (user for user in users if str(user.get("email", "")).strip().lower() == email),
            None,
        )
        if configured and _password_matches(password, configured):
            role = str(configured.get("role", CONSULTANT))
            if role not in VALID_ROLES:
                st.error("This account has an invalid role configuration.")
            else:
                _set_session(
                    AuthenticatedUser(
                        email=email,
                        display_name=str(configured.get("display_name", email)),
                        role=role,
                    )
                )
                st.rerun()
        else:
            st.error("Email or password was not recognized.")

    st.stop()


def sign_out() -> None:
    st.session_state.pop("authenticated_user", None)
    st.rerun()


def require_role(*allowed_roles: str) -> AuthenticatedUser:
    user = require_authentication()
    if user.role not in allowed_roles:
        st.error("You do not have access to this section.")
        st.stop()
    return user
