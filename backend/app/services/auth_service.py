import os
import time
import json
import base64
import hmac
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models import User

# Read SECRET_KEY or generate a persistent fallback
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cloudlearn-ai-secure-jwt-secret-key-2026")


def hash_password(plain_password: str) -> str:
    """
    Hashes a plain password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a 16-byte random salt.
    Format: pbkdf2:sha256:100000$<salt_hex>$<hash_hex>
    """
    salt = secrets.token_bytes(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
    return f"pbkdf2:sha256:{iterations}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against the stored PBKDF2 hash using constant-time comparison.
    """
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        meta, salt_hex, expected_hash_hex = parts
        _, _, iterations_str = meta.split(":")
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        derived = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(derived.hex(), expected_hash_hex)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = "=" * (4 - (len(s) % 4)) if len(s) % 4 != 0 else ""
    return base64.urlsafe_b64decode(s + padding)


def create_access_token(user_id: str, username: str, email: str, expires_in_seconds: int = 7 * 86400) -> str:
    """
    Generates an RFC 7519 HMAC-SHA256 signed JSON Web Token (JWT).
    """
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "email": email,
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{signing_input}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and verifies a JWT token. Returns payload dict if valid and unexpired; None otherwise.
    """
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check expiration
        exp = payload.get("exp", 0)
        if time.time() > exp:
            return None

        return payload
    except Exception:
        return None


def register_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None,
) -> Tuple[User, str]:
    """
    Registers a new user in Neon PostgreSQL, returning (user, token).
    Raises ValueError if username or email already exists or is invalid.
    """
    username_clean = username.strip().lower()
    email_clean = email.strip().lower()

    if len(username_clean) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if "@" not in email_clean or "." not in email_clean:
        raise ValueError("Please provide a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    # Check for existing user
    existing = db.query(User).filter(
        (User.username == username_clean) | (User.email == email_clean)
    ).first()

    if existing:
        if existing.username.lower() == username_clean:
            raise ValueError(f"Username '{username_clean}' is already registered.")
        else:
            raise ValueError(f"Email '{email_clean}' is already registered.")

    hashed = hash_password(password)
    user = User(
        username=username_clean,
        email=email_clean,
        hashed_password=hashed,
        full_name=full_name.strip() if full_name else username_clean,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user_id=user.username,
        username=user.username,
        email=user.email,
    )
    return user, token


def authenticate_user(
    db: Session,
    username_or_email: str,
    password: str,
) -> Optional[Tuple[User, str]]:
    """
    Authenticates user with username or email and password.
    Returns (user, token) if successful, None otherwise.
    """
    ident = username_or_email.strip().lower()
    user = db.query(User).filter(
        (User.username == ident) | (User.email == ident)
    ).first()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    token = create_access_token(
        user_id=user.username,
        username=user.username,
        email=user.email,
    )
    return user, token


def get_user_by_id_or_username(db: Session, identifier: str) -> Optional[User]:
    """Retrieves a user by username or numeric id."""
    ident = identifier.strip().lower()
    if ident.isdigit():
        u = db.query(User).filter(User.id == int(ident)).first()
        if u:
            return u
    return db.query(User).filter(User.username == ident).first()

