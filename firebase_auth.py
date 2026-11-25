"""
Firebase Authentication & Token Verification Module for SYNTRIQ.
Verifies Google/Firebase ID tokens cryptographically using google-auth
without exposing any private keys or service account secrets to the frontend.
"""

import json
import os
import time
from typing import Any, Dict, Optional

import google.auth.transport.requests
import google.oauth2.id_token

_GOOGLE_REQUEST = google.auth.transport.requests.Request()
_FIREBASE_ADMIN_APP = None

# Public Firebase Web SDK client configuration (safe for client exposure;
# security is enforced by Cloud Firestore Rules & Firebase Auth Authorized Domains).
# Environment variables always take precedence when configured.
DEFAULT_FIREBASE_WEB_CONFIG: Dict[str, str] = {
    "apiKey": "AIzaSyAdFaKmVwhsM0gwwTxgnIZ7a3t-S9omsrI",
    "authDomain": "study-planner-b8fe1.firebaseapp.com",
    "projectId": "study-planner-b8fe1",
    "storageBucket": "study-planner-b8fe1.firebasestorage.app",
    "messagingSenderId": "612179872774",
    "appId": "1:612179872774:web:15f8c5ffdd2d0f91430787",
    "measurementId": "G-PW49D3MVE1",
}


def get_firebase_web_config() -> Dict[str, str]:
    """Returns public Firebase Web SDK configuration from env vars or public default."""
    return {
        "apiKey": os.environ.get("FIREBASE_API_KEY", "").strip() or DEFAULT_FIREBASE_WEB_CONFIG["apiKey"],
        "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", "").strip() or DEFAULT_FIREBASE_WEB_CONFIG["authDomain"],
        "projectId": os.environ.get("FIREBASE_PROJECT_ID", "").strip() or DEFAULT_FIREBASE_WEB_CONFIG["projectId"],
        "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", "").strip() or DEFAULT_FIREBASE_WEB_CONFIG["storageBucket"],
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "").strip() or DEFAULT_FIREBASE_WEB_CONFIG["messagingSenderId"],
        "appId": os.environ.get("FIREBASE_APP_ID", "").strip() or DEFAULT_FIREBASE_WEB_CONFIG["appId"],
        "measurementId": os.environ.get("FIREBASE_MEASUREMENT_ID", "").strip() or DEFAULT_FIREBASE_WEB_CONFIG["measurementId"],
    }


def is_firebase_configured() -> bool:
    """Returns True when minimum required Firebase Web configuration values are present."""
    cfg = get_firebase_web_config()
    return bool(
        cfg["apiKey"]
        and cfg["authDomain"]
        and cfg["projectId"]
        and not cfg["apiKey"].startswith("your-")
        and not cfg["projectId"].startswith("your-")
    )


def _get_admin_auth():
    """Lazily initializes firebase_admin only if explicit service account credentials exist."""
    global _FIREBASE_ADMIN_APP
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not sa_json and not sa_path:
        return None

    try:
        import firebase_admin
        from firebase_admin import auth as admin_auth, credentials

        if not firebase_admin._apps:
            if sa_json:
                cred_info = json.loads(sa_json)
                cred = credentials.Certificate(cred_info)
            else:
                cred = credentials.Certificate(sa_path)
            _FIREBASE_ADMIN_APP = firebase_admin.initialize_app(cred)
        return admin_auth
    except Exception:
        return None


def verify_firebase_id_token(id_token: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Verifies a Firebase ID token and returns normalized user identity claims:
    {uid, email, name, picture, email_verified, exp}.
    Raises ValueError if the token is invalid, expired, or mismatched.
    """
    if not id_token or not isinstance(id_token, str):
        raise ValueError("Missing Firebase ID token.")

    target_project = (project_id or get_firebase_web_config()["projectId"]).strip()
    if not target_project:
        raise ValueError("FIREBASE_PROJECT_ID is not configured.")

    admin_auth = _get_admin_auth()
    if admin_auth is not None:
        try:
            claims = admin_auth.verify_id_token(id_token, check_revoked=True)
        except Exception as exc:
            raise ValueError(f"Firebase token verification failed: {exc}") from exc
    else:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token,
                _GOOGLE_REQUEST,
                audience=target_project,
            )
        except Exception as exc:
            raise ValueError(f"Firebase token verification failed: {exc}") from exc

    if not claims:
        raise ValueError("Empty Firebase token claims.")

    uid = claims.get("user_id") or claims.get("sub")
    if not uid or not isinstance(uid, str):
        raise ValueError("Firebase token missing valid UID claim.")

    exp = int(claims.get("exp", 0))
    if exp and exp < int(time.time()):
        raise ValueError("Firebase ID token has expired.")

    return {
        "uid": uid,
        "email": claims.get("email", ""),
        "name": claims.get("name") or claims.get("email", "SYNTRIQ Student").split("@")[0],
        "picture": claims.get("picture", ""),
        "email_verified": bool(claims.get("email_verified", False)),
        "exp": exp,
    }
