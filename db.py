import os
import psycopg

def get_db():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Environment variable not set")
    return psycopg.connect(database_url)