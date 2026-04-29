import hashlib
import hmac
import uuid

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import jwt as jwt_utils
from app.auth.schemas import RegisterRequest, TokenResponse
from app.crud import user as user_crud
from app.models.user import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _hash_token(token: str) -> str:
    # Refresh tokens are long JWTs (>72 bytes) — bcrypt would truncate them.
    # SHA-256 is safe here since the token already has cryptographic entropy.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _verify_token_hash(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(_hash_token(token), stored_hash)


def _make_tokens(user: User) -> TokenResponse:
    access = jwt_utils.create_access_token(user.id)
    refresh = jwt_utils.create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


async def register(db: AsyncSession, req: RegisterRequest) -> User:
    if await user_crud.get_by_username(db, req.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    if await user_crud.get_by_email(db, req.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return await user_crud.create(db, req.username, req.email, hash_password(req.password))


async def login(db: AsyncSession, username: str, password: str) -> TokenResponse:
    user = await user_crud.get_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    tokens = _make_tokens(user)
    await user_crud.update_refresh_token(db, user.id, _hash_token(tokens.refresh_token))
    return tokens


async def refresh(db: AsyncSession, refresh_token: str) -> TokenResponse:
    payload = jwt_utils.decode_token(refresh_token, expected_type="refresh")
    user_id = uuid.UUID(payload["sub"])
    user = await user_crud.get_by_id(db, user_id)
    if not user or not user.refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please log in again")
    if not _verify_token_hash(refresh_token, user.refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    tokens = _make_tokens(user)
    await user_crud.update_refresh_token(db, user.id, _hash_token(tokens.refresh_token))
    return tokens


async def logout(db: AsyncSession, user: User) -> None:
    await user_crud.update_refresh_token(db, user.id, None)
