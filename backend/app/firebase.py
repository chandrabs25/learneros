"""
Firebase Admin SDK initialization.
Handles service account credential loading and provides
the initialized Firebase app for token verification.
"""

import firebase_admin
from firebase_admin import credentials, auth

from app.config import settings

_firebase_app = None


def get_firebase_app() -> firebase_admin.App:
    """Initialize Firebase Admin SDK (singleton)."""
    global _firebase_app
    if _firebase_app is None:
        if settings.FIREBASE_SERVICE_ACCOUNT:
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT)
        else:
            # Fall back to Application Default Credentials (for Cloud environments)
            cred = credentials.ApplicationDefault()
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def verify_id_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token and return the decoded claims.

    Returns dict with: uid, email, name, picture, etc.
    Raises firebase_admin.auth.InvalidIdTokenError if invalid.
    """
    get_firebase_app()  # Ensure initialized
    return auth.verify_id_token(id_token)
