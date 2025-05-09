from typing import Optional, Dict
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_db_session
from src.services.promo import PromoService
from src.services.company import CompanyService
from src.services.user import UserService


user_service = UserService()

oauth2_scheme_user = OAuth2PasswordBearer(tokenUrl="/api/user/auth/sign-in")

router = APIRouter()


@router.post(
        "/user/auth/sign-up",
        status_code=status.HTTP_201_CREATED,
        )
async def user_sign_up(
    request: dict,
    db: AsyncSession = Depends(get_db_session),
    ):
    return await user_service.sign_up(request, db)


@router.post(
        "/user/auth/sign-in",
        status_code=status.HTTP_200_OK,
        )
async def user_sign_in(
    request: dict = Body(None),
    db: AsyncSession = Depends(get_db_session),
    ):
    if not request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is required",
        )
    return await user_service.sign_in(request, db)


@router.get(
        "/user/profile",
        status_code=status.HTTP_200_OK,
        )
async def get_profile(
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await user_service.profile_get(user_id, db)


@router.patch(
        "/user/profile",
        status_code=status.HTTP_200_OK,
        )
async def update_profile(
    request: dict,
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await user_service.profile_update(user_id, request, db)