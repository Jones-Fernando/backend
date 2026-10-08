"""Camada de conexão do WEPAY.

MySQL é o banco oficial. SQLite existe somente para testes automatizados locais.
Os modelos usam '?' como placeholder; esta camada adapta para '%s' no MySQL.
"""

from contextlib import contextmanager
import os
import sqlite3
from pathlib import Path

from config import Config

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:  # pragma: no cover - dependência é obrigatória em runtime
    mysql = None
    MySQLError = Exception
else:
    mysql = mysql.connector

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "database" / "wepay.sql"
TEST_SCHEMA_FILE = BASE_DIR / "database" / "test_schema.sql"


def adapt_query(query: str) -> str:
    """Converte placeholders portáveis para o dialeto usado pelo driver."""
    if Config.DB_DRIVER == "mysql":
        return query.replace("?", "%s")
    return query


def _sqlite_path() -> str:
    path = Config.TEST_DB_PATH
    if path == ":memory:":
        return path
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return str(candidate)


def _connect_mysql(database: str | None = None):
    if mysql is None:
        raise RuntimeError(
            "mysql-connector-python nao esta instalado. Execute: pip install -r requirements.txt"
        )

    params = {
        "host": Config.DB_HOST,
        "port": Config.DB_PORT,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
    }
    if database:
        params["database"] = database
    return mysql.connect(**params)


def _ensure_mysql_database():
    connection = _connect_mysql()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        connection.commit()
        cursor.close()
    finally:
        connection.close()


def _connect_sqlite():
    connection = sqlite3.connect(_sqlite_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _ensure_schema():
    schema_file = SCHEMA_FILE if Config.DB_DRIVER == "mysql" else TEST_SCHEMA_FILE
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema nao encontrado: {schema_file}")

    if Config.DB_DRIVER == "mysql":
        _ensure_mysql_database()
        connection = _connect_mysql(Config.DB_NAME)
        try:
            cursor = connection.cursor()
            sql = schema_file.read_text(encoding="utf-8-sig")
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            connection.commit()
            cursor.close()
        finally:
            connection.close()
    else:
        connection = _connect_sqlite()
        try:
            sql = schema_file.read_text(encoding="utf-8-sig")
            connection.executescript(sql)
            connection.commit()
        finally:
            connection.close()


_ensure_schema()


@contextmanager
def get_connection_context():
    connection = _connect_mysql(Config.DB_NAME) if Config.DB_DRIVER == "mysql" else _connect_sqlite()
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_connection():
    return _connect_mysql(Config.DB_NAME) if Config.DB_DRIVER == "mysql" else _connect_sqlite()


def normalize_row(row, description=None):
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return dict(row)
    if description:
        return {column[0]: value for column, value in zip(description, row)}
    if isinstance(row, dict):
        return row
    return dict(row)


def fetch_one(cursor):
    row = cursor.fetchone()
    description = cursor.description
    return normalize_row(row, description)


def fetch_all(cursor):
    rows = cursor.fetchall()
    description = cursor.description
    return [normalize_row(row, description) for row in rows]


class CursorAdapter:
    """Pequeno adaptador para manter a mesma API nos drivers."""
    def __init__(self, cursor):
        self._cursor = cursor

    @staticmethod
    def _params(params):
        if params is None:
            return None
        from decimal import Decimal
        if isinstance(params, (list, tuple)):
            return tuple(str(item) if isinstance(item, Decimal) else item for item in params)
        return params

    def execute(self, operation, params=None):
        if params is None:
            return self._cursor.execute(adapt_query(operation))
        return self._cursor.execute(adapt_query(operation), self._params(params))

    def executemany(self, operation, seq_of_params):
        return self._cursor.executemany(
            adapt_query(operation),
            [self._params(params) for params in seq_of_params],
        )

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        self._cursor.close()


def cursor_for(connection):
    """Cria cursor com comportamento uniforme nos drivers."""
    if Config.DB_DRIVER == "mysql":
        return CursorAdapter(connection.cursor(dictionary=True))
    return CursorAdapter(connection.cursor())
