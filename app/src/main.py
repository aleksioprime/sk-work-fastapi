import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from src.db import redis
from src.db.postgres import engine, Base
from src.core.config import settings
from src.api import ping, company, promo, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения FastAPI
    """

    redis.redis = Redis(host=settings.redis.host, port=settings.redis.port)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    await redis.redis.close()
    await engine.dispose()


# Инициализация FastAPI-приложения
app = FastAPI(
    lifespan=lifespan,
    title='Название приложения',
    description='Описание приложения',
    docs_url="/api/openapi",
)

app.include_router(ping.router, prefix="/api", tags=["ping"])
app.include_router(company.router, prefix="/api", tags=["company"])
app.include_router(user.router, prefix="/api", tags=["user"])
app.include_router(promo.router, prefix="/api", tags=["promo"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.default_host,
        port=settings.default_port,
        reload=True,
    )