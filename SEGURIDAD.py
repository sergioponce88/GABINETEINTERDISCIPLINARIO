import streamlit as st
import sqlite3
import hashlib
import hmac
import secrets
import json
import os
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    TZ_LOCAL = ZoneInfo('America/Argentina/Tucuman')
except Exception:
    TZ_LOCAL = timezone(timedelta(hours=-3))

DB_NAME = 'gabinete_iesp.db'
PBKDF2_ITERACIONES = 600_000
MAX_INTENTOS = 5
BLOQUEO_MINUTOS = 15
TIMEOUT_SESION_MIN = 30
PASSWORD_MIN_LARGO = 10
MAX_PDF_BYTES = 10 * 1024 * 1024

ROL_ADMIN = 'Administrador'
ROL_MEDICO = 'Profesional Médico'
ROL_GUARDIA = 'Guardia / Recepción'
ROL_DIRECTIVO = 'Directivo / Auditor'
ROLES = [ROL_ADMIN, ROL_MEDICO, ROL_GUARDIA, ROL_DIRECTIVO]

PERMISOS = {
    'Administrador': ['Dashboard General', 'Gestión de Legajos', 'Personal del Gabinete', '1. Primera Intervención', '2. Notas Médicas y Reposos', '3. Control de Alta', '4. Exámenes Periódicos y Anuales', '5. Historia Clínica Integral', '6. Examen de Baja / Egreso', '7. Informes y Análisis de Datos (Spark)', '8. Gestión de Usuarios', '9. Auditoría del Sistema'],
    'Profesional Médico': ['Dashboard General', 'Gestión de Legajos', '1. Primera Intervención', '2. Notas Médicas y Reposos', '3. Control de Alta', '4. Exámenes Periódicos y Anuales', '5. Historia Clínica Integral', '6. Examen de Baja / Egreso', '7. Informes y Análisis de Datos (Spark)'],
    'Guardia / Recepción': ['Dashboard General', 'Gestión de Legajos', '1. Primera Intervención', '3. Control de Alta'],
    'Directivo / Auditor': ['Dashboard General', 'Gestión de Legajos', '5. Historia Clínica Integral', '7. Informes y Análisis de Datos (Spark)', '9. Auditoría del Sistema']
}

MENU_PERMISOS = {
    'Dashboard General': 'ver_dashboard',
    'Gestión de Legajos': 'ver_legajos_basico',
    'Personal del Gabinete': 'ver_personal',
    '1. Primera Intervención': 'primera_intervencion',
    '2. Notas Médicas y Reposos': 'notas_medicas',
    '3. Control de Alta': 'control_alta',
    '4. Exámenes Periódicos y Anuales': 'examenes_periodicos',
    '5. Historia Clínica Integral': 'historia_clinica',
    '6. Examen de Baja / Egreso': 'examen_baja',
    '7. Informes y Análisis de Datos (Spark)': 'informes',
    '8. Gestión de Usuarios': 'gestion_usuarios',
    '9. Auditoría del Sistema': 'ver_auditoria',
}

_PERMISOS_MATRIZ = {
    'ver_dashboard': {ROL_ADMIN, ROL_MEDICO, ROL_DIRECTIVO},
    'ver_legajos_basico': set(ROLES),
    'ver_legajos_completo': {ROL_ADMIN, ROL_MEDICO, ROL_DIRECTIVO},
    'exportar_legajos': {ROL_ADMIN, ROL_MEDICO, ROL_DIRECTIVO},
    'alta_cadete': {ROL_ADMIN, ROL_MEDICO},
    'sincronizar_excel': {ROL_ADMIN},
    'ver_personal': {ROL_ADMIN, ROL_MEDICO, ROL_DIRECTIVO},
    'gestionar_personal': {ROL_ADMIN},
    'primera_intervencion': {ROL_ADMIN, ROL_MEDICO, ROL_GUARDIA},
    'notas_medicas': {ROL_ADMIN, ROL_MEDICO},
    'control_alta': {ROL_ADMIN, ROL_MEDICO},
    'examenes_periodicos': {ROL_ADMIN, ROL_MEDICO},
    'historia_clinica': {ROL_ADMIN, ROL_MEDICO, ROL_DIRECTIVO},
    'examen_baja': {ROL_ADMIN, ROL_MEDICO},
    'informes': {ROL_ADMIN, ROL_MEDICO, ROL_DIRECTIVO},
    'gestion_usuarios': {ROL_ADMIN},
    'ver_auditoria': {ROL_ADMIN, ROL_DIRECTIVO},
}

def ahora_local():
    return datetime.now(TZ_LOCAL).replace(tzinfo=None) if 'TZ_LOCAL' in globals() else datetime.now()

def _ts():
    return ahora_local().strftime('%Y-%m-%d %H:%M:%S')

def _conn():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def nombre_seguro(nombre, unico=True):
    base = os.path.basename(str(nombre).replace('\\', '/'))
    raiz, ext = os.path.splitext(base)
    raiz = re.sub(r'[^A-Za-z0-9._-]+', '_', raiz).strip('._') or 'archivo'
    ext = re.sub(r'[^A-Za-z0-9.]+', '', ext)[:10] or '.pdf'
    sufijo = f'_{secrets.token_hex(4)}' if unico else ''
    return f'{raiz[:100]}{sufijo}{ext.lower()}'

def validar_pdf(archivo):
    if archivo is None:
        return None
    datos = archivo.getbuffer()
    if len(datos) > MAX_PDF_BYTES:
        st.error(f'«{archivo.name}» supera el límite.')
        return None
    return archivo

def hash_password(password, iteraciones=PBKDF2_ITERACIONES):
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iteraciones)
    return f'pbkdf2_sha256${iteraciones}${salt.hex()}${dk.hex()}'

def verify_password(password, almacenado):
    try:
        alg, it, salt_hex, hash_hex = almacenado.split('$')
        if alg != 'pbkdf2_sha256':
            return False
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt_hex), int(it))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False

def validar_politica_password(password, username=''):
    if len(password) < PASSWORD_MIN_LARGO:
        return f'La contraseña debe tener al menos {PASSWORD_MIN_LARGO} caracteres.'
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        return 'La contraseña debe combinar letras y números.'
    return None

def generar_password_temporal():
    while True:
        pw = secrets.token_urlsafe(9)
        if validar_politica_password(pw) is None:
            return pw

def init_seguridad(db_name):
    global DB_NAME
    DB_NAME = db_name
    conn = _conn()
    cur = conn.cursor()
    roles_sql = ', '.join(f"'{r}'" for r in ROLES)
    cur.execute(f'''
      CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nombre_completo TEXT NOT NULL,
        rol TEXT NOT NULL CHECK (rol IN ({roles_sql})),
        leg
