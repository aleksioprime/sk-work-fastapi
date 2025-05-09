from typing import Optional
from uuid import uuid4
import re
from datetime import datetime, timezone, timedelta
import pycountry

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
from redis.asyncio import Redis

from fastapi import HTTPException, status

from src.core.config import settings
from src.models.promo import Promo, PromoActivation, Comment, Like
from src.services.user import UserService
from src.services.antifraud import AntifraudService

user_service = UserService()
antifraud_service = AntifraudService(antifraud_address=settings.antifraud)

class PromoService:

    def __init__(self):
        self.iso_3166_regex = re.compile(r"^[a-z]{2}$")

    async def promo_create(self, body: dict, db: AsyncSession, company_id: str) -> dict:
        """
        Создание компанией нового промокода
        POST /business/promo
        """
        # Проверка наличия обязательных полей
        required_fields = ["description", "target", "max_count", "mode"]
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Валидация входящих данных
        errors = self.validate_promo(body)
        if errors:
            raise HTTPException(status_code=400, detail=errors)

        promo = Promo(
            id=str(uuid4()),
            company_id=company_id,
            description=body["description"],
            image_url=body.get("image_url"),
            mode=body["mode"],
            promo_common=body.get("promo_common"),
            promo_unique=body.get("promo_unique"),
            target=body["target"],
            max_count=body["max_count"],
            active_from=self.parse_optional_date(body.get("active_from")),
            active_until=self.parse_optional_date(body.get("active_until")),
            active=True,
            created_at=datetime.utcnow(),
        )

        try:
            db.add(promo)
            await db.commit()
            return {"id": promo.id}
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create promo due to database integrity error.",
            )

    def parse_optional_date(self, date_str: str | None, default: datetime | None = None) -> datetime | None:
        """
        Парсит строку даты в объект datetime. Возвращает значение по умолчанию, если дата отсутствует.
        """
        if date_str:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format for '{date_str}'. Expected format: YYYY-MM-DD")
        return default

    async def promo_get_list(self, db: AsyncSession, company_id: str, params: dict) -> dict:
        """
        Получение списка промокодов компании
        GET /business/promo
        """
        base_query = select(Promo).where(Promo.company_id == company_id)

        # Фильтрация по странам
        if country_param := params.get("country"):
            countries = [c.strip().lower() for c in country_param.split(",")]
            country_filters = [Promo.target.op("@>")({"country": country}) for country in countries]
            base_query = base_query.filter(
                or_(
                    *country_filters,
                    Promo.target == {},
                    Promo.target.is_(None)
                )
            )

        # Подсчет общего количества записей
        total_query = select(func.count()).select_from(base_query.subquery())
        total_count = (await db.execute(total_query)).scalar()

        # Сортировка
        sort_field = {
            "active_from": Promo.active_from,
            "active_until": Promo.active_until,
            "created_at": Promo.created_at,
        }.get(params.get("sort_by"), Promo.created_at)
        base_query = base_query.order_by(sort_field.desc())

        # Пагинация
        offset = int(params.get("offset", 0))
        limit = int(params.get("limit", 10))
        paginated_query = base_query.offset(offset).limit(limit)

        # Получение данных
        promos = (await db.execute(paginated_query)).scalars().all()

        # Преобразование данных в словари
        promos_dicts = [
            {
                "id": str(promo.id),
                "description": promo.description,
                "image_url": promo.image_url,
                "target": promo.target if promo.target else {},
                "max_count": promo.max_count,
                "active_from": promo.active_from.strftime('%Y-%m-%d') if promo.active_from else None,
                "active_until": promo.active_until.strftime('%Y-%m-%d') if promo.active_until else None,
                "mode": promo.mode,
                "promo_common": promo.promo_common,
                "promo_unique": promo.promo_unique,
                "created_at": promo.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for promo in promos
        ]

        return {
            "total_count": total_count,
            "promos": promos_dicts,
        }

    async def promo_get_by_id(self, promo_id: int, db: AsyncSession, company_id: str) -> dict:
        """
        Получение данных промокода по его ID. Сервер должен проверять принадлежность промокода компании
        GET /business/promo/{id}
        """
        # Получение промокода из базы данных
        query = (
            select(Promo)
            .options(
                joinedload(Promo.company),  # Загрузка связанных данных о компании
                joinedload(Promo.likes),   # Загрузка лайков
                joinedload(Promo.comments)  # Загрузка комментариев
            )
            .where(Promo.id == promo_id)
        )

        # Выполнение запроса
        result = await db.execute(query)
        promo = result.scalar()

        print(promo.company_id, company_id)

        # Проверка наличия промокода и принадлежности компании
        if not promo or str(promo.company_id) != company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo not found or not authorized."
            )

        # Преобразование данных в словарь
        promo_dict = {
            "promo_id": str(promo.id),
            "description": promo.description,
            "image_url": promo.image_url,
            "target": promo.target or {},
            "max_count": promo.max_count,
            "active_from": promo.active_from.strftime('%Y-%m-%d') if promo.active_from else None,
            "active_until": promo.active_until.strftime('%Y-%m-%d') if promo.active_until else None,
            "mode": promo.mode,
            "promo_common": promo.promo_common,
            "promo_unique": promo.promo_unique or [],
            "company_name": promo.company.name if promo.company else None,
            "like_count": len(promo.likes),
            "used_count": len(promo.comments),
            "active": promo.active,
        }

        return promo_dict

    async def promo_update(self, promo_id: int, body: dict, db: AsyncSession, company_id: str) -> dict:
        """
        Редактирование компанией данных промокода по его ID
        PATCH /business/promo/{id}
        """
        # Загружаем промокод с предзагрузкой связанных данных
        query = (
            select(Promo)
            .options(
                joinedload(Promo.company),
                joinedload(Promo.likes),
                joinedload(Promo.comments),
            )
            .where(Promo.id == promo_id)
        )
        result = await db.execute(query)
        promo = result.scalar()

        # Проверка прав доступа
        if not promo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo not found.",
            )
        if str(promo.company_id) != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to edit this promo.",
            )

        # Валидация входящих данных
        errors = self.validate_promo(body, promo)
        if errors:
            raise HTTPException(status_code=400, detail=errors)

        # Обновление данных промокода
        for key, value in body.items():
            if key == "target" and isinstance(value, dict):  # Обновление `target` (JSONB)
                promo.target = {**(promo.target or {}), **value} if value else {}
            elif hasattr(promo, key):  # Обновление других полей
                if key in ["active_from", "active_until"]:  # Преобразование строковых дат
                    value = datetime.strptime(value, "%Y-%m-%d") if value else None
                setattr(promo, key, value)

        # Обновляем `updated_at`
        promo.updated_at = datetime.utcnow()

        try:
            # Сохранение изменений
            await db.commit()
            promo_dict = {
                "promo_id": str(promo.id),
                "description": promo.description,
                "image_url": promo.image_url,
                "target": promo.target or {},
                "max_count": promo.max_count,
                "active_from": promo.active_from.strftime("%Y-%m-%d") if promo.active_from else None,
                "active_until": promo.active_until.strftime("%Y-%m-%d") if promo.active_until else None,
                "mode": promo.mode,
                "promo_common": promo.promo_common,
                "promo_unique": promo.promo_unique or [],
                "company_name": promo.company.name if promo.company else None,
                "like_count": len(promo.likes),
                "used_count": len(promo.comments),
                "active": promo.active,
            }
            return promo_dict
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update promo."
            )

    def validate_promo(self, body: dict, promo: Optional[Promo] = None) -> dict:
        # Валидация входящих данных
        errors = []

        if "description" in body and len(body["description"]) < 10:
            errors.append({"field": "description", "msg": "Description must be at least 10 characters long."})

        if "mode" in body:
            if body["mode"] not in {"COMMON", "UNIQUE"}:
                errors.append({"field": "mode", "msg": "Invalid mode. Allowed values are 'COMMON' or 'UNIQUE'."})

            if body["mode"] == "COMMON" and "promo_common" not in body:
                errors.append({"field": "promo_common", "msg": "promo_common is required for mode 'COMMON'."})

            if body["mode"] == "UNIQUE" and "promo_unique" not in body:
                errors.append({"field": "promo_unique", "msg": "promo_unique is required for mode 'UNIQUE'."})

        if "image_url" in body:
            if not isinstance(body["image_url"], str):
                errors.append({"field": "image_url", "msg": "Image URL must be a valid string."})
            elif not body["image_url"].startswith(("http://", "https://")):
                errors.append({"field": "image_url", "msg": "Image URL must start with 'http://' or 'https://'."})

        if "target" in body:
            target = body["target"]
            age_from = target.get("age_from")
            age_until = target.get("age_until")
            if age_from is not None and age_until is not None and age_from > age_until:
                errors.append({"field": "target", "msg": "'age_from' cannot be greater than 'age_until'."})
            categories = target.get("categories", [])
            if any(not category for category in categories):
                errors.append({"field": "target.categories", "msg": "Categories cannot contain empty values."})
            country = target.get("country")
            if country is not None and not pycountry.countries.get(alpha_2=country.upper()):
                errors.append({"field": "target.country", "msg": "Country must be a valid ISO 3166-1 alpha-2 code."})


        if "max_count" in body and promo is not None and promo.mode == "UNIQUE" and body["max_count"] != 1:
            errors.append({"field": "max_count", "msg": "For UNIQUE mode, max_count must be 1."})

        if "active_from" in body:
            try:
                datetime.strptime(body["active_from"], "%Y-%m-%d")
            except ValueError:
                errors.append({"field": "active_from", "msg": "Active_from must be in 'YYYY-MM-DD' format."})

        if "active_until" in body:
            try:
                if body["active_until"]:
                    datetime.strptime(body["active_until"], "%Y-%m-%d")
            except ValueError:
                errors.append({"field": "active_until", "msg": "Active_until must be in 'YYYY-MM-DD' format."})

        return errors

    async def promo_user_get_list(self, db: AsyncSession, user_id: str, country: str = None, search: str = None) -> dict:
        """
        Получение пользователем ленты промокодов
        GET /user/feed
        """
        # Определяем текущую дату в UTC+3 и делаем её наивной
        current_time = (datetime.now(timezone.utc) + timedelta(hours=3)).replace(tzinfo=None)

        # Подзапрос для подсчета количества активаций (если требуется)
        common_count_subquery = (
            select(func.count()).where(Promo.mode == "COMMON").label("common_count")
        )

        # Базовый запрос для активных промокодов
        query = select(Promo).where(
            and_(
                Promo.active == True,
                Promo.active_from <= current_time,
                or_(Promo.active_until.is_(None), Promo.active_until >= current_time),
                or_(
                    and_(Promo.mode == "COMMON", Promo.max_count > common_count_subquery),
                    and_(Promo.mode == "UNIQUE", Promo.promo_unique.is_not(None))
                )
            )
        )

        # Подсчет общего количества записей
        total_query = select(func.count()).select_from(query.subquery())
        total_count = (await db.execute(total_query)).scalar()

        # Фильтрация по стране
        if country:
            query = query.filter(Promo.target["country"].astext.ilike(f"%{country}%"))

        # Поиск по строке search (регистронезависимый)
        if search:
            search_pattern = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Promo.description).ilike(search_pattern),
                    func.lower(Promo.promo_common).ilike(search_pattern)
                )
            )

        # Выполнение запроса
        promos = (await db.execute(query)).scalars().all()

        promos_dicts = [
            {
                "id": promo.id,
                "description": promo.description,
                "image_url": promo.image_url,
                "target": promo.target,
                "max_count": promo.max_count,
                "active_from": promo.active_from,
                "active_until": promo.active_until,
                "mode": promo.mode,
                "created_at": promo.created_at,
                "active": promo.active,
            }
            for promo in promos
        ]

        return {
            "total_count": total_count,
            "promos": promos_dicts,
        }


    async def promo_user_get_by_id(self, promo_id: str, db: AsyncSession, user_id: str) -> dict:
        """
        Получение пользователем информации по промокоду по его id (без активации)
        GET /user/promo/{id}
        """
        promo = await db.get(Promo, promo_id)

        if not promo or not promo.active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo not found or inactive."
            )

        return {
                "id": promo.id,
                "description": promo.description,
                "image_url": promo.image_url,
                "target": promo.target,
                "max_count": promo.max_count,
                "active_from": promo.active_from,
                "active_until": promo.active_until,
                "mode": promo.mode,
                "created_at": promo.created_at,
                "active": promo.active,
            }


    async def promo_like_create(self, promo_id: str, user_id: str, db: AsyncSession) -> dict:
        """
        Создание пользователем своего лайка промокоду
        POST /user/promo/{id}/like
        """
        # Проверяем, существует ли промокод
        promo = await db.execute(select(Promo).where(Promo.id == promo_id))
        if not promo.scalars().first():
            raise HTTPException(status_code=404, detail="Promo not found.")

        # Проверяем, есть ли уже лайк от пользователя
        like_exists = await db.execute(
            select(Like).where(Like.promo_id == promo_id, Like.user_id == user_id)
        )
        if like_exists.scalars().first():
            return {"detail": "Like already exists."}

        # Создаём лайк
        like = Like(
            id=str(uuid4()),
            promo_id=promo_id,
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        db.add(like)
        await db.commit()
        return {"detail": "Like created successfully."}


    async def promo_like_delete(self, promo_id: str, user_id: str, db: AsyncSession) -> dict:
        """
        Удаление пользователем своего лайка с промокода
        DELETE /user/promo/{id}/like
        """
        # Проверяем, существует ли промокод
        promo = await db.execute(select(Promo).where(Promo.id == promo_id))
        if not promo.scalars().first():
            raise HTTPException(status_code=404, detail="Promo not found.")

        # Проверяем, есть ли лайк от пользователя
        like = await db.execute(
            select(Like).where(Like.promo_id == promo_id, Like.user_id == user_id)
        )
        like = like.scalars().first()
        if not like:
            return {"detail": "Like does not exist."}

        # Удаляем лайк
        await db.delete(like)
        await db.commit()
        return {"detail": "Like deleted successfully."}


    async def promo_comment_get_all(self, promo_id: str, db: AsyncSession) -> dict:
        """
        Получение пользователем списка комментариев к промокоду
        GET /user/promo/{id}/comments
        """
        comments = await db.execute(
            select(Comment).where(Comment.promo_id == promo_id).order_by(Comment.created_at.desc())
        )
        return [
            {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
                "user_id": comment.user_id,
            }
            for comment in comments.scalars().all()
        ]

    async def promo_comment_get_by_id(self, promo_id: str, comment_id: str, db: AsyncSession) -> dict:
        """
        Получение пользователем комментария к промокоду по его идентификатору
        GET /user/promo/{id}/comments/{comment_id}
        """
        comment = await db.get(Comment, comment_id)
        if not comment or str(comment.promo_id) != promo_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found."
            )
        return {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
            "user_id": comment.user_id,
        }

    async def promo_comment_create(self, promo_id: str, user_id: str, body: dict, db: AsyncSession) -> dict:
        """
        Создание пользователем комментария к промокоду
        POST /user/promo/{id}/comments
        """
        content = body.get("content")
        if not content or len(content) < 5 or len(content) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content length must be between 5 and 500 characters."
            )

        comment = Comment(
            id=str(uuid4()),
            promo_id=promo_id,
            user_id=user_id,
            content=content,
            created_at=datetime.utcnow()
        )
        db.add(comment)
        await db.commit()
        return {"id": comment.id, "detail": "Comment created successfully."}

    async def promo_comment_update(self, promo_id: str, comment_id: str, user_id: str, body: dict, db: AsyncSession) -> dict:
        """
        Редактирование пользователем комментария к промокоду
        PUT /user/promo/{id}/comments/{comment_id}
        """
        comment = await db.get(Comment, comment_id)
        if not comment or str(comment.promo_id) != promo_id or str(comment.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found or not authorized."
            )

        content = body.get("content")
        if not content or len(content) < 5 or len(content) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content length must be between 5 and 500 characters."
            )

        comment.content = content
        comment.updated_at = datetime.utcnow()
        await db.commit()
        return {"id": comment.id, "detail": "Comment updated successfully."}

    async def promo_comment_delete(self, promo_id: str, comment_id: str, user_id: str, db: AsyncSession) -> dict:
        """
        Удаление пользователем комментария к промокоду
        DELETE /user/promo/{id}/comments/{comment_id}
        """
        comment = await db.get(Comment, comment_id)
        if not comment or str(comment.promo_id) != promo_id or str(comment.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found or not authorized."
            )

        await db.delete(comment)
        await db.commit()
        return {"detail": "Comment deleted successfully."}

    async def promo_activate(self, promo_id: str, db: AsyncSession, redis: Redis,  user_id: str) -> dict:
        """
        Активация промокода пользователем
        POST user/promo/{id}/activate
        """
        # Проверяем существование промокода
        promo = await db.get(Promo, promo_id)
        if not promo or not promo.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Promo not available for activation."
            )

        # Проверяем соответствие таргетингу промокода
        if promo.target and not user_service.matches_targeting(user_id, promo.target, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not match promo targeting criteria."
            )

        # Запрашиваем антифрод-вердикт
        antifraud_result = await antifraud_service.check_user(user_id, promo_id, redis)
        if not antifraud_result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Antifraud service denied activation."
            )

        # Активация для COMMON промокодов
        if promo.mode == "COMMON":
            if promo.max_count <= (await db.execute(
                select(func.count()).where(PromoActivation.promo_id == promo_id)
            )).scalar():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Promo code activation limit reached."
                )

            activation = PromoActivation(
                id=str(uuid4()),
                promo_id=promo.id,
                user_id=user_id,
                activated_at=datetime.utcnow(),
            )
            db.add(activation)

        # Активация для UNIQUE промокодов
        elif promo.mode == "UNIQUE":
            if not promo.promo_unique:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No unique values available for activation."
                )

            activation_value = promo.promo_unique.pop()
            activation = PromoActivation(
                id=str(uuid4()),
                promo_id=promo.id,
                user_id=user_id,
                activation_value=activation_value,
                activated_at=datetime.utcnow(),
            )
            db.add(activation)
            promo.promo_unique = promo.promo_unique

        # Сохраняем изменения
        await db.commit()
        return {"detail": "Promo activated successfully."}

    async def promo_history(self, user_id: str, db: AsyncSession) -> dict:
        """
        Получение пользователем исторической сводки по активированным промокодам
        GET /user/promo/history
        """
        activations = await db.execute(
            select(PromoActivation)
            .where(PromoActivation.user_id == user_id)
            .order_by(PromoActivation.activated_at.desc())
        )
        return [
            {
                "promo_id": activation.promo_id,
                "activation_value": activation.activation_value,
                "activated_at": activation.activated_at,
            }
            for activation in activations.scalars().all()
        ]

    async def promo_stat(self, promo_id: str, company_id: str, db: AsyncSession) -> dict:
        """
        Получение компанией статистики по промокоду
        GET /business/promo/{id}/stat
        """
        # Проверяем существование промокода и его принадлежность компании
        promo = await db.get(Promo, promo_id)

        if not promo or str(promo.company_id) != company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo not found or not authorized."
            )

        # Запрашиваем активации промокода
        activations = await db.execute(
            select(PromoActivation.activation_value, PromoActivation.activated_at)
            .where(PromoActivation.promo_id == promo_id)
        )
        activation_list = activations.all()

        # Подсчет статистики по странам
        country_stats = {}
        for activation in activation_list:
            target_country = promo.target.get("country") if promo.target else None
            if target_country:
                country_stats[target_country] = country_stats.get(target_country, 0) + 1

        # Сортировка по коду региона
        sorted_country_stats = sorted(
            [{"region_code": country, "count": count} for country, count in country_stats.items()],
            key=lambda x: x["region_code"]
        )

        return {
            "promo_id": promo_id,
            "activation_count": len(activation_list),
            "country_summary": sorted_country_stats,
            "detail": "Statistics fetched successfully."
        }