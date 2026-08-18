import uvicorn
from fastapi import FastAPI

from src.api.routes.base import router as base_router
from src.api.routes.health import router as health_router
from src.config.settings import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(base_router)
app.include_router(health_router)


def main() -> None:
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
