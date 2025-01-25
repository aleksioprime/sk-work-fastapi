from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from pydantic import BaseModel


router = APIRouter()


class PingResponse(BaseModel):
    message: str = "PROOOOOOOOOOOOOOOOOD"
    status: str = "ok"


@router.get("/ping", status_code=status.HTTP_200_OK)
async def ping():
    """
    Эндпоинт для проверки работы web-сервера
    """
    return PingResponse()