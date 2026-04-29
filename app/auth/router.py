from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service as auth_service
from app.auth.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    summary="Register a new user",
    responses={
        201: {"description": "User created"},
        409: {"description": "Username or email already exists"},
        422: {"description": "Validation error"},
    },
)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)) -> UserResponse:
    user = await auth_service.register(db, req)
    return UserResponse(id=str(user.id), username=user.username, email=user.email, is_active=user.is_active)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain JWT tokens",
    responses={
        200: {"description": "Access and refresh tokens"},
        401: {"description": "Invalid credentials"},
    },
)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.login(db, req.username, req.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange refresh token for a new token pair",
    responses={
        200: {"description": "New access and refresh tokens"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.refresh(db, req.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate the current refresh token",
    responses={
        204: {"description": "Logged out successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.logout(db, current_user)
