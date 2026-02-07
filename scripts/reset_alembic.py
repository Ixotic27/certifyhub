import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
import psycopg2

def reset_alembic():
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
        conn.commit()
        print("Alembic version table dropped")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    reset_alembic()
