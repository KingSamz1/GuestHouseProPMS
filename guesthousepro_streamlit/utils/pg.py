"""
PostgreSQL helper functions for GuesthousePro.
Import these instead of calling conn.execute() directly.

Usage:
    from utils.pg import fetchall, fetchone, execute, lastrowid
    with get_conn() as conn:
        rows = fetchall(conn, "SELECT * FROM units WHERE account_id = %s", (account_id,))
        row  = fetchone(conn, "SELECT * FROM accounts WHERE id = %s", (aid,))
        execute(conn, "UPDATE units SET status = %s WHERE id = %s", (status, uid))
        new_id = lastrowid(conn, "INSERT INTO guests (...) VALUES (...) RETURNING id", (...))
"""


def fetchall(conn, query, params=None):
    with conn.cursor() as c:
        c.execute(query, params)
        return [dict(r) for r in c.fetchall()]


def fetchone(conn, query, params=None):
    with conn.cursor() as c:
        c.execute(query, params)
        row = c.fetchone()
        return dict(row) if row else None


def execute(conn, query, params=None):
    with conn.cursor() as c:
        c.execute(query, params)


def lastrowid(conn, query, params=None):
    """Run an INSERT ... RETURNING id and return the new id."""
    with conn.cursor() as c:
        c.execute(query, params)
        row = c.fetchone()
        return row["id"] if row else None


def scalar(conn, query, params=None):
    """Return the first column of the first row as a plain value."""
    with conn.cursor() as c:
        c.execute(query, params)
        row = c.fetchone()
        if row is None:
            return None
        return list(dict(row).values())[0]
