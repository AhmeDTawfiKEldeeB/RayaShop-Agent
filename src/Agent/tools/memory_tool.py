import json
import logging
import psycopg
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from src.config.settings import settings

logger = logging.getLogger(__name__)


def _get_connection():
    """Create a new PostgreSQL connection using active settings."""
    return psycopg.connect(
        host=settings.postgres.host,
        port=settings.postgres.port,
        dbname=settings.postgres.database,
        user=settings.postgres.user,
        password=settings.postgres.password,
    )


def ensure_memory_table():
    """Ensure the user_memories table exists in PostgreSQL."""
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_memories (
                        id SERIAL PRIMARY KEY,
                        thread_id VARCHAR(255) NOT NULL,
                        key VARCHAR(255) NOT NULL,
                        value TEXT NOT NULL,
                        UNIQUE(thread_id, key)
                    );
                """)
                conn.commit()
        logger.info("user_memories table checked/created successfully.")
    except Exception as exc:
        logger.exception("Failed to initialize user_memories table: %s", exc)
        raise


@tool
def save_user_preference(key: str, value: str, config: RunnableConfig) -> str:
    """Save a user preference, brand affinity, budget constraint, or personal interest for this thread.
    
    Args:
        key: The preference category (e.g. 'preferred_brand', 'max_budget', 'color').
        value: The preference value (e.g. 'Fresh', '20000', 'Black').
    """
    thread_id = config.get("configurable", {}).get("thread_id", "default_thread")
    try:
        ensure_memory_table()
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_memories (thread_id, key, value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (thread_id, key)
                    DO UPDATE SET value = EXCLUDED.value;
                """, (thread_id, key, value))
                conn.commit()
        logger.info("Memory saved for thread '%s': %s = %s", thread_id, key, value)
        return f"Successfully saved memory: {key} = {value} for thread {thread_id}."
    except Exception as exc:
        logger.exception("Error saving memory")
        return f"Error saving preference: {exc}"


@tool
def get_user_preferences(config: RunnableConfig) -> str:
    """Retrieve all stored user preferences, constraints, or interests saved in this thread."""
    thread_id = config.get("configurable", {}).get("thread_id", "default_thread")
    try:
        ensure_memory_table()
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT key, value FROM user_memories WHERE thread_id = %s;
                """, (thread_id,))
                rows = cur.fetchall()
        if not rows:
            return f"No preferences stored yet for thread {thread_id}."
        
        prefs = {row[0]: row[1] for row in rows}
        return json.dumps(prefs, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.exception("Error retrieving memory")
        return f"Error retrieving preferences: {exc}"
