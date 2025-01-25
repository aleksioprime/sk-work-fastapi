from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_db_session
from src.services.company import CompanyService

router = APIRouter()

company_service = CompanyService()


@router.post(
        "/business/auth/sign-up",
        status_code=status.HTTP_200_OK,
        )
async def company_sign_up(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    ):
    body = await request.json()
    return await company_service.sign_up(body, db)

@router.post(
        "/business/auth/sign-in",
        status_code=status.HTTP_200_OK,
        )
async def company_sign_in(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    ):
    body = await request.json()
    return await company_service.sign_in(body, db)
