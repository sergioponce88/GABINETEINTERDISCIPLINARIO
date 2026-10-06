import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

DB_NAME = 'gabinete_iesp.db'

PERMISOS = {
    'Administrador': ['Dashboard General', 'Gestión de Legajos', 'Personal del Gabinete', '1. Primera Intervención', '2. Notas Médicas y Reposos', '3. Control de Alta', '4. Exámenes Periódicos y Anuales', '5. Historia Clínica Integral', '6. Examen de Baja / Egreso', '7. Informes y Análisis de Datos (Spark)', 'Panel de Usuarios', 'Visor de Auditoría'],
    'Médico/a': ['Dashboard General', 'Gestión de Legajos', '1. Primera Intervención', '2. Notas Médicas y Reposos', '3. Control de Alta', '4. Exámenes Periódicos y Anuales', '5. Historia Clínica Integral', '6. Examen de Baja / Egreso', '7. Informes y Análisis de Datos (Spark)'],
    'Guardia': ['Dashboard General', 'Gestión de Legajos', '1. Primera Intervención', '3. Control de Alta'],
    'Directivo': ['Dashboard General', 'Gestión de Legajos', '5. Historia Clínica Integral', '7. Informes y Análisis de Datos (Spark)', 'Visor de Auditoría']
}

def inicializar_seguridad():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        rol TEXT NOT NULL,
                        debe_cambiar_password INTEGER DEFAULT 1,
                        intentos_fallidos INTEGER DEFAULT 0,
                        bloqueado_hasta TEXT,
                        activo INTEGER DEFAULT 1
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS auditoria_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        username TEXT NOT NULL,
                        rol TEXT NOT NULL,
                        modulo TEXT NOT NULL,
                        accion TEXT NOT NULL,
                        detalle TEXT,
                        id_referencia TEXT,
                        hash_prev TEXT,
                        hash_registro TEXT
                    )''')
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        salt = os.urandom(16).hex()
        pass_inicial = os.environ.get("ADMIN_INITIAL_PASSWORD", "Admin2026*")
        pwd_hash = hashlib.pbkdf2_hmac('sha256', pass_inicial.encode('utf-8'), bytes.fromhex(salt), 600000).hex()
        cursor.execute("INSERT INTO usuarios (username, password_hash, salt, rol, debe_cambiar_password, activo) VALUES (?, ?, ?, ?, 1, 1)",
                       ('admin', pwd_hash, salt, 'Administrador'))
        conn.commit()
    conn.close()

def registrar_auditoria(modulo, accion, detalle, id_referencia=None):
    try:
        username = st.session_state.get('usuario', 'sistema')
        rol = st.session_state.get('rol', 'Sistema')
        hora_arg = (datetime.utcnow() - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT hash_registro FROM auditoria_logs ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        hash_prev = row[0] if row else "GENESIS"
        cadena_actual = f"{hora_arg}|{username}|{rol}|{modulo}|{accion}|{str(detalle)}|{str(id_referencia)}|{hash_prev}"
        hash_reg = hashlib.sha256(cadena_actual.encode('utf-8')).hexdigest()
        cursor.execute("INSERT INTO auditoria_logs (timestamp, username, rol, modulo, accion, detalle, id_referencia, hash_prev, hash_registro) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (hora_arg, username, rol, modulo, accion, str(detalle), str(id_referencia) if id_referencia else None, hash_prev, hash_reg))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error en auditoría: {e}")
