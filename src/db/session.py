from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings


def build_database_url() -> str:
    postgres = settings.postgres
    return (
        f"postgresql+psycopg://{postgres.user}:{postgres.password}"
        f"@{postgres.host}:{postgres.port}/{postgres.database}"
    )


engine = create_engine(
    build_database_url(),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()