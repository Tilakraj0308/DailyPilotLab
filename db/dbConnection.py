import psycopg2
from dotenv import load_dotenv
import os
from contextlib import contextmanager
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
    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        yield connection
    except Exception as e:
        print(f"Failed to connect: {e}")
    finally:
        if connection:
            connection.close()
