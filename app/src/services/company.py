import jwt
import re
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from fastapi import HTTPException, status


from src.core.config import settings
from src.models.company import Company


class CompanyService:

    async def sign_up(self, body: dict, db: AsyncSession) -> dict:
        """
        Регистрация новой компании
        POST /business/auth/sign-up
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
            company = Company(
                name=body["name"],
                email=body["email"],
                password=body["password"],
            )
            db.add(company)
            await db.commit()
            return {"id": company.id, "name": company.name}
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Company with this email already exists."
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
        Аутентификация компании по e-mail и паролю и генерация токена
        POST /business/auth/sign-in
        """
        # Проверка обязательных полей
        required_fields = ["email", "password"]
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )

        query = select(Company).where(Company.email == body["email"])
        result = await db.execute(query)
        company = result.scalars().first()

        if not company or not company.check_password(body["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        token = jwt.encode(
            {"sub": str(company.id), "exp": datetime.utcnow() + timedelta(minutes=settings.jwt.token_expire_time)},
            settings.jwt.secret_key,
            algorithm=settings.jwt.algorithm
        )
        return {"token": token, "type": "bearer"}

    async def validate_token(self, token: str) -> str:
        """
        Проверка токена и извлечение идентификатора компании
        """
        try:
            payload = jwt.decode(token, settings.jwt.secret_key, algorithms=[settings.jwt.algorithm])
            company_id = payload.get("sub")
            if not company_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token validation failed: 'sub' not found."
                )
            return company_id
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
