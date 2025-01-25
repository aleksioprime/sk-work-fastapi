import json
from datetime import datetime
from redis.asyncio import Redis
from fastapi import HTTPException
import httpx


class AntifraudService:
    def __init__(self, antifraud_address: str):
        self.antifraud_address = antifraud_address

    async def check_user(self, user_email: str, promo_id: str, redis: Redis) -> bool:
        """
        Проверка пользователя через антифрод-сервис с кешированием в Redis
        """
        cache_key = f"antifraud:{user_email}:{promo_id}"

        # Проверяем кеш
        cached_result = await redis.get(cache_key)
        if cached_result:
            cached_data = json.loads(cached_result)
            cache_until = datetime.strptime(cached_data["cache_until"], "%Y-%m-%dT%H:%M:%S.%f")
            if datetime.utcnow() < cache_until:
                return cached_data["ok"]

        # Формируем запрос
        url = f"{self.antifraud_address}/api/validate"
        headers = {"Content-Type": "application/json"}
        payload = {
            "user_email": user_email,
            "promo_id": promo_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Antifraud service error.")

            data = response.json()

            # Проверяем обязательные поля ответа
            if "ok" not in data:
                raise HTTPException(status_code=500, detail="Invalid response from antifraud service.")

            # Обновляем кеш
            cache_until = datetime.utcnow()
            if "cache_until" in data:
                cache_until = datetime.strptime(data["cache_until"], "%Y-%m-%dT%H:%M:%S.%f")

            cached_data = {
                "ok": data["ok"],
                "cache_until": cache_until.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            }

            # Сохраняем данные в Redis с TTL
            ttl = (cache_until - datetime.utcnow()).seconds
            await redis.set(cache_key, json.dumps(cached_data), ex=ttl)

            return data["ok"]