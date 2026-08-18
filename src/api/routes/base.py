from fastapi import APIRouter

from src.api.schemas.base import StandardResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["base"])


@router.get("/", response_model=StandardResponse[dict])
async def root() -> StandardResponse[dict]:
    return StandardResponse(
        status="success",
        message="Welcome to the RayaShop Agent API",
        data={"service": "rayashop-agent"},
    )