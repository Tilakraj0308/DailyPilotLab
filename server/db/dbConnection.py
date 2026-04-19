import psycopg2
from dotenv import load_dotenv
import os
from contextlib import contextmanager
from psycopg2 import extras
# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

@contextmanager
def get_connection():
    """Open a DB connection. Only connection failures are logged as 'Failed to connect'."""
    connection = None
    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
    except Exception as e:
        print(f"Failed to connect: {e}")
        raise
    try:
        yield connection
    finally:
        if connection is not None:
            connection.close()

@contextmanager
def get_dict_cursor():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
