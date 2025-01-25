import logging
from collections.abc import MutableMapping
from typing import Any
import pytest
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import settings

logging.basicConfig(
    level=logging.INFO,  # Уровень логирования
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Формат логов
    handlers=[logging.StreamHandler()]  # Логирование в консоль
)

# Создайте движок SQLAlchemy
engine = create_async_engine(settings.db.dsn, future=True, echo=False)

# Создайте фабрику сессий
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def pytest_tavern_beta_before_every_request(request_args: MutableMapping):
    message = f"Request: {request_args['method']} {request_args['url']}"

    params = request_args.get('params', None)
    if params:
        message += f"\nQuery parameters: {params}"

    message += f"\nRequest body: {request_args.get('json', '<no body>')}"

    logging.info(message)

def pytest_tavern_beta_after_every_response(expected: Any, response: Any) -> None:
    logging.info(f"Response: {response.status_code} {response.text}")


def pytest_tavern_beta_before_every_test_run(test_dict):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(clear_database_func())

async def clear_database_func():
    async with async_session() as db_session:
        tables = ["promos", "companies", "users"]
        for table in tables:
            await db_session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
        await db_session.commit()