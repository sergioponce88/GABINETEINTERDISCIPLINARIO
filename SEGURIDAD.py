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
    
    # Crear usuario administrador inicial si no existe
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        salt = os.urandom(16).hex()
        # Contraseña inicial por defecto: Admin2026*
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
        
        # Obtener hash anterior para integridad
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

def verificar_credenciales(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt, rol, debe_cambiar_password, intentos_fallidos, bloqueado_hasta, activo FROM usuarios WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False, "Usuario o contraseña incorrectos."
        
    pwd_hash, salt, rol, debe_cambiar, intentos, bloqueado_hasta, activo = row
    
    if not activo:
        return False, "Cuenta desactivada. Contacte al Administrador."
        
    if bloqueado_hasta and datetime.strptime(bloqueado_hasta, '%Y-%m-%d %H:%M:%S') > datetime.utcnow():
        return False, "Cuenta temporalmente bloqueada por múltiples intentos fallidos. Intente más tarde."
        
    calc_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 600000).hex()
    
    if calc_hash == pwd_hash:
        # Resetear intentos fallidos
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        return True, {"username": username, "rol": rol, "debe_cambiar_password": debe_cambiar}
    else:
        # Incrementar intentos fallidos
        nuevos_intentos = intentos + 1
        bloqueo = None
        if nuevos_intentos >= 5:
            bloqueo = (datetime.utcnow() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE username = ?", (nuevos_intentos, bloqueo, username))
        conn.commit()
        conn.close()
        return False, "Usuario o contraseña incorrectos."

def pantalla_login():
    st.markdown('<div class="pro-header" style="text-align: center;"><p class="pro-title">🛡️ I.E.S.P. - G.J.F.S.M.</p><p class="pro-subtitle">Dirección de Gabinete Interdisciplinario · Acceso Restringido</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("🔐 Iniciar Sesión")
        with st.form("form_login"):
            user = st.text_input("Usuario").strip()
            pwd = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Ingresar al Sistema")
            
            if submitted:
                if user and pwd:
                    exito, res = verificar_credenciales(user, pwd)
                    if exito:
                        st.session_state['autenticado'] = True
                        st.session_state['usuario'] = res['username']
                        st.session_state['rol'] = res['rol']
                        st.session_state['debe_cambiar_password'] = res['debe_cambiar_password']
                        registrar_auditoria("Autenticación", "LOGIN_EXITOSO", f"Usuario {user} inició sesión.")
                        st.success("¡Acceso concedido!")
                        st.rerun()
                    else:
                        registrar_auditoria("Autenticación", "LOGIN_FALLIDO", f"Intento fallido para usuario {user}.")
                        st.error(res)
                else:
                    st.warning("Ingrese usuario y contraseña.")
        st.markdown('</div>', unsafe_allow_html=True)

def cambiar_password_obligatorio():
    st.markdown('<div class="pro-header"><p class="pro-title">🔑 Cambio Obligatorio de Contraseña</p><p class="pro-subtitle">Por seguridad, debe actualizar su contraseña inicial antes de continuar.</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        with st.form("form_cambio_pwd"):
            nuevo_pwd = st.text_input("Nueva Contraseña (Mín. 10 caracteres, letras y números)", type="password")
            conf_pwd = st.text_input("Confirmar Nueva Contraseña", type="password")
            btn_cambiar = st.form_submit_button("Actualizar Contraseña")
            
            if btn_cambiar:
                if len(nuevo_pwd) >= 10 and any(c.isalpha() for c in nuevo_pwd) and any(c.isdigit() for c in nuevo_pwd):
                    if nuevo_pwd == conf_pwd:
                        salt = os.urandom(16).hex()
                        pwd_hash = hashlib.pbkdf2_hmac('sha256', nuevo_pwd.encode('utf-8'), bytes.fromhex(salt), 600000).hex()
                        
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET password_hash = ?, salt = ?, debe_cambiar_password = 0 WHERE username = ?",
                                       (pwd_hash, salt, st.session_state['usuario']))
                        conn.commit()
                        conn.close()
                        
                        st.session_state['debe_cambiar_password'] = 0
                        registrar_auditoria("Autenticación", "CAMBIO_PASSWORD", f"Usuario {st.session_state['usuario']} actualizó su contraseña.")
                        st.success("¡Contraseña actualizada con éxito!")
                        st.rerun()
                    else:
                        st.error("Las contraseñas no coinciden.")
                else:
                    st.warning("La contraseña debe tener al menos 10 caracteres, incluyendo letras y números.")
        st.markdown('</div>', unsafe_allow_html=True)

def panel_gestion_usuarios():
    st.markdown('<h2 style="color: #FFFFFF;">👤 Gestión de Usuarios y Roles</h2>', unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_NAME)
    df_u = pd.read_sql_query("SELECT id, username, rol, intentos_fallidos, bloqueado_hasta, activo FROM usuarios", conn)
    conn.close()
    
    st.dataframe(df_u, use_container_width=True)
    
    st.markdown('<br>', unsafe_allow_html=True)
    with st.form("form_crear_usuario"):
        st.markdown("### Crear Nuevo Usuario")
        u_nuevo = st.text_input("Nombre de Usuario").strip()
        p_nuevo = st.text_input("Contraseña Temporal (Mín. 10 caracteres)", type="password")
        rol_nuevo = st.selectbox("Rol Asignado", ['Administrador', 'Médico/a', 'Guardia', 'Directivo'])
        
        if st.form_submit_button("Crear Usuario"):
            if u_nuevo and p_nuevo:
                if len(p_nuevo) >= 10:
                    try:
                        salt = os.urandom(16).hex()
                        pwd_hash = hashlib.pbkdf2_hmac('sha256', p_nuevo.encode('utf-8'), bytes.fromhex(salt), 600000).hex()
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (username, password_hash, salt, rol, debe_cambiar_password, activo) VALUES (?, ?, ?, ?, 1, 1)",
                                       (u_nuevo, pwd_hash, salt, rol_nuevo))
                        conn.commit()
                        conn.close()
                        registrar_auditoria("Usuarios", "CREAR_USUARIO", f"Se creó el usuario {u_nuevo} con rol {rol_nuevo}.")
                        st.success(f"¡Usuario {u_nuevo} creado con éxito!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("El nombre de usuario ya existe.")
                else:
                    st.warning("La contraseña temporal debe tener al menos 10 caracteres.")
            else:
                st.warning("Complete todos los campos.")

def visor_auditoria():
    st.markdown('<h2 style="color: #FFFFFF;">🔍 Visor de Auditoría y Trazabilidad</h2>', unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_NAME)
    df_logs = pd.read_sql_query("SELECT * FROM auditoria_logs ORDER BY id DESC LIMIT 500", conn)
    conn.close()
    
    if not df_logs.empty:
        f1, f2, f3 = st.columns(3)
        with f1:
            mod_filtro = st.selectbox("Filtrar por Módulo", ["Todos"] + list(df_logs['modulo'].unique()))
        with f2:
            usu_filtro = st.selectbox("Filtrar por Usuario", ["Todos"] + list(df_logs['username'].unique()))
        with f3:
            busq_txt = st.text_input("Búsqueda libre en detalle").strip()
            
        df_view = df_logs.copy()
        if mod_filtro != "Todos":
            df_view = df_view[df_view['modulo'] == mod_filtro]
        if usu_filtro != "Todos":
            df_view = df_view[df_view['username'] == usu_filtro]
        if busq_txt:
            df_view = df_view[df_view['detalle'].str.contains(busq_txt, case=False, na=False)]
            
        st.dataframe(df_view, use_container_width=True)
        st.download_button("⬇️ Descargar Logs (CSV)", df_view.to_csv(index=False).encode('utf-8-sig'), file_name=f"auditoria_{datetime.today().date()}.csv", mime="text/csv")
    else:
        st.info("No hay registros de auditoría todavía.")
