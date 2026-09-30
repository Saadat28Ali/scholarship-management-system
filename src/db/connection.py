from os import getenv;
from mysql.connector import pooling, Error
import mysql.connector
from dotenv import load_dotenv

load_dotenv();

# Environment variables must be DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME
def getConnection():
    """Open and return a new DB connection. Caller must close it."""
    return mysql.connector.connect(
        host=getenv("DB_HOST"),
        port=getenv("DB_PORT"),
        user=getenv("DB_USERNAME"),
        password=getenv("DB_PASSWORD"),
        database=getenv("DB_NAME"),
    )
