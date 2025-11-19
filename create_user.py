import os
import psycopg
from werkzeug.security import generate_password_hash

database_url = os.environ.get("DATABASE_URL")

username = "admin"
password = "password"

pw_hash = generate_password_hash(password)

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO app_user (username, password_hash, role) VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING",
            (username, pw_hash, "admin")
        )
        conn.commit()
print("User created (or already exists).")
