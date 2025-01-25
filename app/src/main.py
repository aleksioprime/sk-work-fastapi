import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from src.db import redis
from src.core.config import settings
from src.api import ping, company, promo, user

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения FastAPI
    """
    redis.redis = Redis(host=settings.redis.host, port=settings.redis.port)
    yield
    await redis.redis.close()


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