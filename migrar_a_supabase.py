"""Uso local (una sola vez):  python migrar_a_supabase.py gabinete_iesp.db "postgresql://..."
Copia todas las tablas de un respaldo SQLite a Supabase (las tablas ya deben existir:
basta con abrir la app una vez con SUPABASE_DB_URL configurado)."""
import sqlite3
import sys

import psycopg2
from psycopg2.extras import execute_values

TABLAS = ['cadetes', 'personal_gabinete', 'usuarios', 'primera_intervencion', 'notas_medicas',
          'legajo_documentos', 'examenes_periodicos', 'examen_baja', 'auditoria_logs']

src = sqlite3.connect(sys.argv[1])
dst = psycopg2.connect(sys.argv[2], sslmode='require')
cur = dst.cursor()
for t in TABLAS:
    try:
        rs = src.execute(f'SELECT * FROM {t}')
    except sqlite3.Error:
        continue
    cols = [d[0] for d in rs.description]
    filas = rs.fetchall()
    cur.execute('SELECT column_name FROM information_schema.columns WHERE table_name = %s', (t,))
    destino = {r[0] for r in cur.fetchall()}
    for c in set(cols) - destino:  # columnas agregadas con ALTER en la app vieja
        cur.execute(f'ALTER TABLE {t} ADD COLUMN IF NOT EXISTS {c} TEXT')
    if filas:
        execute_values(cur, f'INSERT INTO {t} ({", ".join(cols)}) VALUES %s ON CONFLICT DO NOTHING', filas)
    if 'id' in cols:  # realinear el SERIAL para que los nuevos INSERT no choquen
        cur.execute(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE(MAX(id), 1)) FROM {t}")
    print(f'{t}: {len(filas)} filas')
dst.commit()
