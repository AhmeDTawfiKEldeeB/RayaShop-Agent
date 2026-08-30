import uvicorn
from src.config.settings import settings
from src.main import app

def main() -> None:
    uvicorn.run(
        "src.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.app.debug,
    )


if __name__ == "__main__":
    main()

