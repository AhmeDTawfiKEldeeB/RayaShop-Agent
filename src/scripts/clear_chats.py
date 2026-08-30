import sys
import psycopg

sys.path.insert(0, '.')
from src.config.settings import settings

def clear_all_chats():
    conn_info = f"postgresql://{settings.postgres.user}:{settings.postgres.password}@{settings.postgres.host}:{settings.postgres.port}/{settings.postgres.database}"
    try:
        with psycopg.connect(conn_info) as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE checkpoints, checkpoint_blobs, checkpoint_writes, user_memories CASCADE;")
                conn.commit()
        print("All chat histories and memories cleared successfully!")
    except Exception as exc:
        print("Error clearing chat histories:", exc)

if __name__ == "__main__":
    clear_all_chats()
