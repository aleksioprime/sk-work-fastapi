from fastapi import APIRouter, Depends, status, Request, Query, HTTPException, Path
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from src.db.postgres import get_db_session
from src.db.redis import get_redis
from src.services.promo import PromoService
from src.services.company import CompanyService
from src.services.user import UserService

oauth2_scheme_company = OAuth2PasswordBearer(tokenUrl="/api/business/auth/sign-in")
oauth2_scheme_user = OAuth2PasswordBearer(tokenUrl="/api/user/auth/sign-in")

router = APIRouter()

promo_service = PromoService()
company_service = CompanyService()
user_service = UserService()


@router.post(
        "/business/promo",
        status_code=status.HTTP_201_CREATED,
        )
async def create_promo(
    request: Request,
    token: str = Depends(oauth2_scheme_company),
    db: AsyncSession = Depends(get_db_session),
):
    body = await request.json()
    company_id = await company_service.validate_token(token)
    return await promo_service.promo_create(body, db, company_id)


@router.get(
    "/business/promo",
    status_code=status.HTTP_200_OK,
)
async def list_promos(
    token: str = Depends(oauth2_scheme_company),
    db: AsyncSession = Depends(get_db_session),
    country: str | None = Query(None, description="Страна/страны для фильтрации (ISO 3166-1 alpha-2, через запятую)"),
    sort_by: str | None = Query(None, regex="^(active_from|active_until|created_at)$", description="Сортировка по active_from, active_until или created_at"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    limit: int = Query(10, gt=0, description="Количество записей для пагинации"),
):
    """
    Получение списка промокодов с фильтрацией, сортировкой и пагинацией.
    """
    company_id = await company_service.validate_token(token)

    params = {
        "country": country,
        "sort_by": sort_by,
        "offset": offset,
        "limit": limit,
    }

    result = await promo_service.promo_get_list(db, company_id, params)

    total_count = result["total_count"]
    promos = result["promos"]

    headers = {"X-Total-Count": str(total_count)}
    return JSONResponse(content=promos, headers=headers)


@router.get(
        "/business/promo/{promo_id}",
        status_code=status.HTTP_200_OK,
        )
async def get_promo_by_id(
    promo_id: str,
    token: str = Depends(oauth2_scheme_company),
    db: AsyncSession = Depends(get_db_session)
    ):
    company_id = await company_service.validate_token(token)
    return await promo_service.promo_get_by_id(promo_id, db, company_id)


@router.patch(
        "/business/promo/{promo_id}",
        status_code=status.HTTP_200_OK,
        )
async def update_promo(
    promo_id: str,
    request: Request,
    token: str = Depends(oauth2_scheme_company),
    db: AsyncSession = Depends(get_db_session)
    ):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing JSON in the request body.")

    if not body:
        raise HTTPException(status_code=400, detail="Request body cannot be empty.")
    company_id = await company_service.validate_token(token)
    return await promo_service.promo_update(promo_id, body, db, company_id)


@router.get(
        "/user/feed",
        status_code=status.HTTP_200_OK,
        )
async def user_promo_feed(
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    country: str = None,
    search: str = None
    ):

    user_id = await user_service.validate_token(token)

    result = await promo_service.promo_user_get_list(db, user_id, country=country, search=search)
    total_count = result["total_count"]
    promos = result["promos"]

    headers = {"X-Total-Count": str(total_count)}
    return JSONResponse(content=promos, headers=headers)


@router.get(
        "/user/promo/history",
        status_code=status.HTTP_200_OK,
        )
async def promo_history(
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_history(user_id, db)


@router.get(
        "/user/promo/{promo_id}",
        status_code=status.HTTP_200_OK,
        )
async def get_user_promo_by_id(
    promo_id: str,
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_user_get_by_id(promo_id, db, user_id)


@router.post(
        "/user/promo/{promo_id}/like",
        status_code=status.HTTP_200_OK,
        )
async def like_promo(
    promo_id: str,
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_like_create(promo_id, user_id, db)


@router.delete(
        "/user/promo/{promo_id}/like",
        status_code=status.HTTP_200_OK)
async def unlike_promo(
    promo_id: str,
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_like_delete(promo_id, user_id, db)


@router.post(
        "/user/promo/{promo_id}/comments",
        status_code=status.HTTP_201_CREATED,
        )
async def add_comment(
    promo_id: str,
    request: Request,
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    body = await request.json()
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_comment_create(promo_id, user_id, body, db)


@router.get(
        "/user/promo/{promo_id}/comments",
        status_code=status.HTTP_200_OK,
        )
async def get_comments(
    promo_id: str,
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_comment_get_all(promo_id, db)


@router.get(
        "/user/promo/{promo_id}/comments/{comment_id}",
        status_code=status.HTTP_200_OK,
        )
async def get_comment_by_id(
    promo_id: str,
    comment_id: str,
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_comment_get_by_id(promo_id, comment_id, db)


@router.patch(
        "/user/promo/{promo_id}/comments/{comment_id}",
        status_code=status.HTTP_200_OK,
        )
async def update_comment(
    promo_id: str,
    comment_id: str,
    request: Request,
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    body = await request.json()
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_comment_update(promo_id, comment_id, user_id, body, db)


@router.delete(
        "/user/promo/{promo_id}/comments/{comment_id}",
        status_code=status.HTTP_200_OK,
        )
async def delete_comment(
    promo_id: str,
    comment_id: str,
    token: str = Depends(oauth2_scheme_user),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_comment_delete(promo_id, comment_id, user_id, db)


@router.post(
        "/user/promo/{promo_id}/activate",
        status_code=status.HTTP_200_OK,
        )
async def activate_promo(
    promo_id: str = Path(..., regex=r"^[a-fA-F0-9-]{36}$"),
    token: str = Depends(oauth2_scheme_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db_session),
    ):
    user_id = await user_service.validate_token(token)
    return await promo_service.promo_activate(promo_id, db, redis, user_id)


@router.get(
        "/business/promo/{promo_id}/stat",
        status_code=status.HTTP_200_OK,
        )
async def promo_statistics(
    promo_id: str,
    token: str = Depends(oauth2_scheme_company),
    db: AsyncSession = Depends(get_db_session),
    ):
    company_id = await company_service.validate_token(token)
    return await promo_service.promo_stat(promo_id, company_id, db)