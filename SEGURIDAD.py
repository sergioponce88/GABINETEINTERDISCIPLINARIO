"""Autenticación, control de acceso por roles (RBAC) y auditoría.

Sistema: Gabinete Interdisciplinario (Streamlit + SQLite).

Uso desde app.py:
    import seguridad as sec
    sec.init_seguridad(DB_NAME)      # tablas, triggers, índices, admin inicial
    sec.exigir_login(logo_html)      # login previo; st.stop() si no hay sesión
    sec.tiene_permiso('notas_medicas')
    sec.registrar_auditoria('Notas Médicas', 'INSERT', 'detalle', id_legajo)
"""
import hashlib
import hmac
import html as _html
import io
import json
import os
import re
import secrets
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

try:  # zona horaria local (Argentina no usa horario de verano)
  from zoneinfo import ZoneInfo

  TZ_LOCAL = ZoneInfo('America/Argentina/Tucuman')
except Exception:  # sin tzdata disponible
  TZ_LOCAL = timezone(timedelta(hours=-3))

DB_NAME = 'gabinete_iesp.db'

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
PBKDF2_ITERACIONES = 600_000          # OWASP 2023 para PBKDF2-HMAC-SHA256
MAX_INTENTOS = 5                      # intentos fallidos antes del bloqueo
BLOQUEO_MINUTOS = 15
TIMEOUT_SESION_MIN = int(os.environ.get('SESSION_TIMEOUT_MIN', '30'))
PASSWORD_MIN_LARGO = 10
MAX_PDF_BYTES = 10 * 1024 * 1024

ROL_ADMIN = 'Administrador'
ROL_MEDICO = 'Profesional Médico'
ROL_GUARDIA = 'Guardia / Recepción'
ROL_DIRECTIVO = 'Directivo / Auditor'
ROLES = [ROL_ADMIN, ROL_MEDICO, ROL_GUARDIA, ROL_DIRECTIVO]

ACCIONES_VALIDAS = {
    'INSERT', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'LOGIN_FAIL', 'EXPORT',
    'VIEW', 'DENIED',
}

# ---------------------------------------------------------------------------
# Matriz de permisos (acción -> roles habilitados). Editar aquí para ajustar.
# ---------------------------------------------------------------------------
_TODOS = set(ROLES)
PERMISOS = {
    'ver_dashboard': {ROL_ADMIN, ROL_MEDICO, ROL_DIRECTIVO},
    'ver_legajos_basico': _TODOS,
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

# Ítems del menú, en orden, con el permiso necesario para verlos.
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


# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------
def ahora_local():
  """datetime local *naive* (hora de Tucumán), apto para str()/strftime."""
  return datetime.now(TZ_LOCAL).replace(tzinfo=None)


def _ts():
  return ahora_local().strftime('%Y-%m-%d %H:%M:%S')


def _conn():
  conn = sqlite3.connect(DB_NAME, timeout=15)
  conn.execute('PRAGMA foreign_keys = ON')
  return conn


def nombre_seguro(nombre, unico=True):
  """Nombre de archivo sin rutas ni caracteres peligrosos (anti path-traversal)."""
  base = os.path.basename(str(nombre).replace('\\', '/'))
  raiz, ext = os.path.splitext(base)
  raiz = re.sub(r'[^A-Za-z0-9._-]+', '_', raiz).strip('._') or 'archivo'
  ext = re.sub(r'[^A-Za-z0-9.]+', '', ext)[:10] or '.pdf'
  sufijo = f'_{secrets.token_hex(4)}' if unico else ''
  return f'{raiz[:100]}{sufijo}{ext.lower()}'


def validar_pdf(archivo):
  """Devuelve el archivo subido si es un PDF real y razonable; si no, None."""
  if archivo is None:
    return None
  datos = archivo.getbuffer()
  if len(datos) > MAX_PDF_BYTES:
    st.error(f'«{archivo.name}» supera el máximo de {MAX_PDF_BYTES // 1048576} MB.')
    return None
  if bytes(datos[:5]) != b'%PDF-':
    st.error(f'«{archivo.name}» no es un PDF válido y fue descartado.')
    return None
  return archivo


# ---------------------------------------------------------------------------
# Contraseñas
# ---------------------------------------------------------------------------
def hash_password(password, iteraciones=PBKDF2_ITERACIONES):
  salt = secrets.token_bytes(16)
  dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iteraciones)
  return f'pbkdf2_sha256${iteraciones}${salt.hex()}${dk.hex()}'


def verify_password(password, almacenado):
  try:
    alg, it, salt_hex, hash_hex = almacenado.split('$')
    if alg != 'pbkdf2_sha256':
      return False
    dk = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), bytes.fromhex(salt_hex), int(it)
    )
    return hmac.compare_digest(dk.hex(), hash_hex)
  except Exception:
    return False


_HASH_DUMMY = None


def _verificar_dummy(password):
  """Gasta el mismo tiempo que una verificación real (evita enumerar usuarios)."""
  global _HASH_DUMMY
  if _HASH_DUMMY is None:
    _HASH_DUMMY = hash_password('dummy-password-no-valida')
  verify_password(password, _HASH_DUMMY)


def validar_politica_password(password, username=''):
  if len(password) < PASSWORD_MIN_LARGO:
    return f'La contraseña debe tener al menos {PASSWORD_MIN_LARGO} caracteres.'
  if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
    return 'La contraseña debe combinar letras y números.'
  if username and password.lower() == username.lower():
    return 'La contraseña no puede ser igual al usuario.'
  return None


def generar_password_temporal():
  while True:
    pw = secrets.token_urlsafe(9)
    if validar_politica_password(pw) is None:
      return pw


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
def _hash_log(prev, fecha, usuario, rol, modulo, accion, detalle, ref):
  payload = json.dumps(
      [prev, fecha, usuario, rol, modulo, accion, detalle, ref],
      ensure_ascii=False,
  )
  return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _secreto(nombre):
  valor = os.environ.get(nombre)
  if valor:
    return valor
  try:
    return st.secrets.get(nombre)
  except Exception:
    return None


def init_seguridad(db_name):
  """Crea tablas, triggers de solo-anexado, índices y el admin inicial."""
  global DB_NAME
  DB_NAME = db_name
  conn = _conn()
  cur = conn.cursor()
  roles_sql = ', '.join(f"'{r}'" for r in ROLES)
  cur.execute(f"""
      CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nombre_completo TEXT NOT NULL,
        rol TEXT NOT NULL CHECK (rol IN ({roles_sql})),
        legajo_personal TEXT REFERENCES personal_gabinete(id_legajo_personal)
          ON DELETE SET NULL,
        activo INTEGER NOT NULL DEFAULT 1,
        fecha_creacion TEXT NOT NULL,
        debe_cambiar_password INTEGER NOT NULL DEFAULT 0,
        intentos_fallidos INTEGER NOT NULL DEFAULT 0,
        bloqueado_hasta TEXT
      )""")
  cur.execute("""
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
      )""")
  # Los registros de auditoría no se pueden editar ni borrar (solo anexar).
  cur.execute("""
      CREATE TRIGGER IF NOT EXISTS auditoria_no_update
      BEFORE UPDATE ON auditoria_logs
      BEGIN SELECT RAISE(ABORT, 'auditoria_logs es de solo anexado'); END""")
  cur.execute("""
      CREATE TRIGGER IF NOT EXISTS auditoria_no_delete
      BEFORE DELETE ON auditoria_logs
      BEGIN SELECT RAISE(ABORT, 'auditoria_logs es de solo anexado'); END""")
  for sql in (
      'CREATE INDEX IF NOT EXISTS idx_aud_fecha ON auditoria_logs(fecha_hora)',
      'CREATE INDEX IF NOT EXISTS idx_aud_usuario ON auditoria_logs(usuario)',
      'CREATE INDEX IF NOT EXISTS idx_aud_modulo ON auditoria_logs(modulo)',
      'CREATE INDEX IF NOT EXISTS idx_aud_ref ON auditoria_logs(id_referencia)',
      'CREATE INDEX IF NOT EXISTS idx_pi_legajo ON primera_intervencion(id_legajo)',
      'CREATE INDEX IF NOT EXISTS idx_nm_legajo ON notas_medicas(id_legajo, estado_alta)',
      'CREATE INDEX IF NOT EXISTS idx_ld_legajo ON legajo_documentos(id_legajo)',
      'CREATE INDEX IF NOT EXISTS idx_ep_legajo ON examenes_periodicos(id_legajo)',
  ):
    try:
      cur.execute(sql)
    except sqlite3.OperationalError:
      pass  # tabla de negocio aún inexistente: no es crítico
  conn.commit()

  # Administrador inicial (solo si no existe ningún usuario)
  if cur.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0] == 0:
    pw = _secreto('ADMIN_INITIAL_PASSWORD')
    de_config = bool(pw)
    if not pw:
      pw = generar_password_temporal()
    cur.execute(
        'INSERT INTO usuarios (username, password_hash, nombre_completo, rol,'
        ' activo, fecha_creacion, debe_cambiar_password)'
        ' VALUES (?, ?, ?, ?, 1, ?, 1)',
        ('admin', hash_password(pw), 'Administrador del Sistema', ROL_ADMIN, _ts()),
    )
    conn.commit()
    if not de_config:
      print(
          '[SEGURIDAD] Usuario inicial creado -> usuario: admin | contraseña'
          f' temporal: {pw} (se exige cambiarla en el primer ingreso)',
          file=sys.stderr, flush=True,
      )
  conn.close()


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------
def registrar_auditoria(modulo, accion, detalle, id_referencia=None, _usuario=None):
  """Registra un evento con usuario, rol y hora local. Nunca interrumpe la app.

  No incluir contenido clínico en `detalle`: solo identificadores y metadatos.
  """
  accion = str(accion).upper()
  u = _usuario or st.session_state.get('auth_user') or {}
  username = u.get('username', 'sistema')
  rol = u.get('rol', '-')
  fecha = _ts()
  detalle = str(detalle or '')[:1000]
  ref = None if id_referencia is None else str(id_referencia)[:200]
  conn = None
  try:
    conn = _conn()
    conn.execute('BEGIN IMMEDIATE')
    fila = conn.execute(
        'SELECT hash_registro FROM auditoria_logs ORDER BY id DESC LIMIT 1'
    ).fetchone()
    prev = fila[0] if fila and fila[0] else ''
    h = _hash_log(prev, fecha, username, rol, modulo, accion, detalle, ref)
    conn.execute(
        'INSERT INTO auditoria_logs (fecha_hora, usuario, rol, modulo, accion,'
        ' detalle, id_referencia, hash_prev, hash_registro)'
        ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (fecha, username, rol, modulo, accion, detalle, ref, prev, h),
    )
    conn.commit()
    return True
  except Exception as e:
    print(f'[AUDITORIA] No se pudo registrar el evento: {e}', file=sys.stderr, flush=True)
    return False
  finally:
    if conn is not None:
      conn.close()


def auditar_vista(modulo, detalle, id_referencia):
  """Audita lecturas sensibles una sola vez por selección (evita ruido)."""
  clave = f'_aud_vista_{modulo}'
  if st.session_state.get(clave) != id_referencia:
    st.session_state[clave] = id_referencia
    registrar_auditoria(modulo, 'VIEW', detalle, id_referencia)


def verificar_integridad_logs():
  """Recorre la cadena de hashes. Devuelve (ok, id_primer_error, total)."""
  conn = _conn()
  filas = conn.execute(
      'SELECT id, fecha_hora, usuario, rol, modulo, accion, detalle,'
      ' id_referencia, hash_prev, hash_registro FROM auditoria_logs ORDER BY id'
  ).fetchall()
  conn.close()
  prev = ''
  for (i, f, u, r, m, a, d, ref, hp, hr) in filas:
    esperado = _hash_log(prev, f, u, r, m, a, d, ref)
    if (hp or '') != prev or hr != esperado:
      return False, i, len(filas)
    prev = hr
  return True, None, len(filas)


# ---------------------------------------------------------------------------
# Usuarios (consulta y administración)
# ---------------------------------------------------------------------------
def _fila_usuario(where, params):
  conn = _conn()
  conn.row_factory = sqlite3.Row
  fila = conn.execute(f'SELECT * FROM usuarios WHERE {where}', params).fetchone()
  conn.close()
  return dict(fila) if fila else None


def listar_usuarios():
  conn = _conn()
  df = pd.read_sql_query(
      'SELECT id, username, nombre_completo, rol, legajo_personal, activo,'
      ' fecha_creacion, debe_cambiar_password, intentos_fallidos,'
      ' bloqueado_hasta FROM usuarios ORDER BY username', conn)
  conn.close()
  return df


_RE_USER = re.compile(r'^[a-z0-9._-]{3,32}$')


def crear_usuario(username, nombre, rol, legajo, password):
  username = (username or '').strip().lower()
  nombre = (nombre or '').strip()
  if not _RE_USER.match(username):
    return False, 'Usuario inválido: 3 a 32 caracteres (a-z, 0-9, punto, guion).'
  if not nombre:
    return False, 'Complete el nombre completo.'
  if rol not in ROLES:
    return False, 'Rol inválido.'
  err = validar_politica_password(password, username)
  if err:
    return False, err
  conn = _conn()
  try:
    cur = conn.execute(
        'INSERT INTO usuarios (username, password_hash, nombre_completo, rol,'
        ' legajo_personal, activo, fecha_creacion, debe_cambiar_password)'
        ' VALUES (?, ?, ?, ?, ?, 1, ?, 1)',
        (username, hash_password(password), nombre, rol, legajo or None, _ts()),
    )
    conn.commit()
    nuevo_id = cur.lastrowid
  except sqlite3.IntegrityError as e:
    conn.rollback()
    if 'UNIQUE' in str(e):
      return False, 'Ya existe un usuario con ese nombre.'
    if 'FOREIGN' in str(e):
      return False, 'El profesional vinculado no existe en el staff.'
    return False, f'Error de integridad: {e}'
  finally:
    conn.close()
  registrar_auditoria('Usuarios', 'INSERT', f'Alta de usuario {username} (rol: {rol})', nuevo_id)
  return True, f'Usuario «{username}» creado.'


def _admins_activos(excluyendo_id=None):
  conn = _conn()
  q = 'SELECT COUNT(*) FROM usuarios WHERE rol = ? AND activo = 1'
  p = [ROL_ADMIN]
  if excluyendo_id is not None:
    q += ' AND id <> ?'
    p.append(excluyendo_id)
  n = conn.execute(q, p).fetchone()[0]
  conn.close()
  return n


def _actualizar_usuario(user_id, campos):
  conn = _conn()
  try:
    sets = ', '.join(f'{k} = ?' for k in campos)
    conn.execute(f'UPDATE usuarios SET {sets} WHERE id = ?', (*campos.values(), user_id))
    conn.commit()
  finally:
    conn.close()


def cambiar_estado_usuario(user_id, activo):
  yo = st.session_state.get('auth_user') or {}
  u = _fila_usuario('id = ?', (user_id,))
  if not u:
    return False, 'Usuario inexistente.'
  if not activo:
    if u['id'] == yo.get('id'):
      return False, 'No puede desactivar su propia cuenta.'
    if u['rol'] == ROL_ADMIN and _admins_activos(excluyendo_id=user_id) == 0:
      return False, 'Debe quedar al menos un administrador activo.'
  _actualizar_usuario(user_id, {'activo': 1 if activo else 0})
  registrar_auditoria(
      'Usuarios', 'UPDATE',
      f'{"Activación" if activo else "Desactivación"} de la cuenta {u["username"]}', user_id)
  return True, f'Cuenta «{u["username"]}» {"activada" if activo else "desactivada"}.'


def cambiar_rol_usuario(user_id, nuevo_rol):
  yo = st.session_state.get('auth_user') or {}
  u = _fila_usuario('id = ?', (user_id,))
  if not u or nuevo_rol not in ROLES:
    return False, 'Datos inválidos.'
  if u['id'] == yo.get('id'):
    return False, 'No puede cambiar su propio rol.'
  if u['rol'] == ROL_ADMIN and nuevo_rol != ROL_ADMIN and _admins_activos(excluyendo_id=user_id) == 0:
    return False, 'Debe quedar al menos un administrador activo.'
  _actualizar_usuario(user_id, {'rol': nuevo_rol})
  registrar_auditoria(
      'Usuarios', 'UPDATE', f'Cambio de rol de {u["username"]}: {u["rol"]} → {nuevo_rol}', user_id)
  return True, f'Rol de «{u["username"]}» actualizado.'


def restablecer_password(user_id):
  u = _fila_usuario('id = ?', (user_id,))
  if not u:
    return None, 'Usuario inexistente.'
  temporal = generar_password_temporal()
  _actualizar_usuario(user_id, {
      'password_hash': hash_password(temporal), 'debe_cambiar_password': 1,
      'intentos_fallidos': 0, 'bloqueado_hasta': None})
  registrar_auditoria('Usuarios', 'UPDATE', f'Restablecimiento de contraseña de {u["username"]}', user_id)
  return temporal, u['username']


def desbloquear_usuario(user_id):
  u = _fila_usuario('id = ?', (user_id,))
  if not u:
    return False
  _actualizar_usuario(user_id, {'intentos_fallidos': 0, 'bloqueado_hasta': None})
  registrar_auditoria('Usuarios', 'UPDATE', f'Desbloqueo de la cuenta {u["username"]}', user_id)
  return True


def cambiar_password_propia(user_id, actual, nueva, confirmar):
  u = _fila_usuario('id = ?', (user_id,))
  if not u or not verify_password(actual, u['password_hash']):
    return False, 'La contraseña actual no es correcta.'
  if nueva != confirmar:
    return False, 'La confirmación no coincide.'
  if verify_password(nueva, u['password_hash']):
    return False, 'La nueva contraseña debe ser distinta de la actual.'
  err = validar_politica_password(nueva, u['username'])
  if err:
    return False, err
  _actualizar_usuario(user_id, {
      'password_hash': hash_password(nueva), 'debe_cambiar_password': 0})
  registrar_auditoria('Usuarios', 'UPDATE', 'Cambio de contraseña propio', user_id)
  return True, 'Contraseña actualizada.'


# ---------------------------------------------------------------------------
# Autenticación y sesión
# ---------------------------------------------------------------------------
def autenticar(username, password):
  """Devuelve (usuario_dict | None, mensaje)."""
  username = (username or '').strip().lower()
  generico = 'Usuario o contraseña incorrectos, o cuenta inactiva.'
  u = _fila_usuario('username = ?', (username,))
  if not u:
    _verificar_dummy(password)
    registrar_auditoria('Autenticación', 'LOGIN_FAIL', 'Intento con usuario inexistente',
                        _usuario={'username': '(desconocido)', 'rol': '-'})
    return None, generico
  ctx = {'username': u['username'], 'rol': u['rol']}
  if u['bloqueado_hasta'] and u['bloqueado_hasta'] > _ts():
    _verificar_dummy(password)
    registrar_auditoria('Autenticación', 'LOGIN_FAIL', 'Intento con cuenta bloqueada', u['id'], _usuario=ctx)
    return None, f'Cuenta bloqueada temporalmente por intentos fallidos. Reintente luego de {BLOQUEO_MINUTOS} minutos.'
  if not verify_password(password, u['password_hash']):
    intentos = u['intentos_fallidos'] + 1
    campos = {'intentos_fallidos': intentos}
    detalle = f'Contraseña incorrecta (intento {intentos}/{MAX_INTENTOS})'
    if intentos >= MAX_INTENTOS:
      campos = {'intentos_fallidos': 0,
                'bloqueado_hasta': (ahora_local() + timedelta(minutes=BLOQUEO_MINUTOS)).strftime('%Y-%m-%d %H:%M:%S')}
      detalle += f' - cuenta bloqueada {BLOQUEO_MINUTOS} min'
    _actualizar_usuario(u['id'], campos)
    registrar_auditoria('Autenticación', 'LOGIN_FAIL', detalle, u['id'], _usuario=ctx)
    return None, generico
  if not u['activo']:
    registrar_auditoria('Autenticación', 'LOGIN_FAIL', 'Credenciales correctas en cuenta inactiva', u['id'], _usuario=ctx)
    return None, generico
  _actualizar_usuario(u['id'], {'intentos_fallidos': 0, 'bloqueado_hasta': None})
  return u, 'OK'


def _sesion_desde_fila(u):
  return {
      'id': u['id'], 'username': u['username'], 'nombre': u['nombre_completo'],
      'rol': u['rol'], 'legajo_personal': u['legajo_personal'],
  }


def cerrar_sesion(motivo='Cierre de sesión'):
  if st.session_state.get('auth_user'):
    registrar_auditoria('Autenticación', 'LOGOUT', motivo, st.session_state['auth_user'].get('id'))
  for k in list(st.session_state.keys()):
    del st.session_state[k]


def _form_cambio_password(obligatorio):
  etiqueta = 'Contraseña temporal / actual' if obligatorio else 'Contraseña actual'
  with st.form('sec_form_cambio_pw', clear_on_submit=True):
    actual = st.text_input(etiqueta, type='password')
    nueva = st.text_input('Nueva contraseña', type='password',
                          help=f'Mínimo {PASSWORD_MIN_LARGO} caracteres, con letras y números.')
    conf = st.text_input('Repetir nueva contraseña', type='password')
    enviado = st.form_submit_button('Actualizar contraseña')
  if enviado:
    ok, msg = cambiar_password_propia(st.session_state['auth_user']['id'], actual, nueva, conf)
    if ok:
      st.success(msg)
      return True
    st.error(msg)
  return False


def _pantalla_login(logo_html):
  st.markdown(
      '<style>[data-testid="stSidebar"], [data-testid="collapsedControl"]'
      '{display:none !important;}</style>', unsafe_allow_html=True)
  _, centro, _ = st.columns([1, 1.15, 1])
  with centro:
    st.markdown('<br><br>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="brand">{logo_html}<div><div class="brand-name">I.E.S.P.'
        ' G.J.F.S.M.</div><div class="brand-sub">Dirección de Gabinete Médico'
        '</div></div></div>', unsafe_allow_html=True)
    st.markdown('### Acceso al sistema')
    aviso = st.session_state.pop('msg_login', None)
    if aviso:
      st.info(aviso)
    with st.form('sec_form_login'):
      usuario = st.text_input('Usuario', autocomplete='username')
      clave = st.text_input('Contraseña', type='password', autocomplete='current-password')
      entrar = st.form_submit_button('Ingresar')
    if entrar:
      if not usuario or not clave:
        st.warning('Complete usuario y contraseña.')
      else:
        u, msg = autenticar(usuario, clave)
        if u:
          st.session_state['auth_user'] = _sesion_desde_fila(u)
          st.session_state['auth_last_activity'] = time.time()
          registrar_auditoria('Autenticación', 'LOGIN', 'Inicio de sesión', u['id'])
          st.rerun()
        else:
          st.error(msg)
    st.markdown(
        '<div class="side-foot">🔒 Información sanitaria confidencial. Todos los'
        ' accesos y operaciones quedan registrados.</div>', unsafe_allow_html=True)


def exigir_login(logo_html=''):
  """Bloquea el resto de la app hasta que haya una sesión válida."""
  u = st.session_state.get('auth_user')
  if not u:
    _pantalla_login(logo_html)
    st.stop()

  if time.time() - st.session_state.get('auth_last_activity', 0) > TIMEOUT_SESION_MIN * 60:
    cerrar_sesion(f'Sesión expirada por inactividad ({TIMEOUT_SESION_MIN} min)')
    st.session_state['msg_login'] = 'Su sesión expiró por inactividad. Ingrese nuevamente.'
    st.rerun()
  st.session_state['auth_last_activity'] = time.time()

  # Revalidar contra la base: una baja o cambio de rol rige de inmediato.
  fila = _fila_usuario('id = ?', (u['id'],))
  if not fila or not fila['activo']:
    cerrar_sesion('Sesión cerrada: cuenta desactivada o inexistente')
    st.session_state['msg_login'] = 'Su cuenta ya no está activa.'
    st.rerun()
  st.session_state['auth_user'] = _sesion_desde_fila(fila)

  if fila['debe_cambiar_password']:
    st.markdown(
        '<style>[data-testid="stSidebar"], [data-testid="collapsedControl"]'
        '{display:none !important;}</style>', unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 1.15, 1])
    with centro:
      st.markdown('<br><br>', unsafe_allow_html=True)
      st.markdown('### Debe cambiar su contraseña')
      st.caption('Por seguridad, reemplace la contraseña temporal antes de continuar.')
      if _form_cambio_password(obligatorio=True):
        st.rerun()
    st.stop()
  return st.session_state['auth_user']


def render_sidebar_usuario():
  """Tarjeta de usuario, cambio de contraseña y botón de cierre de sesión."""
  u = st.session_state.get('auth_user')
  if not u:
    return
  st.sidebar.markdown(
      '<div class="side-foot">👤 <b>' + _html.escape(u['nombre']) + '</b><br>'
      + _html.escape(u['rol']) + ' · @' + _html.escape(u['username']) + '</div>',
      unsafe_allow_html=True)
  with st.sidebar.expander('🔑 Cambiar contraseña'):
    _form_cambio_password(obligatorio=False)
  if st.sidebar.button('🚪 Cerrar sesión', use_container_width=True, key='sec_btn_logout'):
    cerrar_sesion()
    st.rerun()


# ---------------------------------------------------------------------------
# Permisos
# ---------------------------------------------------------------------------
def rol_actual():
  return (st.session_state.get('auth_user') or {}).get('rol')


def tiene_permiso(permiso):
  return rol_actual() in PERMISOS.get(permiso, set())


def menu_disponible():
  return [m for m, p in MENU_PERMISOS.items() if tiene_permiso(p)]


def exigir(permiso):
  """True si el rol puede; si no, muestra error y audita el intento."""
  if tiene_permiso(permiso):
    return True
  st.error('⛔ Su rol no tiene permiso para realizar esta acción.')
  registrar_auditoria('Seguridad', 'DENIED', f'Acción sin permiso: {permiso}')
  return False


def autorizar_menu(menu):
  permiso = MENU_PERMISOS.get(menu)
  if permiso is None or tiene_permiso(permiso):
    return True
  st.error('⛔ Su rol no tiene acceso a este módulo.')
  registrar_auditoria('Seguridad', 'DENIED', f'Acceso a módulo no autorizado: {menu}')
  return False


def indice_profesional(nombres, df_personal):
  """Índice del profesional vinculado al usuario logueado (selección por defecto)."""
  leg = (st.session_state.get('auth_user') or {}).get('legajo_personal')
  if not leg or df_personal is None or df_personal.empty:
    return 0
  m = df_personal[df_personal['id_legajo_personal'].astype(str) == str(leg)]
  if m.empty:
    return 0
  nombre = m.iloc[0]['apellido_nombre']
  return nombres.index(nombre) if nombre in nombres else 0


# ---------------------------------------------------------------------------
# Página: gestión de usuarios (solo administradores)
# ---------------------------------------------------------------------------
def pagina_usuarios():
  if not exigir('gestion_usuarios'):
    return
  st.markdown(
      '<div class="pro-header"><p class="pro-title">👤 Gestión de Usuarios y Accesos</p>'
      '<p class="pro-subtitle">Alta de cuentas, asignación de roles, restablecimiento de'
      ' contraseñas y desactivación.</p></div>', unsafe_allow_html=True)

  t_lista, t_crear, t_gest, t_roles = st.tabs([
      '📋 Usuarios', '➕ Crear usuario', '🛠️ Administrar cuenta', '🧭 Matriz de roles'])

  # Se rellenan primero las pestañas que modifican datos, así el listado
  # (que se dibuja al final) ya refleja los cambios de esta misma ejecución.
  with t_crear:
    conn = _conn()
    try:
      df_pers = pd.read_sql_query(
          'SELECT id_legajo_personal, apellido_nombre FROM personal_gabinete ORDER BY apellido_nombre', conn)
    except Exception:
      df_pers = pd.DataFrame(columns=['id_legajo_personal', 'apellido_nombre'])
    conn.close()
    opciones_pers = ['(sin vincular)'] + [
        f'{r.id_legajo_personal} - {r.apellido_nombre}' for r in df_pers.itertuples()]
    with st.form('sec_form_crear_usuario', clear_on_submit=False):
      c1, c2 = st.columns(2)
      with c1:
        n_user = st.text_input('Usuario *', placeholder='ej: mgomez')
        n_nombre = st.text_input('Nombre completo *')
        n_rol = st.selectbox('Rol *', ROLES)
      with c2:
        n_pers = st.selectbox('Vincular a profesional del staff (opcional)', opciones_pers)
        auto = st.checkbox('Generar contraseña temporal automáticamente', value=True)
        n_pass = st.text_input('Contraseña temporal (si no se autogenera)', type='password')
      crear = st.form_submit_button('💾 Crear usuario')
    if crear:
      pw = generar_password_temporal() if auto else n_pass
      leg = None if n_pers == opciones_pers[0] else n_pers.split(' - ')[0]
      ok, msg = crear_usuario(n_user, n_nombre, n_rol, leg, pw)
      if ok:
        st.success(msg)
        st.code(f'Usuario: {n_user.strip().lower()}\nContraseña temporal: {pw}')
        st.caption('Entregue estos datos en forma segura. La contraseña no se volverá a mostrar y deberá cambiarse en el primer ingreso.')
      else:
        st.error(msg)

  with t_gest:
    df_u = listar_usuarios()
    if df_u.empty:
      st.info('No hay usuarios.')
    else:
      etiquetas = {
          int(r.id): f'{r.username} — {r.rol} [{"activo" if r.activo else "INACTIVO"}]'
          for r in df_u.itertuples()}
      uid = st.selectbox('Cuenta', list(etiquetas), format_func=lambda i: etiquetas[i], key='sec_sel_cuenta')
      c1, c2, c3 = st.columns(3)
      fila = df_u[df_u['id'] == uid].iloc[0]
      with c1:
        st.markdown('**Contraseña**')
        if st.button('🔑 Restablecer contraseña', key='sec_btn_reset'):
          temporal, info = restablecer_password(uid)
          if temporal:
            st.success(f'Contraseña de «{info}» restablecida.')
            st.code(temporal)
            st.caption('Se exigirá cambiarla al ingresar. No se volverá a mostrar.')
          else:
            st.error(info)
        if st.button('🔓 Desbloquear cuenta', key='sec_btn_unlock'):
          desbloquear_usuario(uid)
          st.success('Cuenta desbloqueada.')
      with c2:
        st.markdown('**Estado**')
        if fila['activo']:
          if st.button('⛔ Desactivar cuenta', key='sec_btn_off'):
            ok, msg = cambiar_estado_usuario(uid, False)
            (st.success if ok else st.error)(msg)
        else:
          if st.button('✅ Reactivar cuenta', key='sec_btn_on'):
            ok, msg = cambiar_estado_usuario(uid, True)
            (st.success if ok else st.error)(msg)
      with c3:
        st.markdown('**Rol**')
        nuevo_rol = st.selectbox('Nuevo rol', ROLES, index=ROLES.index(fila['rol']), key='sec_sel_rol')
        if st.button('💾 Aplicar rol', key='sec_btn_rol') and nuevo_rol != fila['rol']:
          ok, msg = cambiar_rol_usuario(uid, nuevo_rol)
          (st.success if ok else st.error)(msg)

  with t_roles:
    st.caption('Permisos vigentes por rol (se editan en `PERMISOS` dentro de seguridad.py).')
    matriz = pd.DataFrame(
        {rol: ['✔' if rol in roles else '' for roles in PERMISOS.values()] for rol in ROLES},
        index=list(PERMISOS.keys()))
    st.dataframe(matriz, use_container_width=True)

  with t_lista:
    df_lista = listar_usuarios()
    if not df_lista.empty:
      df_lista['activo'] = df_lista['activo'].map({1: 'Sí', 0: 'No'})
      df_lista['debe_cambiar_password'] = df_lista['debe_cambiar_password'].map({1: 'Sí', 0: 'No'})
      st.dataframe(df_lista, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Página: visor de auditoría
# ---------------------------------------------------------------------------
def _consultar_logs(f, limite):
  sql = ('SELECT id, fecha_hora, usuario, rol, modulo, accion, detalle,'
         ' id_referencia FROM auditoria_logs WHERE 1=1')
  p = []
  for campo, clave in (('usuario', 'usuarios'), ('modulo', 'modulos'), ('accion', 'acciones')):
    if f.get(clave):
      sql += f' AND {campo} IN ({",".join("?" * len(f[clave]))})'
      p += list(f[clave])
  if f.get('desde'):
    sql += ' AND fecha_hora >= ?'
    p.append(f'{f["desde"]} 00:00:00')
  if f.get('hasta'):
    sql += ' AND fecha_hora <= ?'
    p.append(f'{f["hasta"]} 23:59:59')
  if f.get('texto'):
    like = '%' + f['texto'].replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
    sql += " AND (detalle LIKE ? ESCAPE '\\' OR id_referencia LIKE ? ESCAPE '\\')"
    p += [like, like]
  sql += ' ORDER BY id DESC LIMIT ?'
  p.append(int(limite))
  conn = _conn()
  df = pd.read_sql_query(sql, conn, params=p)
  conn.close()
  return df


def generar_pdf_auditoria(df, filtros_txt, emitido_por):
  from reportlab.lib import colors
  from reportlab.lib.pagesizes import landscape, letter
  from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
  from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

  buf = io.BytesIO()
  doc = SimpleDocTemplate(buf, pagesize=landscape(letter), leftMargin=30, rightMargin=30,
                          topMargin=36, bottomMargin=36,
                          title='Registro de Auditoría', author=emitido_por)
  ss = getSampleStyleSheet()
  celda = ParagraphStyle('celda', parent=ss['Normal'], fontName='Helvetica', fontSize=7, leading=8.5)
  cab = ParagraphStyle('cab', parent=celda, fontName='Helvetica-Bold', textColor=colors.white)
  titulo = ParagraphStyle('tit', parent=ss['Title'], fontSize=15, leading=18)

  def p(t, est=celda):
    return Paragraph(_html.escape(str(t if t is not None and str(t) != 'nan' else '')), est)

  encabezado = ['ID', 'Fecha/Hora', 'Usuario', 'Rol', 'Módulo', 'Acción', 'Detalle', 'Referencia']
  filas = [[p(h, cab) for h in encabezado]]
  for r in df.itertuples(index=False):
    filas.append([p(r.id), p(r.fecha_hora), p(r.usuario), p(r.rol), p(r.modulo),
                  p(r.accion), p(r.detalle), p(r.id_referencia)])
  anchos = [30, 78, 70, 82, 80, 64, 258, 58]
  tabla = Table(filas, colWidths=anchos, repeatRows=1)
  tabla.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
      ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
      ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#CBD5E1')),
      ('VALIGN', (0, 0), (-1, -1), 'TOP'),
  ]))
  info = ParagraphStyle('info', parent=ss['Normal'], fontSize=8, leading=10)
  elementos = [
      Paragraph('Registro de Auditoría del Sistema', titulo),
      Paragraph(_html.escape(
          f'Emitido por: {emitido_por} | Fecha: {ahora_local():%d/%m/%Y %H:%M} | Registros: {len(df)}'), info),
      Paragraph(_html.escape(f'Filtros: {filtros_txt}'), info),
      Spacer(1, 8), tabla]

  def pie(canvas, doc_):
    canvas.saveState()
    canvas.setFont('Helvetica', 7)
    canvas.drawString(30, 20, 'Documento confidencial - Gabinete Interdisciplinario')
    canvas.drawRightString(landscape(letter)[0] - 30, 20, f'Página {doc_.page}')
    canvas.restoreState()

  doc.build(elementos, onFirstPage=pie, onLaterPages=pie)
  return buf.getvalue()


def pagina_auditoria():
  if not exigir('ver_auditoria'):
    return
  st.markdown(
      '<div class="pro-header"><p class="pro-title">🛡️ Auditoría del Sistema</p>'
      '<p class="pro-subtitle">Trazabilidad de accesos y operaciones críticas. Los registros'
      ' son de solo lectura y están encadenados criptográficamente.</p></div>', unsafe_allow_html=True)

  conn = _conn()
  usuarios_d = [r[0] for r in conn.execute('SELECT DISTINCT usuario FROM auditoria_logs ORDER BY 1')]
  modulos_d = [r[0] for r in conn.execute('SELECT DISTINCT modulo FROM auditoria_logs ORDER BY 1')]
  conn.close()

  with st.expander('🔎 Filtros', expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
      f_usuarios = st.multiselect('Usuario', usuarios_d)
      rango = st.date_input('Rango de fechas', value=(ahora_local().date() - timedelta(days=7), ahora_local().date()))
    with c2:
      f_modulos = st.multiselect('Módulo', modulos_d)
      f_texto = st.text_input('Buscar en detalle / referencia (ej. legajo)')
    with c3:
      f_acciones = st.multiselect('Tipo de acción', sorted(ACCIONES_VALIDAS))
      limite = st.selectbox('Máx. registros a mostrar', [200, 500, 1000, 5000], index=1)
  desde = hasta = None
  if isinstance(rango, (tuple, list)):
    desde = rango[0] if len(rango) > 0 else None
    hasta = rango[1] if len(rango) > 1 else rango[0] if len(rango) > 0 else None
  elif rango:
    desde = hasta = rango
  filtros = {'usuarios': f_usuarios, 'modulos': f_modulos, 'acciones': f_acciones,
             'desde': desde, 'hasta': hasta, 'texto': f_texto}
  df = _consultar_logs(filtros, limite)

  k1, k2, k3, k4 = st.columns(4)
  k1.metric('Eventos (filtrados)', len(df))
  k2.metric('Usuarios distintos', df['usuario'].nunique() if not df.empty else 0)
  k3.metric('Intentos de acceso fallidos', int((df['accion'] == 'LOGIN_FAIL').sum()) if not df.empty else 0)
  k4.metric('Exportaciones', int((df['accion'] == 'EXPORT').sum()) if not df.empty else 0)

  if not df.empty:
    por_dia = df.assign(dia=df['fecha_hora'].str[:10]).groupby('dia').size().rename('Eventos')
    st.bar_chart(por_dia, height=160)
    st.dataframe(df, use_container_width=True, hide_index=True)

    txt = ', '.join(f'{k}={v}' for k, v in {
        'usuario': f_usuarios, 'módulo': f_modulos, 'acción': f_acciones,
        'desde': desde, 'hasta': hasta, 'texto': f_texto}.items() if v) or 'sin filtros'
    yo = st.session_state.get('auth_user', {})
    pdf = generar_pdf_auditoria(df.head(5000), txt, f'{yo.get("nombre", "")} ({yo.get("username", "")})')
    cd1, cd2 = st.columns(2)
    nombre_base = f'auditoria_{ahora_local():%Y%m%d_%H%M}'
    cd1.download_button('⬇️ Descargar PDF', pdf, file_name=f'{nombre_base}.pdf', mime='application/pdf',
                        on_click=registrar_auditoria,
                        args=('Auditoría', 'EXPORT', f'Descarga PDF de auditoría ({len(df)} registros; {txt})'))
    cd2.download_button('⬇️ Descargar CSV', df.to_csv(index=False).encode('utf-8-sig'),
                        file_name=f'{nombre_base}.csv', mime='text/csv',
                        on_click=registrar_auditoria,
                        args=('Auditoría', 'EXPORT', f'Descarga CSV de auditoría ({len(df)} registros; {txt})'))
  else:
    st.info('No hay eventos para los filtros seleccionados.')

  st.markdown('#### Integridad del registro')
  st.caption('Verifica que ningún evento haya sido alterado o eliminado del medio de la cadena.')
  if st.button('🔐 Verificar integridad de la cadena de auditoría', key='sec_btn_integridad'):
    ok, falla, total = verificar_integridad_logs()
    if ok:
      st.success(f'Cadena íntegra: {total} eventos verificados.')
    else:
      st.error(f'⚠️ Se detectó una alteración en el evento #{falla} (de {total}). Investigue de inmediato.')
