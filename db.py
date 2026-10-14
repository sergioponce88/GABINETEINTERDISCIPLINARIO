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


_INS_DOC = re.compile(r'INSERT\s+INTO\s+legajo_documentos\s*\(([^)]*)\)(\s*VALUES\s*\()([^)]*)\)', re.I)
_COL_CONTENIDO = {'ok': False}


def _con_pdf(cur, sql, params):
    """Los módulos viejos guardan el PDF en disco (temporal en Streamlit Cloud) y la ruta en
    legajo_documentos. Acá se agrega también el contenido a la base para que no se pierda."""
    m = _INS_DOC.search(sql)
    if not m or not params or 'contenido' in m.group(1):
        return sql, params
    cols = [c.strip() for c in m.group(1).split(',')]
    if 'archivo_nombre' not in cols:
        return sql, params
    try:
        with open(params[cols.index('archivo_nombre')], 'rb') as fh:
            datos = fh.read()
    except Exception:
        return sql, params
    if not _COL_CONTENIDO['ok']:
        cur.execute('ALTER TABLE legajo_documentos ADD COLUMN IF NOT EXISTS contenido BYTEA')
        _COL_CONTENIDO['ok'] = True
    nuevo = f'INSERT INTO legajo_documentos ({m.group(1)}, contenido){m.group(2)}{m.group(3)}, ?)'
    return sql.replace(m.group(0), nuevo, 1), params + (datos,)


class _Cursor:
    def __init__(self, cur):
        self._c = cur

    def execute(self, sql, params=None):
        if sql.strip().upper().startswith('PRAGMA'):
            return self
        params = tuple(params) if params else None
        sql, params = _con_pdf(self._c, sql, params)
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


def _diagnostico(e):
    """Muestra el motivo real del fallo (sin la contraseña) y detiene la app."""
    url = _url() or ''
    m = re.match(r'postgres(?:ql)?://([^:@/]+)(?::[^@]*)?@([^:/]+)(?::(\d+))?', url)
    usuario, host, puerto = (m.groups() if m else ('?', '?', '?'))
    msg = str(e).replace(url, '***')
    st.error('🔴 No se pudo conectar a Supabase.')
    st.code(f'Usuario: {usuario}\nHost: {host}\nPuerto: {puerto}\n\nMotivo: {msg.strip()}')
    pistas = {
        'password authentication failed': 'Contraseña incorrecta. Si tiene ? @ # / : escríbalos como %3F %40 %23 %2F %3A.',
        'Tenant or user not found': 'Usuario/host no coinciden: copie de nuevo la URL desde Supabase → Connect → Session pooler.',
        'could not translate host name': 'Host mal escrito o URL incompleta.',
        'timeout': 'Tiempo agotado: verifique host y puerto (5432 session pooler).',
        'invalid dsn': 'La URL no tiene formato válido (revise comillas y que esté en una sola línea).',
    }
    for k, v in pistas.items():
        if k.lower() in msg.lower():
            st.info(v)
    st.stop()


def _nueva_pg(autocommit=True):
    try:
        raw = psycopg2.connect(_url(), connect_timeout=10, sslmode='require')
    except psycopg2.Error as e:
        _diagnostico(e)
    raw.autocommit = autocommit
    return raw


@st.cache_resource(show_spinner=False)
def _pg_compartida():
    return {'raw': _nueva_pg()}


def pdf_bytes(fila):
    """Contenido de un documento: primero desde la base, si no desde el disco."""
    datos = fila.get('contenido') if hasattr(fila, 'get') else None
    if datos is not None and not (isinstance(datos, float)):
        return bytes(datos)
    ruta = str(fila.get('archivo_nombre') or '')
    if ruta and os.path.exists(ruta):
        with open(ruta, 'rb') as fh:
            return fh.read()
    return None


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
