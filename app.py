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
            background-color: #0B132B;
            color: #F8FAFC;
        }
        
        [data-testid="stSidebar"] {
            background-color: #0F172A;
            border-right: 1px solid #1E293B;
        }
        [data-testid="stSidebar"] .stRadio label {
            color: #E2E8F0;
            font-weight: 500;
        }

        .pro-header {
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            padding: 2rem;
            border-radius: 1rem;
            border: 1px solid #334155;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
        .pro-title {
            font-size: 2.2rem;
            font-weight: 700;
            margin: 0;
            color: #FFFFFF;
        }
        .pro-subtitle {
            font-size: 1.05rem;
            color: #94A3B8;
            margin-top: 0.5rem;
            margin-bottom: 0;
        }

        .metric-card {
            background: #111827;
            padding: 1.25rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            border: 1px solid #1F2937;
            text-align: center;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #38BDF8;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #9CA3AF;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
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
            letter-spacing: 0.05em;
        }

        .stTextInput input, .stSelectbox select, .stTextArea textarea, .stDateInput input {
            background-color: #1F2937 !important;
            color: #FFFFFF !important;
            border: 1px solid #374151 !important;
            border-radius: 0.5rem !important;
        }

        .stButton>button {
            background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
            color: white;
            font-weight: 600;
            border-radius: 0.5rem;
            padding: 0.5rem 1.25rem;
            border: none;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%);
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.5);
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
        return True, f"¡Se sincronizaron {cargados} cadetes correctamente!"
    except Exception as e:
        return False, f"Error al procesar el Excel: {str(e)}"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS cadetes (id_legajo TEXT PRIMARY KEY, apellido_nombre TEXT NOT NULL, curso TEXT NOT NULL, dni TEXT, genero TEXT, fecha_nacimiento TEXT, observaciones TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS personal_gabinete (id_legajo_personal TEXT PRIMARY KEY, apellido_nombre TEXT NOT NULL, dni TEXT, matricula TEXT, especialidad TEXT, telefono TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS primera_intervencion (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, fecha_hora TEXT, profesional_atiende TEXT, sintomas TEXT, presion TEXT, saturacion TEXT, derivacion TEXT, FOREIGN KEY(id_legajo) REFERENCES cadetes(id_legajo))")
    cursor.execute("CREATE TABLE IF NOT EXISTS notas_medicas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, nro_expediente TEXT, medico TEXT, diagnostico TEXT, tipo_reposo TEXT, fecha_desde TEXT, fecha_hasta TEXT, medicamentos TEXT, estado_alta TEXT DEFAULT 'Pendiente', FOREIGN KEY(id_legajo) REFERENCES cadetes(id_legajo))")
    cursor.execute("CREATE TABLE IF NOT EXISTS examenes_periodicos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, anio TEXT, ddjj_enfermedades TEXT, visus TEXT, hemograma TEXT, orina TEXT, electrocardiograma TEXT, aptitud_fisica TEXT, toxicologico TEXT, beta_hcg TEXT, fecha_registro TEXT, FOREIGN KEY(id_legajo) REFERENCES cadetes(id_legajo))")
    cursor.execute("CREATE TABLE IF NOT EXISTS examen_baja (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, fecha_baja TEXT, motivo TEXT, estado_salud_egreso TEXT, observaciones_medicas TEXT, FOREIGN KEY(id_legajo) REFERENCES cadetes(id_legajo))")
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
    st.markdown('<div class="pro-header"><p class="pro-title">Panel Sanitario y Gabinete I.E.S.P.</p><p class="pro-subtitle">Sistema de control, historias clinicas y seguimiento de cadetes (1°, 2° y 3° Ano).</p></div>', unsafe_allow_html=True)
    df_c = obtener_cadetes()
    df_p = obtener_personal()
    conn = sqlite3.connect(DB_NAME)
    df_n = pd.read_sql_query("SELECT * FROM notas_medicas", conn)
    df_i = pd.read_sql_query("SELECT * FROM primera_intervencion", conn)
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_c)}</div><div class="metric-label">Cadetes Registrados</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_i)}</div><div class="metric-label">Intervenciones</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_p)}</div><div class="metric-label">Personal Gabinete</div></div>', unsafe_allow_html=True)
    with col4:
        pendientes_alta = len(df_n[df_n['estado_alta'] == 'Pendiente']) if not df_n.empty else 0
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #FBBF24;">{pendientes_alta}</div><div class="metric-label">Altas Pendientes</div></div>', unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Sincronizacion Institucional")
    if st.button("Sincronizar Cadetes desde Excel"):
        exito, msg = importar_excel_directo()
        if exito:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

elif menu == "Gestión de Legajos":
    st.markdown('<h2 style="color: #FFFFFF;">Gestion de Legajos de Cadetes</h2>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Consultar / Listar Compañia", "Registrar Nuevo"])
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
                        st.success(f"¡Legajo {id_legajo} guardado con exito!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Error: El numero de legajo ya existe.")
                else:
                    st.warning("Complete Legajo y Apellido y Nombres.")

elif menu == "Personal del Gabinete":
    st.markdown('<h2 style="color: #FFFFFF;">Gestion del Personal del Gabinete</h2>', unsafe_allow_html=True)
    tab_p1, tab_p2 = st.tabs(["Listado del Personal", "Agregar / Quitar Personal"])
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
                mat_pers = st.text_input("Matricula Profesional").strip()
                esp_pers = st.selectbox("Especialidad / Cargo", ["Medico/a", "Psicologo/a", "Psicopedagogo/a", "Enfermero/a", "Administrativo/a", "Otro"])
                tel_pers = st.text_input("Telefono de Contacto").strip()
            if st.form_submit_button("Registrar Personal"):
                if leg_pers and ap_nom_pers:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO personal_gabinete VALUES (?, ?, ?, ?, ?, ?)", (leg_pers, ap_nom_pers, dni_pers, mat_pers, esp_pers, tel_pers))
                        conn.commit()
                        conn.close()
                        st.success(f"¡Personal {ap_nom_pers} registrado con exito!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Error: El legajo del personal ya existe.")
                else:
                    st.warning("Complete al menos el Legajo y Apellido y Nombres.")
        st.markdown("---")
        st.markdown("### Eliminar Personal del Gabinete")
        df_pers_del = obtener_personal()
        if not df_pers_del.empty:
            lista_del = (df_pers_del['id_legajo_personal'].astype(str) + " - " + df_pers_del['apellido_nombre'] + " (" + df_pers_del['especialidad'] + ")").tolist()
            sel_del = st.selectbox("Seleccione el Personal a Quitar", lista_del)
            if st.button("Eliminar Personal Seleccionado"):
                id_elim = sel_del.split(" - ")[0]
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM personal_gabinete WHERE id_legajo_personal = ?", (id_elim,))
                conn.commit()
                conn.close()
                st.success("¡Personal eliminado correctamente!")
                st.rerun()

elif menu == "1. Primera Intervención":
    st.markdown('<h2 style="color: #FFFFFF;">Primera Intervencion en Gabinete</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    df_personal = obtener_personal()
    if df_cadetes.empty:
        st.warning("No hay cadetes en la base.")
    else:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre']).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        cad_sel = df_cadetes[df_cadetes['id_legajo'].astype(str) == id_legajo].iloc[0]
        
        st.markdown(f'<div class="profile-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div><h3 style="margin: 0; color: #FFFFFF;">{cad_sel["apellido_nombre"]}</h3><p style="margin: 0.25rem 0 0 0; color: #94A3B8; font-size: 0.9rem;">Legajo: <b>{cad_sel["id_legajo"]}</b> | Curso: <b>{cad_sel["curso"]}</b> | DNI: <b>{cad_sel["dni"]}</b></p></div><div><span class="badge-active">ACTIVO</span></div></div></div>', unsafe_allow_html=True)
        
        lista_profesionales = df_personal['apellido_nombre'].tolist() if not df_personal.empty else ["Sin personal registrado (Cargue en 'Personal del Gabinete')"]
        
        with st.form("form_intervencion"):
            st.markdown("#### Registro de Atencion Inicial")
            col1, col2 = st.columns(2)
            with col1:
                fecha_hora = st.text_input("Fecha y Hora", value=str(datetime.now().strftime("%Y-%m-%d %H:%M")))
                profesional_atiende = st.selectbox("Profesional que Atiende (Gabinete)*", lista_profesionales)
                sintomas = st.text_area("Sintomas / Motivo (Dolor de cabeza, lesiones, congestion, etc.)*")
            with col2:
                presion = st.text_input("Valores de Presion Arterial (Ej: 120/80)")
                saturacion = st.text_input("Saturacion de Oxigeno (Ej: 98%)")
                derivacion = st.selectbox("Lugar de Derivacion / Especialista*", [
                    "Clinica Central", "Especialista en Traumatologia", "Especialista en Cardiologia", 
                    "Psicologia / Salud Mental", "Oftalmologia (Visus)", "Odontologia", "Otro Centro Medico / Especialista"
                ])
                derivacion_detalles = st.text_input("Detalles de derivacion / Clinica especifica (Opcional)")
            if st.form_submit_button("Registrar Primera Intervencion"):
                if profesional_atiende and sintomas and derivacion:
                    derivacion_final = f"{derivacion} - {derivacion_detalles}" if derivacion_detalles else derivacion
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO primera_intervencion (id_legajo, fecha_hora, profesional_atiende, sintomas, presion, saturacion, derivacion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (id_legajo, fecha_hora, profesional_atiende, sintomas, presion, saturacion, derivacion_final))
                    conn.commit()
                    conn.close()
                    st.success("¡Primera intervencion registrada correctamente!")
                    st.rerun()
                else:
                    st.warning("Complete los campos obligatorios.")

    st.markdown("### Historial de Intervenciones del Cadete")
    conn = sqlite3.connect(DB_NAME)
    df_ints = pd.read_sql_query(f"SELECT * FROM primera_intervencion WHERE id_legajo = '{id_legajo}'", conn)
    conn.close()
    if not df_ints.empty:
        st.dataframe(df_ints, use_container_width=True)
    else:
        st.info("No registra intervenciones previas.")

elif menu == "2. Notas Médicas y Reposos":
    st.markdown('<h2 style="color: #FFFFFF;">Registro de Notas Medicas y Expedientes</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    if df_cadetes.empty:
        st.warning("No hay cadetes.")
    else:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre']).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        with st.form("form_nota_medica"):
            col1, col2 = st.columns(2)
            with col1:
                nro_expediente = st.text_input("Numero de Expediente (Ej: EXP-2026-XX)")
                medico = st.text_input("Medico Tratante / Matricula")
                diagnostico = st.text_area("Diagnostico Medico")
            with col2:
                tipo_reposo = st.selectbox("Tipo de Reposo", ["Reposo Domiciliario", "Reposo Academico", "Internacion", "ART"])
                fecha_desde = st.date_input("Reposo Desde", value=datetime.today().date())
                fecha_hasta = st.date_input("Reposo Hasta", value=datetime.today().date())
                medicamentos = st.text_input("Medicamentos Indicados")
            if st.form_submit_button("Generar Expediente y Nota Medica"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO notas_medicas (id_legajo, nro_expediente, medico, diagnostico, tipo_reposo, fecha_desde, fecha_hasta, medicamentos, estado_alta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente')",
                               (id_legajo, nro_expediente, medico, diagnostico, tipo_reposo, str(fecha_desde), str(fecha_hasta), medicamentos))
                conn.commit()
                conn.close()
                st.success(f"¡Expediente {nro_expediente} guardado!")

elif menu == "3. Control de Alta":
    st.markdown('<h2 style="color: #FFFFFF;">Control y Convalidacion de Alta Medica</h2>', unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    df_pendientes = pd.read_sql_query("SELECT * FROM notas_medicas WHERE estado_alta = 'Pendiente'", conn)
    conn.close()
    if df_pendientes.empty:
        st.info("No hay notas medicas pendientes de alta.")
    else:
        st.dataframe(df_pendientes, use_container_width=True)
        exp_id = st.selectbox("Seleccione el ID de la Nota / Expediente", df_pendientes['id'].tolist())
        if st.button("Confirmar Alta Medica"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE notas_medicas SET estado_alta = 'Alta Convalidada' WHERE id = ?", (exp_id,))
            conn.commit()
            conn.close()
            st.success("¡Alta medica convalidada!")
            st.rerun()

elif menu == "4. Exámenes Periódicos y Anuales":
    st.markdown('<h2 style="color: #FFFFFF;">Examenes Periodicos y Anuales</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    if df_cadetes.empty:
        st.warning("No hay cadetes.")
    else:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre']).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        cadete_info = df_cadetes[df_cadetes['id_legajo'].astype(str) == id_legajo].iloc[0]
        es_femenino = cadete_info['genero'] == 'Femenino'
        with st.form("form_examenes"):
            anio_eval = st.text_input("Anio de Evaluacion", "2026")
            col1, col2 = st.columns(2)
            with col1:
                ddjj = st.selectbox("DDJJ Enfermedades", ["Aprobada / Sin Novedad", "Con Observaciones"])
                visus = st.text_input("Visus")
                hemograma = st.selectbox("Hemograma", ["Normal", "Alterado", "Pendiente"])
                orina = st.selectbox("Orina", ["Normal", "Alterado", "Pendiente"])
            with col2:
                electro = st.selectbox("Electrocardiograma", ["Normal", "Con Patologia", "Pendiente"])
                aptitud = st.selectbox("Aptitud Fisica", ["Apto", "No Apto"])
                toxicologico = st.selectbox("Toxicologico", ["Negativo", "Positivo", "Pendiente"])
                beta_hcg = st.selectbox("Beta HCG (Trimestral)", ["Negativo", "Positivo", "No Realizado"]) if es_femenino else "N/A"
            if st.form_submit_button("Guardar Examenes"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO examenes_periodicos (id_legajo, anio, ddjj_enfermedades, visus, hemograma, orina, electrocardiograma, aptitud_fisica, toxicologico, beta_hcg, fecha_registro) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (id_legajo, anio_eval, ddjj, visus, hemograma, orina, electro, aptitud, toxicologico, beta_hcg, str(datetime.today())))
                conn.commit()
                conn.close()
                st.success("¡Examenes guardados!")

elif menu == "5. Historia Clínica Integral":
    st.markdown('<h2 style="color: #FFFFFF;">Historia Clinica Integral</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    if df_cadetes.empty:
        st.warning("No hay cadetes.")
    else:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre']).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        cadete = df_cadetes[df_cadetes['id_legajo'].astype(str) == id_legajo].iloc[0]
        st.markdown(f'<div class="profile-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div><h2 style="margin: 0; color: #FFFFFF;">{cadete["apellido_nombre"]}</h2><p style="margin: 0.25rem 0 0 0; color: #94A3B8; font-size: 0.95rem;">Legajo: <b>{cadete["id_legajo"]}</b> | Curso: <b>{cadete["curso"]}</b> | DNI: <b>{cadete["dni"]}</b></p></div><div><span class="badge-active">LEGAJO SANITARIO</span></div></div></div>', unsafe_allow_html=True)
        conn = sqlite3.connect(DB_NAME)
        df_nm = pd.read_sql_query(f"SELECT * FROM notas_medicas WHERE id_legajo = '{id_legajo}'", conn)
        df_int = pd.read_sql_query(f"SELECT * FROM primera_intervencion WHERE id_legajo = '{id_legajo}'", conn)
        conn.close()
        st.markdown("### Notas Medicas y Reposos")
        if not df_nm.empty:
            st.dataframe(df_nm, use_container_width=True)
        else:
            st.write("Sin notas medicas registradas.")
        st.markdown("### Primera Intervencion (Atencion y Derivacion)")
        if not df_int.empty:
            st.dataframe(df_int, use_container_width=True)
        else:
            st.write("Sin intervenciones registradas.")

elif menu == "6. Examen de Baja / Egreso":
    st.markdown('<h2 style="color: #FFFFFF;">Examen Medico de Baja / Egreso</h2>', unsafe_allow_html=True)
    df_cadetes = obtener_cadetes()
    if df_cadetes.empty:
        st.warning("No hay cadetes.")
    else:
        lista_cadetes = (df_cadetes['id_legajo'].astype(str) + " - " + df_cadetes['apellido_nombre'].str.strip()).tolist()
        seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
        id_legajo = seleccion.split(" - ")[0]
        with st.form("form_baja"):
            fecha_baja = st.date_input("Fecha de Baja", value=datetime.today().date())
            motivo = st.selectbox("Motivo", ["Egreso / Graduación", "Baja Voluntaria", "Baja Médica"])
            estado_salud_egreso = st.text_area("Estado General de Salud al Egreso")
            observaciones_medicas = st.text_area("Observaciones / Cierre")
            if st.form_submit_button("Guardar Examen de Baja"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO examen_baja (id_legajo, fecha_baja, motivo, estado_salud_egreso, observaciones_medicas) VALUES (?, ?, ?, ?, ?)",
                               (id_legajo, str(fecha_baja), motivo, estado_salud_egreso, observaciones_medicas))
                conn.commit()
                conn.close()
                st.success("¡Examen de baja registrado!")
