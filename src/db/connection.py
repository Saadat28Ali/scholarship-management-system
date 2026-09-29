import os
import mysql.connector
from mysql.connector import pooling, Error
import os
import mysql.connector

# Env var names match your dashboard: DATABASE, HOST, PASSWORD, PORT, USERNAME
def getConnection():
    """Open and return a new DB connection. Caller must close it."""
    return mysql.connector.connect(
        host=os.environ["HOST"],
        port=int(os.environ["PORT"]),
        user=os.environ["USERNAME"],
        password=os.environ["PASSWORD"],
        database=os.environ["DATABASE"],
    )