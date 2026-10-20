from mysql.connector import Error, IntegrityError
import hmac
import math
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

from .connection import getConnection
from ..util.template_response import TemplateResponse;
from ..util.pw_hash import PwHash;

ROLES = {"student", "officer"}
AUDIT_RESULTS = {"tampered", "verified"}

#! for create application
APPLICATION_STATUSES = {"submitted", "processing", "verified"}
EDUCATION_LEVELS = {"10th", "12th", "graduation", "postgraduation"}
MINORITY_CATEGORIES = {"Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Parsi"}


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


# Users

def createUser(name: str, email: str, password: str, role: str) -> TemplateResponse:
    """Insert a new user. On success, details["user_id"] holds the new user's id."""
    conn = cur = None
    try:
        conn = getConnection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (name, email, password, role),  # 'password' is the hash from the frontend
        )
        conn.commit()
        return TemplateResponse(True, "OK", {"user_id": cur.lastrowid})
    except IntegrityError:
        if conn:
            conn.rollback()
        return TemplateResponse(False, "User already exists.", {})
    except Error as e:
        if conn:
            conn.rollback()
        return TemplateResponse(False, str(e), {})
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def searchUser(email: str, password: str | None, role: str) -> TemplateResponse:
    """
    Login:    searchUser(email, password, role) -> details["row"] is the user, or None if no match.
    Register: searchUser(email, None, role)     -> existence check only (password not verified).
    """
    try:
        with _cursor(dictionary=True) as (_, cur):
            cur.execute(
                "SELECT user_id, name, email, role, password_hash, is_admin FROM users "
                "WHERE email = %s AND role = %s LIMIT 1",
                (email, role),
            )
            row = cur.fetchone()

        if row is not None and password is not None:
            stored = str(row["password_hash"]).encode()
            supplied = str(password).encode()
            if not hmac.compare_digest(stored, supplied):
                row = None

        if row is not None:
            row.pop("password_hash")

        return TemplateResponse(True, "OK", {"row": row})
    except Error as e:
        return TemplateResponse(False, str(e), {})


# Scholarships

def getScholarships(offset: int, limit: int) -> TemplateResponse:
    """details["rows"] = list of scholarships, or None if there are none."""
    try:
        with _cursor(dictionary=True) as (_, cur):
            cur.execute(
                "SELECT scholarship_id, name, min_education_level, min_passing_percentage, max_age, "
                "one_child_req, minority_category_req, benefit_amount, deadline "
                "FROM scholarships ORDER BY deadline ASC, scholarship_id ASC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            rows = [_serialize(r) for r in cur.fetchall()]
        return TemplateResponse(True, "OK", {"rows": rows or None})
    except Error as e:
        return TemplateResponse(False, str(e), {})


# Applications

def getApplications(user_id: int | None, offset: int, limit: int) -> TemplateResponse:
    """
    user_id=None -> all applications (officer view); user_id=<id> -> that student's only.
    details["rows"] = list of applications, or None if there are none.
    """
    query = (
        "SELECT a.application_id, u.name AS user_name, s.name AS scholarship_name, a.status, "
        "a.education_level, a.passing_percentage, a.income, "
        "a.timestamp AS `timestamp`, a.minority_category "
        "FROM applications a "
        "JOIN users u ON u.user_id = a.user_id "
        "JOIN scholarships s ON s.scholarship_id = a.scholarship_id "
    )
    params: list = []
    if user_id is not None:
        query += "WHERE a.user_id = %s "
        params.append(user_id)
    query += "ORDER BY a.timestamp DESC, a.application_id DESC LIMIT %s OFFSET %s"
    params += [limit, offset]

    try:
        with _cursor(dictionary=True) as (_, cur):
            cur.execute(query, tuple(params))
            rows = [_serialize(r) for r in cur.fetchall()]
        return TemplateResponse(True, "OK", {"rows": rows or None})
    except Error as e:
        return TemplateResponse(False, str(e), {})


def searchApplications(application_id: int) -> TemplateResponse:
    """
    details["row"] = the application (with user/scholarship names) plus its
    "documents" and "audit_logs" lists, or None if the application doesn't exist.
    """
    try:
        with _cursor(dictionary=True) as (_, cur):
            cur.execute(
                "SELECT a.application_id, a.user_id, u.name AS user_name, u.email AS user_email, "
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
                return TemplateResponse(True, "OK", {"row": None})
            row = _serialize(row)

            cur.execute(
                "SELECT application_id, type, path, created_at AS `timestamp` FROM documents "
                "WHERE application_id = %s ORDER BY id ASC",
                (application_id,),
            )
            row["documents"] = [_serialize(r) for r in cur.fetchall()]

            cur.execute(
                "SELECT application_id, document_id, result, confidence, created_at AS `timestamp` "
                "FROM audit_logs WHERE application_id = %s ORDER BY id DESC",
                (application_id,),
            )
            row["audit_logs"] = [_serialize(r) for r in cur.fetchall()]

        return TemplateResponse(True, "OK", {"row": row})
    except Error as e:
        return TemplateResponse(False, str(e), {})





# Documents & audit logs (used by /verify)

def createDocument(type: str, user_id: int, application_id: int, path: str) -> TemplateResponse:
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
            return TemplateResponse(True, "OK", {"document_id": cur.lastrowid})
    except IntegrityError:
        return TemplateResponse(False, "Invalid user_id or application_id.", {})
    except Error as e:
        return TemplateResponse(False, str(e), {})


def createAuditLog(result: str, confidence: float, document_id: int,
                   user_id: int, application_id: int) -> TemplateResponse:
    """result = "tampered" | "verified". On success details["id"] = new audit log id."""
    if result not in AUDIT_RESULTS:
        return TemplateResponse(False, "result must be 'tampered' or 'verified'.", {})
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return TemplateResponse(False, "confidence must be a number.", {})
    if not math.isfinite(confidence):
        return TemplateResponse(False, "confidence must be a finite number.", {})

    try:
        with _cursor() as (conn, cur):
            cur.execute(
                "INSERT INTO audit_logs (result, confidence, document_id, user_id, application_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (result, confidence, document_id, user_id, application_id),
            )
            conn.commit()
            return TemplateResponse(True, "OK", {"id": cur.lastrowid})
    except IntegrityError:
        return TemplateResponse(False, "Invalid document_id, user_id or application_id.", {})
    except Error as e:
        return TemplateResponse(False, str(e), {})


# this i have done on basis of days, that how old is the application, i will change this further according to the db or other changes..


def getDashboard(days: int) -> TemplateResponse:
    """Summary stats for the last `days` days (1-365)."""
    try:
        days = int(days)
    except (TypeError, ValueError):
        return TemplateResponse(False, "days must be an integer.", {})
    if not 1 <= days <= 365:
        return TemplateResponse(False, "days must be between 1 and 365.", {})

    try:
        with _cursor(dictionary=True) as (_, cur):
            cur.execute(
                "SELECT status, COUNT(*) AS count FROM applications "
                "WHERE created_at >= NOW() - INTERVAL %s DAY GROUP BY status",
                (days,),
            )
            by_status = {r["status"]: r["count"] for r in cur.fetchall()}

            cur.execute(
                "SELECT DATE(created_at) AS day, COUNT(*) AS count FROM applications "
                "WHERE created_at >= NOW() - INTERVAL %s DAY GROUP BY day ORDER BY day",
                (days,),
            )
            per_day = [_serialize(r) for r in cur.fetchall()]

            cur.execute(
                "SELECT result, COUNT(*) AS count, AVG(confidence) AS avg_confidence "
                "FROM audit_logs WHERE created_at >= NOW() - INTERVAL %s DAY GROUP BY result",
                (days,),
            )
            audit = {r["result"]: _serialize(r) for r in cur.fetchall()}

            cur.execute(
                "SELECT COUNT(*) AS count FROM documents "
                "WHERE created_at >= NOW() - INTERVAL %s DAY",
                (days,),
            )
            documents = cur.fetchone()["count"]

        return TemplateResponse(True, "OK", {
            "days": days,
            "applications": {
                "total": sum(by_status.values()),
                "by_status": by_status,
                "per_day": per_day,
            },
            "audit": {
                "verified": audit.get("verified", {}).get("count", 0),
                "tampered": audit.get("tampered", {}).get("count", 0),
                "avg_confidence": {k: v["avg_confidence"] for k, v in audit.items()},
            },
            "documents": documents,
        })
    except Error as e:
        return TemplateResponse(False, str(e), {})

def createScholarship(
    name: str,
    benefit_amount: int,
    deadline: str,
    min_education_level: str | None = None,
    min_passing_percentage: int | None = None,
    max_age: int | None = None,
    max_income: int | None = None,
    one_child_req: bool | None = None,
    minority_category_req: str | None = None,
) -> TemplateResponse:
    """Insert a new scholarship. On success, details["id"] holds the new scholarship's id."""
    query = (
        "INSERT INTO scholarships ("
        "name, benefit_amount, deadline, min_education_level, "
        "min_passing_percentage, max_age, max_income, "
        "one_child_req, minority_category_req"
        ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    params = (
        name,
        benefit_amount,
        deadline,
        min_education_level,
        min_passing_percentage,
        max_age,
        max_income,
        one_child_req,
        minority_category_req,
    )

    try:
        with _cursor() as (conn, cur):
            cur.execute(query, params)
            conn.commit()
            return TemplateResponse(True, "OK", {"id": cur.lastrowid})
    except IntegrityError as e:
        return TemplateResponse(False, f"Integrity error: {e}", {})
    except Error as e:
        return TemplateResponse(False, str(e), {})





def createApplication(
    user_id: int,
    scholarship_id: int,
    status: str,
    education_level: str,
    passing_percentage: int,
    income: int,
    timestamp: str,
    minority_category: str
) -> TemplateResponse:
    # 1. Input validations
    if status not in APPLICATION_STATUSES:
        return TemplateResponse(
            False,
            f"Invalid status. Must be one of: {', '.join(sorted(APPLICATION_STATUSES))}.",
            {}
        )

    if education_level not in EDUCATION_LEVELS:
        return TemplateResponse(
            False,
            f"Invalid education level. Must be one of: {', '.join(sorted(EDUCATION_LEVELS))}.",
            {}
        )

    try:
        passing_percentage = int(passing_percentage)
        income = int(income)
    except (TypeError, ValueError):
        return TemplateResponse(False, "passing_percentage and income must be integers.", {})

    if passing_percentage < 0:
        return TemplateResponse(False, "passing_percentage cannot be less than 0.", {})

    if income < 0:
        return TemplateResponse(False, "income cannot be less than 0.", {})

    try:
        datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return TemplateResponse(False, "timestamp must be in 'YYYY-MM-DD HH:MM:SS' format.", {})

    if minority_category not in MINORITY_CATEGORIES:
        return TemplateResponse(
            False,
            f"Invalid minority category. Must be one of: {', '.join(sorted(MINORITY_CATEGORIES))}.",
            {}
        )

  
    query = (
        "INSERT INTO applications ("
        "user_id, scholarship_id, status, education_level, "
        "passing_percentage, income, created_at, minority_category"
        ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    )
    params = (
        user_id,
        scholarship_id,
        status,
        education_level,
        passing_percentage,
        income,
        timestamp,
        minority_category,
    )

    try:
        with _cursor() as (conn, cur):
            cur.execute(query, params)
            conn.commit()
            return TemplateResponse(
                True,
                "OK",
                {"application_id": cur.lastrowid}
            )
    except IntegrityError as e:
        return TemplateResponse(False, f"Integrity error: {e}", {})
    except Error as e:
        return TemplateResponse(False, str(e), {})
