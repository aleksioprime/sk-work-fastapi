import jwt
import re
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from fastapi import HTTPException, status

from src.core.config import settings
from src.models.user import User


class UserService:

    async def sign_up(self, body: dict, db: AsyncSession) -> dict:
        """
        Регистрация нового пользователя
        POST /user/auth/sign-up
        """
        # Проверка обязательных полей
        required_fields = ["name", "email", "password"]
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Проверка сложности пароля
        if not self._is_password_strong(body["password"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Password must contain at least 8 characters, including one uppercase letter, "
                    "one lowercase letter, one number, and one special character."
                ),
            )

        try:
            user = User(
                email=body["email"],
                password=body["password"],
                name=body.get("name")
            )
            db.add(user)
            await db.commit()
            return {"id": user.id, "email": user.email, "name": user.name}
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists."
            )

    @staticmethod
    def _is_password_strong(password: str) -> bool:
        """
        Проверяет, соответствует ли пароль требованиям сложности.
        """
        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        return re.match(pattern, password) is not None

    async def sign_in(self, body: dict, db: AsyncSession) -> dict:
        """
        Аутентификация пользователя по e-mail и паролю и генерация токена доступа
        POST /user/auth/sign-in
        """
        # Проверка обязательных полей
        required_fields = ["email", "password"]
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )

        query = select(User).where(User.email == body["email"])
        result = await db.execute(query)
        user = result.scalars().first()

        if not user or not user.check_password(body["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        token = jwt.encode(
            {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(minutes=settings.jwt.token_expire_time)},
            settings.jwt.secret_key,
            algorithm=settings.jwt.algorithm
        )
        return {"token": token, "token_type": "bearer"}

    async def validate_token(self, token: str) -> str:
        """
        Проверка токена и извлечение идентификатора пользователя
        """
        try:
            payload = jwt.decode(token, settings.jwt.secret_key, algorithms=[settings.jwt.algorithm])
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token validation failed: 'sub' not found."
                )
            return user_id
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired."
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token."
            )

    async def profile_get(self, user_id: str, db: AsyncSession) -> dict:
        """
        Получение информации о своем профиле
        GET /user/profile
        """
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        return {"id": user.id, "email": user.email, "name": user.name, "created_at": user.created_at}

    async def profile_update(self, user_id: str, body: dict, db: AsyncSession) -> dict:
        """
        Изменение пользовательских настроек
        PATCH /user/profile
        """
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        for key, value in body.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        await db.commit()
        return {"id": user.id, "email": user.email, "name": user.name, "updated_at": user.updated_at}

    async def matches_targeting(self, user_id: str, targeting: dict, db: AsyncSession) -> bool:
        """
        Проверяет соответствие пользователя условиям таргетинга промокода
        """
        # Получаем данные пользователя (пример: из базы данных или внешнего сервиса)
        user = await self.profile_get(user_id, db)

        if not user:
            return False

        # Пример таргетинга по стране
        if "country" in targeting:
            if user.country not in targeting["country"]:
                return False

        # Пример таргетинга по возрасту
        if "age_min" in targeting or "age_max" in targeting:
            if "age_min" in targeting and user.age < targeting["age_min"]:
                return False
            if "age_max" in targeting and user.age > targeting["age_max"]:
                return False

        # Пример таргетинга по языку
        if "language" in targeting:
            if user.language not in targeting["language"]:
                return False

        # Добавьте дополнительные проверки таргетинга, если требуется
        return True