
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash


load_dotenv()

# Password hashing configuration
password_hash = PasswordHash.recommended()

# JWT configuration
ALGORITHM = "HS256"


def get_secret_key() -> str:
    """Get the JWT secret key from environment variables."""
    secret_key = os.getenv("AUTH_SECRET_KEY")

    if not secret_key:
        raise RuntimeError(
            "AUTH_SECRET_KEY is missing from environment variables."
        )

    return secret_key


def hash_password(password: str) -> str:
    """Generate a secure Argon2 password hash."""
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """Verify a password against its stored hash."""
    return password_hash.verify(
        plain_password,
        hashed_password
    )


def create_access_token(
    data: dict,
    expires_minutes: int | None = None
) -> str:
    """Create a signed JWT access token."""

    if expires_minutes is None:
        expires_minutes = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )

    payload = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes
    )

    payload.update({
        "exp": expire
    })

    token = jwt.encode(
        payload,
        get_secret_key(),
        algorithm=ALGORITHM
    )

    return token


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token."""

    try:
        payload = jwt.decode(
            token,
            get_secret_key(),
            algorithms=[ALGORITHM]
        )

        return payload

    except jwt.InvalidTokenError:
        return None
