import html as _html
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
