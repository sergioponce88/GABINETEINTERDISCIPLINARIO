"""Capa de conexión única: Supabase (PostgreSQL) si hay credenciales, SQLite local si no.

Mantiene la API de sqlite3 que usa la app (placeholders '?', conn.execute(),
cursor.execute(...).fetchone(), pd.read_sql_query) para no reescribir las consultas.
"""
import os
import re
import sqlite3
import warnings
from contextlib import contextmanager

import streamlit as st

try:
    import psycopg2
    import psycopg2.extras
    _PG_ERRORS = (psycopg2.Error,)
    _PG_INTEGRITY = (psycopg2.IntegrityError,)
except ImportError:  # sin psycopg2 → solo SQLite
    psycopg2 = None
    _PG_ERRORS = ()
    _PG_INTEGRITY = ()

warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy.*')

Error = (sqlite3.Error,) + _PG_ERRORS
IntegrityError = (sqlite3.IntegrityError,) + _PG_INTEGRITY


def _url():
    try:
        return st.secrets.get('SUPABASE_DB_URL') or os.environ.get('SUPABASE_DB_URL')
    except Exception:
        return os.environ.get('SUPABASE_DB_URL')


USA_PG = bool(_url()) and psycopg2 is not None

# --- Traducción mínima de dialecto SQLite → PostgreSQL ----------------------
_DDL = [
    (re.compile(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', re.I), 'SERIAL PRIMARY KEY'),
    (re.compile(r'DEFAULT\s+"([^"]*)"', re.I), r"DEFAULT '\1'"),
    (re.compile(r'ADD\s+COLUMN\s+(?!IF\s+NOT\s+EXISTS)', re.I), 'ADD COLUMN IF NOT EXISTS '),
]


def _traducir(sql, con_params):
    for pat, rep in _DDL:
        sql = pat.sub(rep, sql)
    if con_params:
        sql = sql.replace('%', '%%').replace('?', '%s')
    return sql


class _Cursor:
    def __init__(self, cur):
        self._c = cur

    def execute(self, sql, params=None):
        if sql.strip().upper().startswith('PRAGMA'):
            return self
        params = tuple(params) if params else None
        self._c.execute(_traducir(sql, bool(params)), params)
        return self  # permite cur.execute(...).fetchone() como en sqlite3

    def executemany(self, sql, seq):
        self._c.executemany(_traducir(sql, True), [tuple(p) for p in seq])
        return self

    def __getattr__(self, n):  # fetchone, fetchall, description, rowcount, close…
        return getattr(self._c, n)

    def __iter__(self):
        return iter(self._c)


class _Conn:
    """Conexión compartida (cacheada); close() es no-op para no cortarla entre reruns."""

    def __init__(self, raw):
        self.raw = raw
        self.row_factory = None  # si se asigna sqlite3.Row → filas accesibles por nombre

    def cursor(self):
        if self.row_factory is not None:
            return _Cursor(self.raw.cursor(cursor_factory=psycopg2.extras.DictCursor))
        return _Cursor(self.raw.cursor())

    def execute(self, sql, params=None):
        return self.cursor().execute(sql, params)

    def commit(self):
        if not self.raw.autocommit:
            self.raw.commit()

    def rollback(self):
        if not self.raw.autocommit:
            self.raw.rollback()

    def close(self):
        pass


def _nueva_pg(autocommit=True):
    raw = psycopg2.connect(_url(), connect_timeout=10, sslmode='require')
    raw.autocommit = autocommit
    return raw


@st.cache_resource(show_spinner=False)
def _pg_compartida():
    return {'raw': _nueva_pg()}


def conectar(db_name=None, timeout=15):
    """Reemplazo directo de sqlite3.connect(DB_NAME)."""
    if not USA_PG:
        return sqlite3.connect(db_name or 'gabinete_iesp.db', timeout=timeout)
    box = _pg_compartida()
    raw = box['raw']
    if raw.closed:
        box['raw'] = raw = _nueva_pg()
    else:
        try:
            raw.cursor().execute('SELECT 1')
        except Exception:
            box['raw'] = raw = _nueva_pg()
    return _Conn(raw)


@contextmanager
def transaccion(db_name=None):
    """Bloque atómico: todo se guarda o nada (para cargas masivas)."""
    if USA_PG:
        raw = _nueva_pg(autocommit=False)
        try:
            yield _Cursor(raw.cursor())
            raw.commit()
        except Exception:
            raw.rollback()
            raise
        finally:
            raw.close()
    else:
        conn = sqlite3.connect(db_name or 'gabinete_iesp.db', timeout=15)
        try:
            yield conn.cursor()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
