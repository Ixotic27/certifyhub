from app.config import settings
import psycopg2

def main():
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    cur.execute("select tablename from pg_tables where schemaname='public'")
    tables = cur.fetchall()
    print('public tables:', tables)
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
