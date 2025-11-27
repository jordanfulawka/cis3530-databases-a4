import os
import sys
import psycopg
from werkzeug.security import generate_password_hash


if len(sys.argv) != 2:
    print("Usage: python script.py <role>")
    sys.exit(1)


database_url = os.environ.get("DATABASE_URL")

username = sys.argv[1]
password = "password"

pw_hash = generate_password_hash(password)

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO app_user (username, password_hash, role) VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING",
            (username, pw_hash, sys.argv[1])
        )
        conn.commit()
print("User created (or already exists).")
