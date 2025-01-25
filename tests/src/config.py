from datetime import timedelta

from pydantic import Field
from pydantic_settings import BaseSettings


class DBSettings(BaseSettings):
    """
    Конфигурация для настроек базы данных
    """
    name: str = Field(alias='POSTGRES_DATABASE', default='prod')
    user: str = Field(alias='POSTGRES_USERNAME', default='admin')
    password: str = Field(alias='POSTGRES_PASSWORD', default='123qwe')
    host: str = Field(alias='POSTGRES_HOST', default='localhost')
    port: int = Field(alias='POSTGRES_PORT', default=5432)

    @property
    def _base_url(self) -> str:
        """ Формирует базовый URL для подключения к базе данных """
        return f"{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def dsn(self) -> str:
        """ Формирует DSN строку для подключения к базе данных с использованием asyncpg """
        return f"postgresql+asyncpg://{self._base_url}"


class RedisSettings(BaseSettings):
    """
    Конфигурация для настроек Redis
    """
    host: str = Field(alias='REDIS_HOST', default='localhost')
    port: int = Field(alias='REDIS_PORT', default=6379)


class JWTSettings(BaseSettings):
    """
    Конфигурация для настроек JWT
    """
    secret_key: str = Field(
        alias='RANDOM_SECRET', default='7Fp0SZsBRKqo1K82pnQ2tcXV9XUfuiIJxpDcE5FofP2fL0vlZw3SOkI3YYLpIGP',
    )
    algorithm: str = Field(default='HS256')
    token_expire_time: int = Field(default=60)


class Settings(BaseSettings):
    db: DBSettings = DBSettings()
    redis: RedisSettings = RedisSettings()
    jwt: JWTSettings = JWTSettings()
    default_address: str = Field(alias='SERVER_ADDRESS', default='0.0.0.0:8080')
    default_host: str = '0.0.0.0'
    default_port: int = Field(alias='SERVER_PORT', default=8000)
    antifraud: str = Field(alias='ANTIFRAUD_ADDRESS', default='localhost:9090')



settings = Settings()
