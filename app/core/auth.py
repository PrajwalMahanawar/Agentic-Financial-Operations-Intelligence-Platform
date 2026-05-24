from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import base64
import hashlib
import hmac
import json

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class User:
    email: str
    role: str


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def _parse_users(settings: Settings) -> dict[str, tuple[str, str]]:
    users: dict[str, tuple[str, str]] = {}
    for raw_user in settings.auth_users.split(","):
        if not raw_user.strip():
            continue
        email, password, role = raw_user.split(":", 2)
        users[email.strip().lower()] = (password, role.strip())
    return users


def authenticate(email: str, password: str, settings: Settings) -> User | None:
    stored = _parse_users(settings).get(email.lower())
    if stored is None:
        return None
    expected_password, role = stored
    if not hmac.compare_digest(expected_password, password):
        return None
    return User(email=email.lower(), role=role)


def create_access_token(user: User, settings: Settings) -> str:
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.auth_token_ttl_seconds)
    payload = {"sub": user.email, "role": user.role, "exp": int(expires_at.timestamp())}
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(settings.auth_secret_key.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def decode_access_token(token: str, settings: Settings) -> User:
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(settings.auth_secret_key.encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(signature), expected):
            raise ValueError("bad signature")
        payload = json.loads(_b64decode(body))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    if int(payload["exp"]) < int(datetime.now(UTC).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")
    return User(email=payload["sub"], role=payload["role"])


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        return User(email="anonymous", role="admin" if settings.environment == "development" else "anonymous")
    return decode_access_token(credentials.credentials, settings)


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role.")
        return user

    return dependency
