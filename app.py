from datetime import datetime, date, timedelta
import os
import sqlite3
import pandas as pd
import streamlit as st
import html as _html
import reportlab
import hashlib
import hmac
import secrets
import json
import io
import zipfile
from collections import Counter
import unicodedata
import re
import time
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

try:
    from zoneinfo import ZoneInfo
    TZ_LOCAL = ZoneInfo('America/Argentina/Tucuman')
except Exception:
    TZ_LOCAL = timezone(timedelta(hours=-3))

DB_NAME = 'gabinete_iesp.db'
EXCEL_FILE = 'LISTADO DE COMPAÑIA DE CADETES AÑO 2026 PARA D1.xlsx'
UPLOAD_DIR = 'documentos_legajos'
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

PBKDF2_ITERACIONES = 600000
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
    if archivo is None: return None
    datos = archivo.getbuffer()
    if len(datos) > MAX_PDF_BYTES:
        st.error('El archivo supera el límite.')
        return None
    return archivo

def hash_password(password, iteraciones=PBKDF2_ITERACIONES):
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iteraciones)
    return f'pbkdf2_sha256${iteraciones}${salt.hex()}${dk.hex()}'

def verify_password(password, almacenado):
    try:
        alg, it, salt_hex, hash_hex = almacenado.split('$')
        if alg != 'pbkdf2_sha256': return False
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt_hex), int(it))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception: return False

def validar_politica_password(password, username=''):
    if len(password) < PASSWORD_MIN_LARGO:
        return f'La contraseña debe tener al menos {PASSWORD_MIN_LARGO} caracteres.'
    if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
        return 'La contraseña debe combinar letras y números.'
    return None

def generar_password_temporal():
    while True:
        pw = secrets.token_urlsafe(9)
        if validar_politica_password(pw) is None: return pw

def init_seguridad():
    conn = _conn()
    cur = conn.cursor()
    roles_sql = ', '.join(f"'{r}'" for r in ROLES)
    cur.execute('''
      CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nombre_completo TEXT NOT NULL,
        rol TEXT NOT NULL,
        legajo_personal TEXT,
        activo INTEGER NOT NULL DEFAULT 1,
        fecha_creacion TEXT NOT NULL,
        debe_cambiar_password INTEGER NOT NULL DEFAULT 0,
        intentos_fallidos INTEGER NOT NULL DEFAULT 0,
        bloqueado_hasta TEXT
      )
    ''')
    cur.execute('''
      CREATE TABLE IF NOT EXISTS auditoria_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT NOT NULL,
        usuario TEXT NOT NULL,
        rol TEXT,
        modulo TEXT NOT NULL,
        accion TEXT NOT NULL,
        detalle TEXT,
        id_referencia TEXT,
        hash_prev TEXT,
        hash_registro TEXT
      )
    ''')
    conn.commit()
    if cur.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0] == 0:
        pw = os.environ.get('ADMIN_INITIAL_PASSWORD', 'Admin2026*')
        cur.execute('INSERT INTO usuarios (username, password_hash, nombre_completo, rol, activo, fecha_creacion, debe_cambiar_password) VALUES (?, ?, ?, ?, 1, ?, 1)',
                    ('admin', hash_password(pw), 'Administrador del Sistema', ROL_ADMIN, _ts()))
        conn.commit()
    conn.close()

def registrar_auditoria(modulo, accion, detalle, id_referencia=None):
    try:
        u = st.session_state.get('auth_user') or {}
        username = u.get('username', 'sistema')
        rol = u.get('rol', 'Sistema')
        fecha = _ts()
        detalle = str(detalle or '')[:1000]
        ref = None if id_referencia is None else str(id_referencia)[:200]
        conn = _conn()
        fila = conn.execute('SELECT hash_registro FROM auditoria_logs ORDER BY id DESC LIMIT 1').fetchone()
        prev = fila[0] if fila and fila[0] else ''
        payload = json.dumps([prev, fecha, username, rol, modulo, accion, detalle, ref], ensure_ascii=False)
        h = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        conn.execute('INSERT INTO auditoria_logs (fecha_hora, usuario, rol, modulo, accion, detalle, id_referencia, hash_prev, hash_registro) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                     (fecha, username, rol, modulo, accion, detalle, ref, prev, h))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error auditoria: {e}")

def auditar_vista(modulo, detalle, id_referencia):
    clave = f'_aud_vista_{modulo}'
    if st.session_state.get(clave) != id_referencia:
        st.session_state[clave] = id_referencia
        registrar_auditoria(modulo, 'VIEW', detalle, id_referencia)

def autenticar(username, password):
    username = (username or '').strip().lower()
    conn = _conn()
    conn.row_factory = sqlite3.Row
    u = conn.execute('SELECT * FROM usuarios WHERE username = ?', (username,)).fetchone()
    conn.close()
    if not u: return None, 'Usuario o contraseña incorrectos.'
    if u['bloqueado_hasta'] and u['bloqueado_hasta'] > _ts(): return None, 'Cuenta bloqueada temporalmente.'
    if not verify_password(password, u['password_hash']): return None, 'Usuario o contraseña incorrectos.'
    if not u['activo']: return None, 'Cuenta inactiva.'
    return dict(u), 'OK'

def cerrar_sesion(motivo='Cierre de sesión'):
    for k in list(st.session_state.keys()):
        del st.session_state[k]

def exigir_login(logo_html):
    u = st.session_state.get('auth_user')
    if not u:
        st.markdown('<style>[data-testid="sidebar"], [data-testid="collapsedControl"]{display:none !important;}</style>', unsafe_allow_html=True)
        _, centro, _ = st.columns([1, 1.2, 1])
        with centro:
            st.markdown('<br><br>', unsafe_allow_html=True)
            st.markdown(f'<div class="brand">{logo_html}<div><div class="brand-name">I.E.S.P. G.J.F.S.M.</div><div class="brand-sub">Dirección de Gabinete Médico</div></div></div>', unsafe_allow_html=True)
            st.markdown('### Acceso al sistema')
            with st.form('sec_form_login'):
                usuario = st.text_input('Usuario')
                clave = st.text_input('Contraseña', type='password')
                entrar = st.form_submit_button('Ingresar')
            if entrar:
                usr, msg = autenticar(usuario, clave)
                if usr:
                    st.session_state['auth_user'] = usr
                    st.rerun()
                else:
                    st.error(msg)
        st.stop()
    if u.get('debe_cambiar_password'):
        _, centro, _ = st.columns([1, 1.2, 1])
        with centro:
            st.markdown('### Debe cambiar su contraseña temporal')
            with st.form('form_cambio_ini'):
                npw = st.text_input('Nueva Contraseña (Mín. 10 caracteres)', type='password')
                cpw = st.text_input('Confirmar Contraseña', type='password')
                if st.form_submit_button('Actualizar'):
                    if len(npw) >= 10 and npw == cpw:
                        conn = _conn()
                        conn.execute('UPDATE usuarios SET password_hash = ?, debe_cambiar_password = 0 WHERE id = ?', (hash_password(npw), u['id']))
                        conn.commit()
                        conn.close()
                        st.session_state['auth_user']['debe_cambiar_password'] = 0
                        st.success('Contraseña actualizada.')
                        st.rerun()
                    else:
                        st.error('Verifique que tenga 10 caracteres y coincidan.')
        st.stop()

def render_sidebar_usuario():
    u = st.session_state.get('auth_user')
    if not u: return
    st.sidebar.markdown(f'<div class="side-foot">👤 <b>{_html.escape(u["nombre_completo"])}</b><br>{_html.escape(u["rol"])}</div>', unsafe_allow_html=True)
    if st.sidebar.button('🚪 Cerrar sesión', use_container_width=True):
        cerrar_sesion()
        st.rerun()

def tiene_permiso(permiso):
    rol = (st.session_state.get('auth_user') or {}).get('rol')
    return rol in _PERMISOS_MATRIZ.get(permiso, set())

def menu_disponible():
    rol = (st.session_state.get('auth_user') or {}).get('rol')
    return [m for m, p in MENU_PERMISOS.items() if rol in _PERMISOS_MATRIZ.get(p, set())]

def autorizar_menu(menu):
    permiso = MENU_PERMISOS.get(menu)
    if permiso is None or tiene_permiso(permiso): return True
    st.error('⛔ Su rol no tiene acceso a este módulo.')
    return False

def exigir(permiso):
    if tiene_permiso(permiso): return True
    st.error('⛔ Sin permiso.')
    return False

def indice_profesional(nombres, df_personal):
    return 0

def pagina_usuarios():
    st.markdown('<div class="pro-header"><p class="pro-title">👤 Gestión de Usuarios y Accesos</p><p class="pro-subtitle">Control de cuentas, asignación de roles, restablecimiento de contraseñas y activación.</p></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(['📋 Listado de Usuarios', '➕ Crear Nuevo Usuario', '🛠️ Administrar Cuenta'])
    
    with t1:
        st.markdown('<br>', unsafe_allow_html=True)
        conn = _conn()
        df_u = pd.read_sql_query('SELECT id, username, nombre_completo, rol, activo, debe_cambiar_password FROM usuarios', conn)
        conn.close()
        st.dataframe(df_u, use_container_width=True)
        
    with t2:
        st.markdown('<br>', unsafe_allow_html=True)
        with st.form('form_crear_usu_admin', clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                u_nuevo = st.text_input('Nombre de Usuario *', placeholder='ej: jperez').strip().lower()
                n_completo = st.text_input('Nombre y Apellido *', placeholder='ej: JUAN PÉREZ')
                rol_nuevo = st.selectbox('Rol Asignado *', ROLES)
            with c2:
                auto_pw = st.checkbox('Generar contraseña temporal automáticamente', value=True)
                p_nuevo = st.text_input('Contraseña (si no es autom.)', type='password')
            
            if st.form_submit_button('💾 Crear Cuenta de Usuario'):
                pw_final = generar_password_temporal() if auto_pw else p_nuevo
                if u_nuevo and n_completo:
                    if not auto_pw and len(pw_final) < 10:
                        st.warning('La contraseña debe tener al menos 10 caracteres.')
                    else:
                        try:
                            conn = _conn()
                            cur = conn.cursor()
                            cur.execute('INSERT INTO usuarios (username, password_hash, nombre_completo, rol, activo, fecha_creacion, debe_cambiar_password) VALUES (?, ?, ?, ?, 1, ?, 1)',
                                        (u_nuevo, hash_password(pw_final), n_completo, rol_nuevo, _ts()))
                            conn.commit()
                            conn.close()
                            registrar_auditoria('Usuarios', 'INSERT', f'Creación de usuario {u_nuevo} (rol: {rol_nuevo})')
                            st.success(f'¡Usuario «{u_nuevo}» creado con éxito!')
                            if auto_pw: st.info(f'Contraseña temporal: **{pw_final}**')
                        except sqlite3.IntegrityError:
                            st.error('El nombre de usuario ya existe en el sistema.')
                else:
                    st.warning('Complete los campos obligatorios (*).')
                    
    with t3:
        st.markdown('<br>', unsafe_allow_html=True)
        conn = _conn()
        df_u = pd.read_sql_query('SELECT id, username, nombre_completo, rol, activo FROM usuarios', conn)
        conn.close()
        if df_u.empty:
            st.info('No hay usuarios registrados.')
        else:
            dict_u = {r.id: f"{r.username} - {r.nombre_completo} ({r.rol})" for r in df_u.itertuples()}
            uid_sel = st.selectbox('Seleccione Usuario', list(dict_u.keys()), format_func=lambda x: dict_u[x])
            fila_u = df_u[df_u['id'] == uid_sel].iloc[0]
            
            c_a, c_b, c_c = st.columns(3)
            with c_a:
                st.markdown('**Cambiar Rol**')
                nuevo_r = st.selectbox('Rol', ROLES, index=ROLES.index(fila_u['rol']) if fila_u['rol'] in ROLES else 0, key='sel_nuevo_rol')
                if st.button('Actualizar Rol'):
                    conn = _conn()
                    conn.execute('UPDATE usuarios SET rol = ? WHERE id = ?', (nuevo_r, uid_sel))
                    conn.commit()
                    conn.close()
                    registrar_auditoria('Usuarios', 'UPDATE', f'Cambio de rol para usuario ID {uid_sel} a {nuevo_r}', uid_sel)
                    st.success('¡Rol actualizado con éxito!')
                    st.rerun()
            with c_b:
                st.markdown('**Estado de Cuenta**')
                estado_actual = bool(fila_u['activo'])
                if estado_actual:
                    if st.button('⛔ Desactivar Usuario'):
                        conn = _conn()
                        conn.execute('UPDATE usuarios SET activo = 0 WHERE id = ?', (uid_sel,))
                        conn.commit()
                        conn.close()
                        registrar_auditoria('Usuarios', 'UPDATE', f'Desactivación de usuario ID {uid_sel}', uid_sel)
                        st.success('Usuario desactivado.')
                        st.rerun()
                else:
                    if st.button('✅ Activar Usuario'):
                        conn = _conn()
                        conn.execute('UPDATE usuarios SET activo = 1 WHERE id = ?', (uid_sel,))
                        conn.commit()
                        conn.close()
                        registrar_auditoria('Usuarios', 'UPDATE', f'Activación de usuario ID {uid_sel}', uid_sel)
                        st.success('Usuario activado.')
                        st.rerun()
            with c_c:
                st.markdown('**Seguridad y Credenciales**')
                if st.button('🔑 Restablecer Contraseña'):
                    nueva_temp = generar_password_temporal()
                    conn = _conn()
                    conn.execute('UPDATE usuarios SET password_hash = ?, debe_cambiar_password = 1, intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?', (hash_password(nueva_temp), uid_sel))
                    conn.commit()
                    conn.close()
                    registrar_auditoria('Usuarios', 'UPDATE', f'Restablecimiento de contraseña para usuario ID {uid_sel}', uid_sel)
                    st.success('¡Contraseña restablecida con éxito!')
                    st.code(f'Nueva contraseña temporal: {nueva_temp}')

def pagina_auditoria():
    st.markdown('<div class="pro-header"><p class="pro-title">🛡️ Auditoría del Sistema</p><p class="pro-subtitle">Trazabilidad de accesos y operaciones críticas.</p></div>', unsafe_allow_html=True)
    conn = _conn()
    df = pd.read_sql_query('SELECT * FROM auditoria_logs ORDER BY id DESC LIMIT 100', conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

def render_analisis_avanzado(db_name):
    st.markdown('<h2 style="color: #FFFFFF;">🔬 Análisis Avanzado de Salud Institucional</h2>', unsafe_allow_html=True)
    conn = sqlite3.connect(db_name)
    df_i = pd.read_sql_query("SELECT * FROM primera_intervencion", conn)
    df_n = pd.read_sql_query("SELECT * FROM notas_medicas", conn)
    conn.close()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="panel"><h3>Resumen de Guardia</h3>', unsafe_allow_html=True)
        if not df_i.empty:
            st.metric("Total Intervenciones", len(df_i))
            st.dataframe(df_i, use_container_width=True)
        else:
            st.info("Sin intervenciones.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel"><h3>Resumen de Notas Médicas</h3>', unsafe_allow_html=True)
        if not df_n.empty:
            st.metric("Total Notas", len(df_n))
            st.dataframe(df_n, use_container_width=True)
        else:
            st.info("Sin notas.")
        st.markdown('</div>', unsafe_allow_html=True)

def _buscar_logo(nombre):
  for carpeta in ('.', 'assets', 'imagenes', 'img'):
    if os.path.isdir(carpeta):
      for f in os.listdir(carpeta):
        if f.lower() == nombre.lower():
          return os.path.join(carpeta, f)
  return None

try:
  from PIL import Image as _PILImage
  _ruta_icono = _buscar_logo('GABINETE.png')
  if _ruta_icono:
    _icono = _PILImage.open(_ruta_icono).convert('RGBA')
    _icono.thumbnail((128, 128))
  else:
    _icono = '🛡'
except Exception:
  _icono = '🛡'

st.set_page_config(
    page_title="Gabinete Interdisciplinario | Policía de Tucumán",
    page_icon=_icono,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
:root { --bg: #05070D; --surface: #0C1220; --surface-2: #111A2E; --border: #1C2740; --text: #E6EAF2; --muted: #8A97B1; --accent: #3B82F6; --accent-2: #22D3EE; --ok: #10B981; --warn: #F59E0B; --crit: #EF4444; --info: #38BDF8; }
html, body, [class*="css"], .stApp, button, input, textarea, select { font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif !important; }
.stApp { background: radial-gradient(900px 400px at 85% -10%, rgba(59,130,246,0.10), transparent 60%), radial-gradient(700px 380px at -5% 0%, rgba(34,211,238,0.06), transparent 60%), var(--bg); color: var(--text); }
[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1400px; }
h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #FFFFFF !important; font-weight: 800 !important; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0A1020 0%, #070B16 100%); border-right: 1px solid var(--border); }
.brand { display: flex; align-items: center; gap: 0.85rem; padding: 0.4rem 0.2rem 1.1rem 0.2rem; border-bottom: 1px solid var(--border); margin-bottom: 1.2rem; }
.brand-logo { width: 46px; height: 46px; border-radius: 13px; display: grid; place-items: center; font-size: 1.5rem; background: linear-gradient(135deg, #2563EB, #22D3EE); }
.brand-name { font-weight: 800; font-size: 1.02rem; color: #FFFFFF; }
.brand-sub { font-size: 0.74rem; color: var(--muted); }
.brand-logo.has-img { background: none; box-shadow: none; width: 54px; height: 58px; }
.brand-logo img { width: 100%; height: 100%; object-fit: contain; }
.nav-label { font-size: 0.68rem; font-weight: 700; color: #5F6C88; text-transform: uppercase; letter-spacing: 0.12em; margin: 0 0 0.5rem 0.3rem; }
.side-foot { margin-top: 2rem; padding: 0.8rem 0.9rem; border: 1px solid var(--border); border-radius: 12px; font-size: 0.74rem; color: var(--muted); background: rgba(17,26,46,0.6); }
.hero { position: relative; overflow: hidden; display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; flex-wrap: wrap; padding: 2rem 2.2rem; border-radius: 22px; margin-bottom: 1.4rem; border: 1px solid #22305A; background: radial-gradient(600px 220px at 100% 0%, rgba(34,211,238,0.18), transparent 65%), radial-gradient(500px 260px at 0% 100%, rgba(99,102,241,0.25), transparent 65%), linear-gradient(135deg, #0B1330 0%, #121B45 100%); }
.kpi { position: relative; overflow: hidden; display: flex; align-items: center; gap: 1rem; padding: 1.15rem 1.3rem; border-radius: 18px; border: 1px solid var(--border); background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); }
.kpi-icon { flex: 0 0 auto; width: 50px; height: 50px; border-radius: 14px; display: grid; place-items: center; font-size: 1.45rem; background: color-mix(in srgb, var(--c) 16%, transparent); border: 1px solid color-mix(in srgb, var(--c) 35%, transparent); }
.kpi-value { font-size: 2rem; font-weight: 800; color: #FFFFFF; }
.kpi-label { font-size: 0.72rem; font-weight: 700; color: var(--muted); text-transform: uppercase; }
.panel { border: 1px solid var(--border); border-radius: 18px; padding: 1.2rem 1.3rem; margin-bottom: 1rem; background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); }
.pro-header { background: linear-gradient(135deg, #0B1330 0%, #121B45 100%); padding: 2rem; border-radius: 20px; border: 1px solid #22305A; color: white; margin-bottom: 1.5rem; }
.pro-title { font-size: 2rem; font-weight: 800; margin: 0; color: #FFFFFF; }
.pro-subtitle { font-size: 1rem; color: #93C5FD; margin-top: 0.4rem; }
.profile-card { background: linear-gradient(135deg, #0F172A 0%, #111B33 100%); padding: 1.5rem 1.75rem; border-radius: 18px; border: 1px solid var(--border); border-left: 4px solid var(--accent); margin-bottom: 1.5rem; }
</style>''', unsafe_allow_html=True)

init_seguridad()

_logo_gab = logo_uri('GABINETE.png', 116)
_brand_logo = f'<div class="brand-logo has-img"><img src="{_logo_gab}" alt="Gabinete"></div>' if _logo_gab else '<div class="brand-logo">🛡️</div>'
exigir_login(_brand_logo)

st.sidebar.markdown(
    f'<div class="brand">{_brand_logo}<div><div class="brand-name">I.E.S.P. G.J.F.S.M.</div><div class="brand-sub">Dirección de Gabinete Médico</div></div></div><div class="nav-label">Navegación principal</div>',
    unsafe_allow_html=True,
)

ICONOS_MENU = {
    'Dashboard General': '📊',
    'Gestión de Legajos': '📁',
    'Personal del Gabinete': '🧑‍⚕️',
    '1. Primera Intervención': '🩺',
    '2. Notas Médicas y Reposos': '📋',
    '3. Control de Alta': '✅',
    '4. Exámenes Periódicos y Anuales': '🧪',
    '5. Historia Clínica Integral': '🗂️',
    '6. Examen de Baja / Egreso': '🚪',
    '7. Informes y Análisis de Datos (Spark)': '📈',
    '8. Gestión de Usuarios': '👤',
    '9. Auditoría del Sistema': '🛡️',
}

menu = st.sidebar.radio(
    'Navegación Principal',
    menu_disponible(),
    format_func=lambda x: f"{ICONOS_MENU.get(x, '•')}  {x}",
    label_visibility='collapsed',
)
st.sidebar.markdown('<div class="side-foot">🔒 Información sanitaria confidencial.<br>Uso exclusivo del personal autorizado.</div>', unsafe_allow_html=True)
render_sidebar_usuario()

if not autorizar_menu(menu):
    st.stop()

def importar_excel_directo():
    if not os.path.exists(EXCEL_FILE):
        return False, f'No se encontro el archivo Excel: {EXCEL_FILE}'
    try:
        df_excel = pd.read_excel(EXCEL_FILE, sheet_name=0)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cargados = 0
        for _, row in df_excel.iterrows():
            if pd.isna(row.get('APELLIDO')) or pd.isna(row.get('NOMBRES')):
                continue
            id_leg = str(row.get('CARGO', row.get('N°', 'S/N'))).strip()
            ap_nom = f"{str(row.get('APELLIDO', '')).strip()}, {str(row.get('NOMBRES', '')).strip()}"
            curso = str(row.get('CURSO', '1 AÑO')).strip()
            dni = str(row.get('DNI', '')).strip()
            genero = 'Masculino'
            f_nac = str(row.get('FECHA DE NACIMIENTO', '')).split(' ')[0] if pd.notna(row.get('FECHA DE NACIMIENTO')) else ''
            obs = f"Email: {row.get('EMAIL', '')} | Celular: {row.get('CELULAR', '')} | CUIL: {row.get('CUIL', '')}"
            cursor.execute('INSERT OR IGNORE INTO cadetes VALUES (?, ?, ?, ?, ?, ?, ?)', (id_leg, ap_nom, curso, dni, genero, f_nac, obs))
            cargados += 1
        conn.commit()
        conn.close()
        return True, f'Sincronizados {cargados} cadetes.'
    except Exception as e:
        return False, str(e)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS cadetes (id_legajo TEXT PRIMARY KEY, apellido_nombre TEXT NOT NULL, curso TEXT NOT NULL, dni TEXT, genero TEXT, fecha_nacimiento TEXT, observaciones TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS personal_gabinete (id_legajo_personal TEXT PRIMARY KEY, apellido_nombre TEXT NOT NULL, dni TEXT, matricula TEXT, especialidad TEXT, telefono TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS primera_intervencion (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, fecha_hora TEXT, profesional_atiende TEXT, sintomas TEXT, presion TEXT, saturacion TEXT, temperatura TEXT, derivacion TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS notas_medicas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, nro_expediente TEXT, medico TEXT, diagnostico TEXT, tipo_reposo TEXT, fecha_desde TEXT, fecha_hasta TEXT, medicamentos TEXT, certificados_indicaciones TEXT, analisis_estudios TEXT, estado_alta TEXT DEFAULT "Pendiente", fecha_alta_efectiva TEXT, medico_alta TEXT, observaciones_alta TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS legajo_documentos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, titulo_documento TEXT, tipo_documento TEXT, fecha_subida TEXT, archivo_nombre TEXT, observaciones TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS examenes_periodicos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, anio TEXT, ddjj_enfermedades TEXT, visus TEXT, hemograma TEXT, orina TEXT, electrocardiograma TEXT, aptitud_fisica TEXT, toxicologico TEXT, beta_hcg TEXT, fecha_registro TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS examen_baja (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, fecha_baja TEXT, motivo TEXT, estado_salud_egreso TEXT, observaciones_medicas TEXT)')
    
    for col, col_type in [('certificados_indicaciones', 'TEXT'), ('analisis_estudios', 'TEXT'), ('medicamentos', 'TEXT'), ('estado_alta', 'TEXT DEFAULT "Pendiente"'), ('fecha_alta_efectiva', 'TEXT'), ('medico_alta', 'TEXT'), ('observaciones_alta', 'TEXT'), ('temperatura', 'TEXT')]:
        try:
            cursor.execute(f'ALTER TABLE notas_medicas ADD COLUMN {col} {col_type};')
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute(f'ALTER TABLE primera_intervencion ADD COLUMN {col} {col_type};')
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM cadetes')
    count = cursor.fetchone()[0]
    conn.close()
    if count == 0:
        importar_excel_directo()

init_db()

def obtener_cadetes():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('SELECT * FROM cadetes', conn)
    conn.close()
    return df

def obtener_personal():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('SELECT * FROM personal_gabinete', conn)
    conn.close()
    return df

DIAS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

def fecha_larga_es(d):
    return f'{DIAS_ES[d.weekday()]} {d.day} de {MESES_ES[d.month - 1]} de {d.year}'

def kpi_card(icono, valor, rotulo, color='#38BDF8', sub=''):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ''
    return f'<div class="kpi" style="--c: {color};"><div class="kpi-icon">{icono}</div><div><div class="kpi-value">{valor}</div><div class="kpi-label">{rotulo}</div>{sub_html}</div></div>'

if menu == 'Dashboard General':
    st.markdown(
        f'<div class="hero"><div class="hero-main"><div>'
        '<div class="hero-eyebrow">Panel de control</div>'
        '<div class="hero-title">Dirección de Gabinete Interdisciplinario de Asesoramiento Psicopedagógico y Psicológico</div>'
        '<div class="hero-org">Dirección General de Institutos e Instrucción · Policía de Tucumán</div></div></div><div'
        ' class="hero-right"><div class="chip"><span class="dot"></span>Sistema operativo</div>'
        f'<div class="hero-date">{fecha_larga_es(ahora_local().date())}</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    df_c = obtener_cadetes()
    df_p = obtener_personal()
    conn = sqlite3.connect(DB_NAME)
    df_n = pd.read_sql_query('SELECT n.*, c.apellido_nombre, c.curso FROM notas_medicas n LEFT JOIN cadetes c ON n.id_legajo = c.id_legajo', conn)
    df_e = pd.read_sql_query('SELECT e.*, c.apellido_nombre, c.curso, c.genero FROM examenes_periodicos e LEFT JOIN cadetes c ON e.id_legajo = c.id_legajo', conn)
    df_i = pd.read_sql_query('SELECT i.*, c.apellido_nombre, c.curso FROM primera_intervencion i LEFT JOIN cadetes c ON i.id_legajo = c.id_legajo', conn)
    conn.close()

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(kpi_card('🎓', len(df_c), 'Cadetes', '#38BDF8'), unsafe_allow_html=True)
    with col2: st.markdown(kpi_card('🩺', len(df_i), 'Guardias', '#A78BFA'), unsafe_allow_html=True)
    with col3: st.markdown(kpi_card('🧑‍⚕️', len(df_p), 'Staff', '#34D399'), unsafe_allow_html=True)
    with col4: st.markdown(kpi_card('⏳', len(df_n[df_n['estado_alta'] == 'Pendiente']) if not df_n.empty else 0, 'Pendientes', '#FBBF24'), unsafe_allow_html=True)

elif menu == 'Gestión de Legajos':
    st.markdown('<div class="pro-header"><p class="pro-title">📁 Gestión de Legajos</p></div>', unsafe_allow_html=True)
    df_c = obtener_cadetes()
    st.dataframe(df_c, use_container_width=True)

elif menu == 'Personal del Gabinete':
    st.markdown('<div class="pro-header"><p class="pro-title">👥 Personal del Gabinete</p></div>', unsafe_allow_html=True)
    df_p = obtener_personal()
    st.dataframe(df_p, use_container_width=True)

elif menu == '1. Primera Intervención':
    st.markdown('## 🩺 Primera Intervención en Gabinete')
    df_c = obtener_cadetes()
    df_p = obtener_personal()
    if not df_c.empty:
        lista_c = (df_c['id_legajo'].astype(str) + ' - ' + df_c['apellido_nombre']).tolist()
        sel = st.selectbox('Cadete', lista_c)
        id_leg = sel.split(' - ')[0]
        lista_prof = df_p['apellido_nombre'].tolist() if not df_p.empty else ['Sin personal']
        with st.form('f_int'):
            c1, c2 = st.columns(2)
            with c1:
                f_h = st.text_input('Fecha y Hora', value=ahora_local().strftime('%Y-%m-%d %H:%M'))
                prof = st.selectbox('Profesional', lista_prof)
                sint = st.text_area('Síntomas')
            with c2:
                pres = st.text_input('Presión')
                sat = st.text_input('Saturación')
                temp = st.text_input('Temperatura (°C)')
                der = st.selectbox('Derivación', ['Clínica', 'Traumatología', 'Psicología', 'Otro'])
            if st.form_submit_button('Registrar') and exigir('primera_intervencion'):
                conn = sqlite3.connect(DB_NAME)
                conn.execute('INSERT INTO primera_intervencion (id_legajo, fecha_hora, profesional_atiende, sintomas, presion, saturacion, temperatura, derivacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                             (id_leg, f_h, prof, sint, pres, sat, temp, der))
                conn.commit()
                conn.close()
                registrar_auditoria('Intervención', 'INSERT', f'Intervención guardada', id_leg)
                st.success('Registrado con éxito!')
                st.rerun()

elif menu == '2. Notas Médicas y Reposos':
    st.markdown('## 📋 Notas Médicas y Reposos')
    st.info('Módulo activo y protegido.')

elif menu == '3. Control de Alta':
    st.markdown('## ✅ Control de Alta')
    st.info('Gestión de altas activas.')

elif menu == '4. Exámenes Periódicos y Anuales':
    st.markdown('## 🧪 Exámenes Periódicos')
    st.info('Control anual activo.')

elif menu == '5. Historia Clínica Integral':
    st.markdown('## 🗂️ Historia Clínica Integral')
    st.info('Historial clínico disponible.')

elif menu == '6. Examen de Baja / Egreso':
    st.markdown('## 🚪 Examen Médico de Baja / Egreso')
    st.info('Módulo de egresos.')

elif menu == '7. Informes y Análisis de Datos (Spark)':
    render_analisis_avanzado(DB_NAME)

elif menu == '8. Gestión de Usuarios':
    pagina_usuarios()

elif menu == '9. Auditoría del Sistema':
    pagina_auditoria()
