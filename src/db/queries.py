from mysql.connector import Error, IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from .connection import getConnection
import math
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal



ROLES = {"student", "officer"}
AUDIT_RESULTS = {"tampered", "verified"}
MAX_LIMIT = 100


@contextmanager
def _cursor(dictionary: bool = False):
    """Yields (conn, cur) and always closes both. Uncommitted work is rolled back on close."""
    conn = getConnection()
    cur = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cur
    finally:
        cur.close()
        conn.close()
 
 
def _ok(details: dict | None = None) -> dict:
    return {"success": True, "msg": "OK", "details": details or {}}
 
 
def _fail(msg: str, details: dict | None = None) -> dict:
    return {"success": False, "msg": msg, "details": details or {}}
 
 
def _serialize(row: dict) -> dict:
    """Make DB values JSON-safe (dates -> ISO strings, Decimal -> float)."""
    out = {}
    for k, v in row.items():
        if isinstance(v, (date, datetime)):
            out[k] = v.isoformat()
        elif isinstance(v, Decimal):
            out[k] = float(v)
        else:
            out[k] = v
    return out
 
 
def _page(offset, limit) -> tuple[int, int]:
    try:
        offset, limit = int(offset), int(limit)
    except (TypeError, ValueError):
        raise ValueError("offset and limit must be integers.")
    if offset < 0 or limit < 1:
        raise ValueError("offset must be >= 0 and limit must be >= 1.")
    return offset, min(limit, MAX_LIMIT)



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





# Scholarships

 
def getScholarships(offset: int, limit: int) -> dict:
    """details["rows"] = list of scholarships, or None if there are none."""
    try:
        offset, limit = _page(offset, limit)
    except ValueError as e:
        return _fail(str(e))
    try:
        with _cursor(dictionary=True) as (_, cur):
            cur.execute(
                "SELECT id, name, min_education_level, min_passing_percentage, max_age, "
                "one_child_req, minority_category_req, benefit_amount, deadline "
                "FROM scholarships ORDER BY deadline ASC, id ASC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            rows = [_serialize(r) for r in cur.fetchall()]
        return _ok({"rows": rows or None})
    except Error as e:
        return _fail(str(e))
 
 
# Applications

 
def getApplications(user_id: int | None, offset: int, limit: int) -> dict:
    """
    user_id=None -> all applications (officer view); user_id=<id> -> that student's only.
    details["rows"] = list of applications, or None if there are none.
    """
    try:
        offset, limit = _page(offset, limit)
    except ValueError as e:
        return _fail(str(e))
 
    query = (
        "SELECT a.id, u.name AS user_name, s.name AS scholarship_name, a.status, "
        "a.education_level, a.passing_percentage, a.income, "
        "a.created_at AS `timestamp`, a.minority_category "
        "FROM applications a "
        "JOIN users u ON u.id = a.user_id "
        "JOIN scholarships s ON s.id = a.scholarship_id "
    )
    params: list = []
    if user_id is not None:
        query += "WHERE a.user_id = %s "
        params.append(user_id)
    query += "ORDER BY a.created_at DESC, a.id DESC LIMIT %s OFFSET %s"
    params += [limit, offset]
 
    try:
        with _cursor(dictionary=True) as (_, cur):
            cur.execute(query, tuple(params))
            rows = [_serialize(r) for r in cur.fetchall()]
        return _ok({"rows": rows or None})
    except Error as e:
        return _fail(str(e))
 
 
def searchApplications(application_id: int) -> dict:
    """
    details["row"] = the application (with user/scholarship names) plus its
    "documents" and "audit_logs" lists, or None if the application doesn't exist.
    """
    try:
        with _cursor(dictionary=True) as (_, cur):
            cur.execute(
                "SELECT a.id, a.user_id, u.name AS user_name, u.email AS user_email, "
                "a.scholarship_id, s.name AS scholarship_name, a.status, a.education_level, "
                "a.passing_percentage, a.income, a.minority_category, "
                "a.created_at AS `timestamp` "
                "FROM applications a "
                "JOIN users u ON u.id = a.user_id "
                "JOIN scholarships s ON s.id = a.scholarship_id "
                "WHERE a.id = %s LIMIT 1",
                (application_id,),
            )
            row = cur.fetchone()
            if row is None:
                return _ok({"row": None})
            row = _serialize(row)
 
            cur.execute(
                "SELECT id, type, path, created_at AS `timestamp` FROM documents "
                "WHERE application_id = %s ORDER BY id ASC",
                (application_id,),
            )
            row["documents"] = [_serialize(r) for r in cur.fetchall()]
 
            cur.execute(
                "SELECT id, document_id, result, confidence, created_at AS `timestamp` "
                "FROM audit_logs WHERE application_id = %s ORDER BY id DESC",
                (application_id,),
            )
            row["audit_logs"] = [_serialize(r) for r in cur.fetchall()]
 
        return _ok({"row": row})
    except Error as e:
        return _fail(str(e))
 
 
# Documents & audit logs (used by /verify)

 
def createDocument(type: str, user_id: int, application_id: int, path: str) -> dict:
    """
    type must be one of the document types defined in the DB (the DB rejects others).
    On success details["id"] = new document id (needed for createAuditLog).
    """
    try:
        with _cursor() as (conn, cur):
            cur.execute(
                "INSERT INTO documents (type, user_id, application_id, path) "
                "VALUES (%s, %s, %s, %s)",
                (type, user_id, application_id, path),
            )
            conn.commit()
            return _ok({"id": cur.lastrowid})
    except IntegrityError:
        return _fail("Invalid user_id or application_id.")
    except Error as e:
        return _fail(str(e))
 
 
def createAuditLog(result: str, confidence: float, document_id: int,
                   user_id: int, application_id: int) -> dict:
    """result = "tampered" | "verified". On success details["id"] = new audit log id."""
    if result not in AUDIT_RESULTS:
        return _fail("result must be 'tampered' or 'verified'.")
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return _fail("confidence must be a number.")
    if not math.isfinite(confidence):
        return _fail("confidence must be a finite number.")
 
    try:
        with _cursor() as (conn, cur):
            cur.execute(
                "INSERT INTO audit_logs (result, confidence, document_id, user_id, application_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (result, confidence, document_id, user_id, application_id),
            )
            conn.commit()
            return _ok({"id": cur.lastrowid})
    except IntegrityError:
        return _fail("Invalid document_id, user_id or application_id.")
    except Error as e:
        return _fail(str(e))
