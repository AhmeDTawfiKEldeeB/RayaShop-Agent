from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    status: str = Field(..., description="Status of the response, e.g. 'success' or 'error'")
    message: str = Field(..., description="Human-readable message describing the result")
    data: T | None = Field(None, description="Payload of the response")


class ErrorResponse(BaseModel):
    status: str = Field("error", description="Always 'error' for error responses")
    message: str = Field(..., description="Human-readable description of the error")
    errors: list[dict[str, Any]] | None = Field(
        None, description="Optional list of validation or field errors"
    )