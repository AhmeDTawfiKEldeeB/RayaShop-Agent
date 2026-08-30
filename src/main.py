import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.Agent.checkpointer import close_checkpointer, get_checkpointer
from src.api.routes.chat import router as chat_router
from src.api.routes.health import router as health_router
from src.api.routes.products import router as products_router
from src.api.routes.threads import router as threads_router
from src.config.settings import settings

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables if dropped
    try:
        from src.db.session import engine
        from src.db.models.base import Base
        import src.db.models.product
        import src.db.models.product_image
        Base.metadata.create_all(bind=engine)
        logging.getLogger(__name__).info("Database tables verified/created successfully.")
    except Exception as exc:
        logging.getLogger(__name__).warning("Database table creation skipped or failed: %s", exc)

    get_checkpointer()
    try:
        from src.Agent.tools.retrieval_tool import _get_embedder
        _get_embedder().embed_text("warmup")
        logging.getLogger(__name__).info("Embedder model loaded and warmed up successfully.")

    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("Embedder warmup failed: %s", exc)

    try:
        from src.Agent.shopping_agent import get_shopping_agent
        get_shopping_agent()
        logging.getLogger(__name__).info("Shopping agent graph compiled and ready.")
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("Shopping agent warmup failed: %s", exc)
        
    yield
    close_checkpointer()


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.app.name,
    version="1.0.0",
    description="AI-powered shopping assistant for RayaShop",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.responses import FileResponse

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(products_router)
app.include_router(threads_router)

@app.get("/chat")
async def chat_page():
    if os.path.exists("frontend/dist/chat.html"):
        return FileResponse("frontend/dist/chat.html")
    if os.path.exists("frontend/public/chat.html"):
        return FileResponse("frontend/public/chat.html")
    return FileResponse("frontend/chat.html")

static_dir = "frontend/dist" if os.path.exists("frontend/dist") else "frontend"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

