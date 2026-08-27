import time
from datetime import UTC, datetime

from fastapi import APIRouter

from src.api.schemas.health import API_VERSION, HealthResponse, HealthStatus

router = APIRouter(
    prefix="/api/v1",
    tags=["health"])

_START_TIME = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="success",
        message="Service is healthy",
        data=HealthStatus(
            status="ok",
            version=API_VERSION,
            uptime_seconds=time.monotonic() - _START_TIME,
            timestamp=datetime.now(UTC),
        ),
    )