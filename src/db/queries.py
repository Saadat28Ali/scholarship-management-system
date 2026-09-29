from mysql.connector import Error, IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from .connection import getConnection

"""
Expected table:

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student'
);
"""


def searchUser(email: str, password: str | None, role: str) -> dict:
    """
    Login:    searchUser(email, password, role) -> details["row"] is the user, or None if no match.
    Register: searchUser(email, None, role)     -> existence check only (password not verified).
    """
    conn = cur = None
    try:
        conn = getConnection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, name, email, role, password_hash FROM users "
            "WHERE email = %s AND role = %s LIMIT 1",
            (email, role),
        )
        row = cur.fetchone()

        if row is not None and password is not None:
            if not check_password_hash(row["password_hash"], password):
                row = None

        if row is not None:
            row.pop("password_hash")

        return {"success": True, "msg": "OK", "details": {"row": row}}
    except Error as e:
        return {"success": False, "msg": str(e), "details": {}}
    finally:
        if cur: cur.close()
        if conn: conn.close()


def createUser(name: str, email: str, password: str, role: str) -> dict:
    """Insert a new user. On success, details["id"] holds the new user's id."""
    conn = cur = None
    try:
        conn = getConnection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (name, email, generate_password_hash(password), role),
        )
        conn.commit()
        return {"success": True, "msg": "OK", "details": {"id": cur.lastrowid}}
    except IntegrityError:
        if conn: conn.rollback()
        return {"success": False, "msg": "User already exists.", "details": {}}
    except Error as e:
        if conn: conn.rollback()
        return {"success": False, "msg": str(e), "details": {}}
    finally:
        if cur: cur.close()
        if conn: conn.close()