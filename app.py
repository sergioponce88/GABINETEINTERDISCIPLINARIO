from datetime import datetime, date
import os
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Gabinete Medico | I.E.S.P. G.J.F.S.M.",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #070D1B;
        color: #F8FAFC;
    }
    [data-testid="stSidebar"] {
        background-color: #0B132B;
        border-right: 1px solid #1E293B;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #E2E8F0;
        font-weight: 500;
    }
    .pro-header {
        background: linear-gradient(135deg, #111C38 0%, #0F172A 100%);
        padding: 2.5rem;
        border-radius: 1rem;
        border: 1px solid #1E3A8A;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 15px 30px -5px rgba(15, 23, 42, 0.6);
    }
    .pro-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        color: #FFFFFF;
    }
    .pro-subtitle {
        font-size: 1.1rem;
        color: #94A3B8;
        margin-top: 0.5rem;
        margin-bottom: 0;
    }
    .metric-card {
        background: #111827;
        padding: 1.5rem;
        border-radius: 0.85rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        border: 1px solid #1F2937;
        text-align: center;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #38BDF8;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #9CA3AF;
        text-transform: uppercase;
        font-weight: 600;
        margin-top: 0.25rem;
    }
    .profile-card {
        background: #111827;
        padding: 1.75rem;
        border-radius: 1rem;
        border: 1px solid #1F2937;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        margin-bottom: 1.5rem;
    }
    .badge-active {
        background-color: #065F46;
        color: #34D399;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .stTextInput input, .stSelectbox select, .stTextArea textarea, .stDateInput input {
        background-color: #111827 !important;
        color: #FFFFFF !important;
        border: 1px solid #374151 !important;
        border-radius: 0.5rem !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        font-weight: 600;
        border-radius: 0.5rem;
        padding: 0.6rem 1.25rem;
        border: none;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
</style>
""", unsafe_allow_html=True)

DB_NAME = "gabinete_iesp.db"
EXCEL_FILE = "LISTADO DE COMPAÑIA DE CADETES AÑO 2026 PARA D1.xlsx"

def importar_excel_directo():
    if not os.path.exists(EXCEL_FILE):
        return False, f"No se encontro el archivo Excel: {EXCEL_FILE}"
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
            genero = "Masculino"
            f_nac = str(row.get('FECHA DE NACIMIENTO', '')).split(' ')[0] if pd.notna(row.get('FECHA DE NACIMIENTO')) else ""
            obs = f"Email: {row.get('EMAIL', '')} | Celular: {row.get('CELULAR', '')} | CUIL: {row.get('CUIL', '')}"
            cursor.execute("INSERT OR IGNORE INTO cadetes (id_legajo, apellido_nombre, curso, dni, genero, fecha_nacimiento, observaciones) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (id_leg, ap_nom, curso, dni, genero, f_nac, obs))
            cargados += 1
        conn.commit()
        conn.close()
        return True, f"Se sincronizaron {cargados} cadetes correctamente."
    except Exception as e:
        return False, f"Error al procesar el Excel: {str(e)}"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS cadetes (id_legajo TEXT PRIMARY KEY, apellido_nombre TEXT NOT NULL, curso TEXT NOT NULL, dni TEXT, genero TEXT, fecha_nacimiento TEXT, observaciones TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS personal_gabinete (id_legajo_personal TEXT PRIMARY KEY, apellido_nombre TEXT NOT NULL, dni TEXT, matricula TEXT, especialidad TEXT, telefono TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS primera_intervencion (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, fecha_hora TEXT, profesional_atiende TEXT, sintomas TEXT, presion TEXT, saturacion TEXT, derivacion TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS notas_medicas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, nro_expediente TEXT, medico TEXT, diagnostico TEXT, tipo_reposo TEXT, fecha_desde TEXT, fecha_hasta TEXT, medicamentos TEXT, estado_alta TEXT DEFAULT 'Pendiente')")
    cursor.execute("CREATE TABLE IF NOT EXISTS examenes_periodicos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, anio TEXT, ddjj_enfermedades TEXT, visus TEXT, hemograma TEXT, orina TEXT, electrocardiograma TEXT, aptitud_fisica TEXT, toxicologico TEXT, beta_hcg TEXT, fecha_registro TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS examen_baja (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, fecha_baja TEXT, motivo TEXT, estado_salud_egreso TEXT, observaciones_medicas TEXT)")
    conn.commit()
    conn.close()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cadetes")
    count = cursor.fetchone()[0]
    conn.close()
    if count == 0:
        importar_excel_directo()

init_db()

def obtener_cadetes():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM cadetes", conn)
    conn.close()
    return df

def obtener_personal():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM personal_gabinete", conn)
    conn.close()
    return df

st.sidebar.image("https://img.icons8.com/color/96/police-badge.png", width=70)
st.sidebar.markdown("### I.E.S.P. G.J.F.S.M.")
st.sidebar.markdown("<small style='color: #94A3B8;'>Direccion de Gabinete</small>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.radio("Navegacion Principal", [
    "Dashboard General",
    "Gestión de Legajos",
    "Personal del Gabinete",
    "1. Primera Intervención",
    "2. Notas Médicas y Reposos",
    "3. Control de Alta",
    "4. Exámenes Periódicos y Anuales",
    "5. Historia Clínica Integral",
    "6. Examen de Baja / Egreso"
])

if menu == "Dashboard General":
    st.markdown('<div class="pro-header"><p class="pro-title">Centro Medico y Gabinete I.E.S.P.</p><p class="pro-subtitle">Sistema integral de gestion sanitaria, historias clinicas de cadetes y control de guardia.</p></div>', unsafe_allow_html=True)
    df_c = obtener_cadetes()
    df_p = obtener_personal()
    conn = sqlite3.connect(DB_NAME)
    df_n = pd.read_sql_query("SELECT * FROM notas_medicas", conn)
    df_i = pd.read_sql_query("SELECT * FROM primera_intervencion", conn)
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_c)}</div><div class="metric-label">Cadetes en Compania</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_i)}</div><div class="metric-label">Intervenciones Guardia</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_p)}</div><div class="metric-label">Staff Gabinete Activo</div></div>', unsafe_allow_html=True)
    with col4:
        pendientes_alta = len(df_n[df_n['estado_alta'] == 'Pendiente']) if not df_n.empty else 0
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #FBBF24;">{pendientes_alta}</div><div class="metric-label">Altas Pendientes</div></div>', unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_dash1, col_dash2 = st.columns(2)
    with col_dash1:
        st.markdown("""
            <div class="profile-card">
                <h3 style="margin-top: 0; color: #38BDF8;">Accesos Rapidos del Servicio Medico</h3>
                <p style="color: #94A3B8; font-size: 0.95rem;">Utilice el panel lateral para navegar entre modulos de atencion clinica.</p>
            </div>
        """, unsafe_allow_html=True)
    with col_dash2:
        st.markdown("""
            <div class="profile-card">
                <h3 style="margin-top: 0; color: #38BDF8;">Estado de Sincronizacion</h3>
                <p style="color: #94A3B8; font-size: 0.95rem;">La base de datos institucional se encuentra conectada al listado oficial.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Sincronizar Base de Cadetes"):
            exito, msg = importar_excel_directo()
            if exito:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

elif menu == "Gestión de Legajos":
    st.markdown('<h2 style="color: #FFFFFF;">Gestion de Legajos de Cadetes</h2>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Consultar / Listar Compania", "Registrar Nuevo"])
    with tab1:
        if st.button("Recargar Base"):
            ex, ms = importar_excel_directo()
            if ex:
                st.success(ms)
                st.rerun()
        df_cadetes = obtener_cadetes()
        if not df_cadetes.empty:
            busqueda = st.text_input("Busqueda rapida por Apellido, Nombre o Numero de Legajo/Cargo")
            if busqueda:
                df_cadetes = df_cadetes[df_cadetes['apellido_nombre'].str.contains(busqueda, case=False, na=False) | df_cadetes['id_legajo'].astype(str).str.contains(busqueda, case=False, na=False)]
            st.dataframe(df_cadetes, use_container_width=True)
        else:
            st.warning("No hay cadetes en la base.")
    with tab2:
        with st.form("form_nuevo_cadete"):
            col1, col2 = st.columns(2)
            with col1:
                id_legajo = st.text_input("Numero de Legajo / Cargo*").strip()
                apellido_nombre = st.text_input("Apellido y Nombres*").strip()
                curso = st.selectbox("Curso", ["1 AÑO", "2 AÑO", "3 AÑO"])
            with col2:
                dni = st.text_input("DNI")
                genero = st.selectbox("Genero", ["Masculino", "Femenino", "Otro"])
                fecha_nacimiento = st.date_input("Fecha de Nacimiento", value=date(2000, 1, 1))
            observaciones = st.text_area("Observaciones / Contacto / Antecedentes")
            if st.form_submit_button("Guardar Legajo"):
                if id_legajo and apellido_nombre:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO cadetes VALUES (?, ?, ?, ?, ?, ?, ?)", (id_legajo, apellido_nombre, curso, dni, genero, str(fecha_nacimiento), observaciones))
                        conn.commit()
                        conn.close()
                        st.success("Legajo guardado con exito!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Error: El numero de legajo ya existe.")
                else:
                    st.warning("Complete Legajo y Apellido y Nombres.")

elif menu == "Personal del Gabinete":
    st.markdown('<h2 style="color: #FFFFFF;">Staff Medico y Personal del Gabinete</h2>', unsafe_allow_html=True)
    tab_p1, tab_p2 = st.tabs(["Listado de Staff", "Alta / Baja de Personal"])
    with tab_p1:
        df_personal = obtener_personal()
        if not df_personal.empty:
            st.dataframe(df_personal, use_container_width=True)
        else:
            st.info("No hay personal del gabinete registrado todavia.")
    with tab_p2:
        with st.form("form_personal"):
            col1, col2 = st.columns(2)
            with col1:
                leg_pers = st.text_input("Numero de Legajo / ID Personal*").strip()
                ap_nom_pers = st.text_input("Apellido y Nombres*").strip()
                dni_pers = st.text_input("DNI").strip()
            with col2:
                mat_pers = st.text_input("Matricula Profesional*").strip()
                esp_pers = st.selectbox("Especialidad", ["Medico/a Clinico/a", "Psicologo/a", "Psicopedagogo/a", "Psiquiatra", "Enfermero/a", "Administrativo/a", "Otro"])
                tel_pers = st.text_input("Telefono de Contacto").strip()
            if st.form_submit_button("Registrar Profesional"):
                if leg_pers and ap_nom_pers and mat_pers:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO personal_gabinete VALUES (?, ?, ?, ?, ?, ?)", (leg_pers, ap_nom_pers, dni_pers, mat_pers, esp_pers, tel_pers))
                        conn.commit()
                        conn.close()
                        st.success("Profesional registrado con exito!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Error: El legajo ya existe.")
                else:
                    st.warning("Complete los campos obligatorios (*).")
        st.markdown("---")
        st.markdown("### Baja de Personal")
        df_pers_del = obtener_personal()
        if not df_pers_del.empty:
            lista_del = (df_pers_del['id_legajo_personal'].astype(str) + " - " + df_pers_del['apellido_nombre'] + " (" + df_pers_del['especialidad'] + ")").tolist()
            sel_del = st.selectbox("Seleccione el Profesional a Dar de Baja", lista_del)
            if st.button("Confirmar Baja"):
                id_elim = sel_del.split(" - ")[0]
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM personal_gabinete WHERE id_legajo_personal = ?", (id_elim,))
                conn.commit()
                conn.close()
                st.success("Personal dado de baja!")
                st.rerun()

elif menu == "1. Primera Intervención":
    st.markdown('<h2 style="color: #FFFFFF;">Primera Intervencion en Gabinete</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    df_personal = obtener_personal()
    if df_cadetes.empty:
        st.warning("No hay cadetes.")
    else:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre']).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        cad_sel = df_cadetes[df_cadetes['id_legajo'].astype(str) == id_legajo].iloc[0]
        
        st.markdown(f'<div class="profile-card"><h3 style="margin: 0; color: #FFFFFF;">{cad_sel["apellido_nombre"]}</h3><p style="margin: 0.25rem 0 0 0; color: #94A3B8;">Legajo: <b>{cad_sel["id_legajo"]}</b> | Curso: <b>{cad_sel["curso"]}</b> | DNI: <b>{cad_sel["dni"]}</b></p></div>', unsafe_allow_html=True)
        
        lista_profesionales = df_personal['apellido_nombre'].tolist() if not df_personal.empty else ["Sin personal registrado"]
        
        with st.form("form_intervencion"):
            col1, col2 = st.columns(2)
            with col1:
                fecha_hora = st.text_input("Fecha y Hora", value=str(datetime.now().strftime("%Y-%m-%d %H:%M")))
                profesional_atiende = st.selectbox("Profesional que Atiende*", lista_profesionales)
                sintomas = st.text_area("Sintomas / Motivo*")
            with col2:
                presion = st.text_input("Presion Arterial")
                saturacion = st.text_input("Saturacion O2")
                derivacion = st.selectbox("Derivacion / Especialista*", ["Clinica Central", "Traumatologia", "Cardiologia", "Psicologia", "Oftalmologia", "Odontologia", "Otro"])
                derivacion_detalles = st.text_input("Detalles especificos")
            if st.form_submit_button("Registrar Intervencion"):
                if profesional_atiende and sintomas and derivacion:
                    derivacion_final = f"{derivacion} - {derivacion_detalles}" if derivacion_detalles else derivacion
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO primera_intervencion (id_legajo, fecha_hora, profesional_atiende, sintomas, presion, saturacion, derivacion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (id_legajo, fecha_hora, profesional_atiende, sintomas, presion, saturacion, derivacion_final))
                    conn.commit()
                    conn.close()
                    st.success("Intervencion registrada!")
                    st.rerun()
                else:
                    st.warning("Complete campos obligatorios.")
    st.markdown("### Historial")
    conn = sqlite3.connect(DB_NAME)
    df_ints = pd.read_sql_query(f"SELECT * FROM primera_intervencion WHERE id_legajo = '{id_legajo}'", conn)
    conn.close()
    if not df_ints.empty:
        st.dataframe(df_ints, use_container_width=True)

elif menu == "2. Notas Médicas y Reposos":
    st.markdown('<h2 style="color: #FFFFFF;">Notas Medicas y Reposos</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    if not df_cadetes.empty:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre']).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        with st.form("form_nota_medica"):
            col1, col2 = st.columns(2)
            with col1:
                nro_expediente = st.text_input("Numero de Expediente*")
                medico = st.text_input("Medico / Matricula*")
                diagnostico = st.text_area("Diagnostico*")
            with col2:
                tipo_reposo = st.selectbox("Tipo de Reposo", ["Domiciliario", "Academico", "Internacion", "ART"])
                fecha_desde = st.date_input("Desde", value=datetime.today().date())
                fecha_hasta = st.date_input("Hasta", value=datetime.today().date())
                medicamentos = st.text_input("Medicamentos")
            if st.form_submit_button("Guardar Nota Medica"):
                if nro_expediente and medico and diagnostico:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO notas_medicas (id_legajo, nro_expediente, medico, diagnostico, tipo_reposo, fecha_desde, fecha_hasta, medicamentos, estado_alta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente')",
                                   (id_legajo, nro_expediente, medico, diagnostico, tipo_reposo, str(fecha_desde), str(fecha_hasta), medicamentos))
                    conn.commit()
                    conn.close()
                    st.success("Nota medica guardada!")

elif menu == "3. Control de Alta":
    st.markdown('<h2 style="color: #FFFFFF;">Control de Alta</h2>', unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    df_pendientes = pd.read_sql_query("SELECT * FROM notas_medicas WHERE estado_alta = 'Pendiente'", conn)
    conn.close()
    if not df_pendientes.empty:
        st.dataframe(df_pendientes, use_container_width=True)
        exp_id = st.selectbox("ID Nota", df_pendientes['id'].tolist())
        if st.button("Convalidar Alta"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE notas_medicas SET estado_alta = 'Alta Convalidada' WHERE id = ?", (exp_id,))
            conn.commit()
            conn.close()
            st.success("Alta convalidada!")
            st.rerun()
    else:
        st.info("Sin notas pendientes.")

elif menu == "4. Exámenes Periódicos y Anuales":
    st.markdown('<h2 style="color: #FFFFFF;">Examenes Periodicos</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    if not df_cadetes.empty:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre']).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        with st.form("form_examenes"):
            col1, col2 = st.columns(2)
            with col1:
                ddjj = st.selectbox("DDJJ", ["Aprobada", "Observada"])
                visus = st.text_input("Visus")
                hemograma = st.selectbox("Hemograma", ["Normal", "Alterado"])
            with col2:
                electro = st.selectbox("Electro", ["Normal", "Patologico"])
                aptitud = st.selectbox("Aptitud", ["Apto", "No Apto"])
            if st.form_submit_button("Guardar Examenes"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO examenes_periodicos (id_legajo, anio, ddjj_enfermedades, visus, hemograma, orina, electrocardiograma, aptitud_fisica, toxicologico, beta_hcg, fecha_registro) VALUES (?, '2026', ?, ?, ?, 'Normal', ?, ?, 'Negativo', 'N/A', ?)",
                               (id_legajo, ddjj, visus, hemograma, electro, aptitud, str(datetime.today())))
                conn.commit()
                conn.close()
                st.success("Examenes guardados!")

elif menu == "5. Historia Clínica Integral":
    st.markdown('<h2 style="color: #FFFFFF;">Historia Clinica Integral</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    if not df_cadetes.empty:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre']).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        conn = sqlite3.connect(DB_NAME)
        df_nm = pd.read_sql_query(f"SELECT * FROM notas_medicas WHERE id_legajo = '{id_legajo}'", conn)
        df_int = pd.read_sql_query(f"SELECT * FROM primera_intervencion WHERE id_legajo = '{id_legajo}'", conn)
        conn.close()
        st.dataframe(df_nm, use_container_width=True)
        st.dataframe(df_int, use_container_width=True)

elif menu == "6. Examen de Baja / Egreso":
    st.markdown('<h2 style="color: #FFFFFF;">Examen de Baja / Egreso</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    if not df_cadetes.empty:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre']).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        with st.form("form_baja"):
            motivo = st.selectbox("Motivo", ["Egreso", "Baja Voluntaria", "Baja Medica"])
            estado = st.text_area("Estado de Salud al Egreso")
            if st.form_submit_button("Guardar Baja"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO examen_baja (id_legajo, fecha_baja, motivo, estado_salud_egreso, observaciones_medicas) VALUES (?, ?, ?, ?, ?)",
                               (id_legajo, str(datetime.today().date()), motivo, estado, ""))
                conn.commit()
                conn.close()
                st.success("Baja registrada!")
