"""Authentication endpoints: register, login, and current-user."""

from fastapi import APIRouter, Depends, HTTPException, status

from .. import db
from ..models import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from ..security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    if await db.users().find_one({"username": payload.username}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

    await db.users().insert_one(
        {
            "username": payload.username,
            "email": payload.email,
            "password_hash": hash_password(payload.password),
            "role": "user",
        }
    )
    return TokenResponse(access_token=create_access_token(payload.username))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    user = await db.users().find_one({"username": payload.username})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenResponse(access_token=create_access_token(payload.username))


@router.get("/me", response_model=UserPublic)
async def me(username: str = Depends(get_current_user)):
    user = await db.users().find_one({"username": username})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserPublic(
        username=user["username"], email=user["email"], role=user.get("role", "user")
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest, username: str = Depends(get_current_user)
):
    user = await db.users().find_one({"username": username})
    if not user or not verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    await db.users().update_one(
        {"username": username},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
