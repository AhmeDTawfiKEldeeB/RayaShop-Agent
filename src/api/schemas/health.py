from datetime import datetime

from pydantic import BaseModel, Field

from src.api.schemas.base import StandardResponse

API_VERSION = "v1"


class HealthStatus(BaseModel):
    status: str = Field(..., description="Overall service status, e.g. 'ok'")
    version: str = Field(..., description="Current API version")
    uptime_seconds: float = Field(..., description="Time elapsed since service started, in seconds")
    timestamp: datetime = Field(..., description="Time of the health check")


class HealthResponse(StandardResponse[HealthStatus]):
    data: HealthStatus