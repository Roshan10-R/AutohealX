import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import JWT_SECRET, JWT_TTL_HOURS

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split(":", 1)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310_000)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def create_access_token(user_id: str) -> str:
    now = int(time.time())
    header = _b64encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = _b64encode(json.dumps({"sub": user_id, "iat": now, "exp": now + JWT_TTL_HOURS * 3600}).encode())
    message = f"{header}.{payload}".encode()
    signature = hmac.new(JWT_SECRET.encode(), message, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64encode(signature)}"


def _decode_access_token(token: str) -> str:
    try:
        header, payload, signature = token.split(".")
        message = f"{header}.{payload}".encode()
        expected = _b64encode(hmac.new(JWT_SECRET.encode(), message, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if claims.get("exp", 0) <= time.time() or not claims.get("sub"):
            raise ValueError("Expired or incomplete token")
        return str(claims["sub"])
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    from app.database import db

    user_id = _decode_access_token(credentials.credentials)
    user = db.users.find_one({"_id": user_id}, {"password_hash": 0})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user
