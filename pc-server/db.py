import psycopg2
from dotenv import load_dotenv
import os
load_dotenv()

def get_guest_profile():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cur = conn.cursor()
    cur.execute("SELECT name, email, phone FROM guest_profile LIMIT 1;")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {"name": row[0], "email": row[1], "phone": row[2]}