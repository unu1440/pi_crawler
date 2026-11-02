"""MySQL 연결."""

import os
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor


@contextmanager
def open_connection():
    """DB 연결. 정상 종료 시 커밋, 오류 시 되돌림."""
    connection = pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        init_command="SET time_zone = '+00:00'",  # 시각을 UTC로 통일
        connect_timeout=5,
    )

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()