"""One MySQL connection per HTTP request; parameterized queries throughout."""
import os
from contextlib import contextmanager
import pymysql
from flask import g


def get_db():
    if "db" not in g:
        g.db = pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "project_kashi"),
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
            autocommit=True, connect_timeout=5,
        )
    return g.db


def query(sql, params=(), one=False):
    with get_db().cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone() if one else cursor.fetchall()


@contextmanager
def transaction():
    connection = get_db()
    connection.begin()
    try:
        with connection.cursor() as cursor:
            yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()
