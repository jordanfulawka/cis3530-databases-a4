import os
import psycopg
from flask import g

def get_db():
    if "db" not in g:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL not set")
        g.db = psycopg.connect(database_url)
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()