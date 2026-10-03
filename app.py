from datetime import datetime, date
import os, sqlite3
import pandas as pd, streamlit as st

st.set_page_config(page_title="Gabinete Medico", page_icon="🛡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
html, body, [class*="css"] { font-family: Inter, sans-serif; background-color: #070D1B; color: #F8FAFC; }
[data-testid="stSidebar"] { background-color: #0B132B; border-right: 1px solid #1E293B; }
.pro-header { background: linear-gradient(135deg, #111C38 0%, #0F172A 100%); padding: 2.5rem; border-radius: 1rem; border: 1px solid #1E3A8A; color: white; margin-bottom: 2rem; }
.pro-title { font-size: 2.5rem; font-weight: 700; margin: 0; color: #FFFFFF; }
.metric-card { background: #111827; padding: 1.5rem; border-radius: 0.85rem; border: 1px solid #1F2937; text-align: center; }
.metric-value { font-size: 2.2rem; font-weight: 700; color: #38BDF8; }
.metric-label { font-size: 0.85rem; color: #9CA3AF; text-transform: uppercase; font-weight: 600; margin-top: 0.25rem; }
.profile-card { background: #111827; padding: 1.75rem; border-radius: 1rem; border: 1px solid #1F2937; margin-bottom: 1.5rem; }
.alert-card { background: #78350F; border: 1px solid #B45309; padding: 1.25rem; border-radius: 0.85rem; margin-bottom: 1rem; color: #FEF3C7; }
.badge-active { background-color: #065F46; color: #34D399; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; }
.stTextInput input, .stSelectbox select, .stTextArea textarea, .stDateInput input { background-color: #111827 !important; color: #FFFFFF !important; border: 1px solid #374151 !important; border-radius: 0.5rem !important; }
.stButton>button { background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%); color: white; font-weight: 600; border-radius: 0.5rem; padding: 0.6rem 1.25rem; border: none; }
</style>""", unsafe_allow_html=True)

DB_NAME = "gabinete_iesp.db"
EXCEL_FILE = "LISTADO DE COMPAÑIA DE CADETES AÑO 2026 PARA D1.xlsx"

def importar_excel_directo():
    if not os.path.exists(EXCEL_FILE): return False, "No se encontro Excel"
    try:
        df_excel = pd.read_excel(EXCEL_FILE, sheet_name=0)
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor(); cargados = 0
        for _, row in df_excel.iterrows():
            if pd.isna(row.get("APELLIDO")) or pd.isna(row.get("NOMBRES")): continue
            id_leg = str(row.get("CARGO", row.get("N°", "S/N"))).strip()
            ap_nom = f"{str(row.get("APELLIDO", "")).strip()}, {str(row.get("NOMBRES", "")).strip()}"
            curso = str(row.get("CURSO", "1 AÑO")).strip(); dni = str(row.get("DNI", "")).strip()
            cursor.execute("INSERT OR IGNORE INTO cadetes VALUES (?, ?, ?, ?, ?, ?, ?)", (id_leg, ap_nom, curso, dni, "Masculino", str(row.get("FECHA DE NACIMIENTO", "")).split(" ")[0], f"Email: {row.get("EMAIL", "")}"))
            cargados += 1
        conn.commit(); conn.close()
        return True, f"Sincronizados {cargados} cadetes."
    except Exception as e: return False, str(e)

def init_db():
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS cadetes (id_legajo TEXT PRIMARY KEY, apellido_nombre TEXT NOT NULL, curso TEXT NOT NULL, dni TEXT, genero TEXT, fecha_nacimiento TEXT, observaciones TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS personal_gabinete (id_legajo_personal TEXT PRIMARY KEY, apellido_nombre TEXT NOT NULL, dni TEXT, matricula TEXT, especialidad TEXT, telefono TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS primera_intervencion (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, fecha_hora TEXT, profesional_atiende TEXT, sintomas TEXT, presion TEXT, saturacion TEXT, derivacion TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS notas_medicas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, nro_expediente TEXT, medico TEXT, diagnostico TEXT, tipo_reposo TEXT, fecha_desde TEXT, fecha_hasta TEXT, medicamentos TEXT, estado_alta TEXT DEFAULT 'Pendiente')")
    cursor.execute("CREATE TABLE IF NOT EXISTS examenes_periodicos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, anio TEXT, ddjj_enfermedades TEXT, visus TEXT, hemograma TEXT, orina TEXT, electrocardiograma TEXT, aptitud_fisica TEXT, toxicologico TEXT, beta_hcg TEXT, fecha_registro TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS examen_baja (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT, fecha_baja TEXT, motivo TEXT, estado_salud_egreso TEXT, observaciones_medicas TEXT)")
    conn.commit(); conn.close()
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cadetes"); count = cursor.fetchone()[0]; conn.close()
    if count == 0: importar_excel_directo()

init_db()

def obtener_cadetes():
    conn = sqlite3.connect(DB_NAME); df = pd.read_sql_query("SELECT * FROM cadetes", conn); conn.close(); return df

def obtener_personal():
    conn = sqlite3.connect(DB_NAME); df = pd.read_sql_query("SELECT * FROM personal_gabinete", conn); conn.close(); return df

st.sidebar.image("https://img.icons8.com/color/96/police-badge.png", width=70)
st.sidebar.markdown("### I.E.S.P. G.J.F.S.M.")
menu = st.sidebar.radio("Navegacion", ["Dashboard General", "Gestión de Legajos", "Personal del Gabinete", "1. Primera Intervención", "2. Notas Médicas y Reposos", "3. Control de Alta", "4. Exámenes Periódicos y Anuales", "5. Historia Clínica Integral", "6. Examen de Baja / Egreso", "7. Informes y Análisis de Datos"])

if menu == "Dashboard General":
    st.markdown('<div class="pro-header"><p class="pro-title">🏥 Centro Medico y Gabinete I.E.S.P.</p><p class="pro-subtitle">Sistema integral de gestion sanitaria y control de alertas.</p></div>', unsafe_allow_html=True)
    df_c = obtener_cadetes(); df_p = obtener_personal()
    conn = sqlite3.connect(DB_NAME)
    df_n = pd.read_sql_query("SELECT n.*, c.apellido_nombre, c.curso FROM notas_medicas n LEFT JOIN cadetes c ON n.id_legajo = c.id_legajo", conn)
    df_e = pd.read_sql_query("SELECT e.*, c.apellido_nombre, c.curso, c.genero FROM examenes_periodicos e LEFT JOIN cadetes c ON e.id_legajo = c.id_legajo", conn)
    df_i = pd.read_sql_query("SELECT i.*, c.apellido_nombre, c.curso FROM primera_intervencion i LEFT JOIN cadetes c ON i.id_legajo = c.id_legajo", conn); conn.close()
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_c)}</div><div class="metric-label">Cadetes</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_i)}</div><div class="metric-label">Intervenciones</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_p)}</div><div class="metric-label">Staff</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #FBBF24;">{len(df_n[df_n.estado_alta=="Pendiente"]) if not df_n.empty else 0}</div><div class="metric-label">Altas Pendientes</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    dash_tab1, dash_tab2, dash_tab3 = st.tabs(["🚨 Centro de Alertas y Vencimientos", "📋 Consulta General de Compañía", "⚡ Acciones Rápidas"])
    with dash_tab1:
        st.markdown("### 🚨 Alertas Clínicas y Control de Vencimientos")
        hoy = datetime.today().date()
        if not df_n.empty:
            pendientes = df_n[df_n['estado_alta'] == 'Pendiente'].copy()
            if not pendientes.empty:
                for _, row in pendientes.iterrows():
                    f_hasta = pd.to_datetime(row['fecha_hasta']).date() if pd.notna(row['fecha_hasta']) else hoy
                    dias_dif = (hoy - f_hasta).days
                    if dias_dif > 0:
                        st.markdown(f'<div class="alert-card"><b>⚠️ EXPEDIENTE VENCIDO / ALTA VENCIDA:</b> El cadete <b>{row["apellido_nombre"]}</b> tiene un reposo finalizado el <b>{row["fecha_hasta"]}</b> (hace {dias_dif} días) sin convalidación de alta.</div>', unsafe_allow_html=True)
        if not df_e.empty:
            femeninos_ex = df_e[df_e['genero'] == 'Femenino'].copy()
            if not femeninos_ex.empty:
                for _, row in femeninos_ex.iterrows():
                    f_reg = pd.to_datetime(row['fecha_registro']).date() if pd.notna(row['fecha_registro']) else hoy
                    dias_beta = (hoy - f_reg).days
                    if dias_beta > 90:
                        st.markdown(f'<div class="alert-card"><b>⚠️ VENCIMIENTO ANÁLISIS DE GONADOTROPINA CORIÓNICA HUMANA (BETA HCG):</b> La cadete <b>{row["apellido_nombre"]}</b> supera los 3 meses desde su último control trimestral.</div>', unsafe_allow_html=True)
    with dash_tab2:
        st.markdown("### 👥 Consulta Rápida")
        if not df_c.empty: st.dataframe(df_c, use_container_width=True)
    with dash_tab3:
        st.markdown("### ⚙️ Administración")
        if st.button("Sincronizar Base de Cadetes"): importar_excel_directo(); st.rerun()
elif menu == "Gestión de Legajos":
    st.markdown("## Legajos"); st.dataframe(obtener_cadetes(), use_container_width=True)
elif menu == "Personal del Gabinete":
    st.markdown("## Personal"); st.dataframe(obtener_personal(), use_container_width=True)
elif menu == "7. Informes y Análisis de Datos":
    st.markdown('<h2 style="color: #FFFFFF;">📊 Informes y Análisis Epidemiológico Institucional</h2>', unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>Análisis avanzado de datos sanitarios de la compañía para la toma de decisiones basada en evidencia.</p>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    df_c_rep = pd.read_sql_query("SELECT * FROM cadetes", conn)
    df_i_rep = pd.read_sql_query("SELECT i.*, c.curso, c.apellido_nombre FROM primera_intervencion i LEFT JOIN cadetes c ON i.id_legajo = c.id_legajo", conn)
    conn.close()
    inf_tab1, inf_tab2, inf_tab3 = st.tabs(["📈 Estadísticas por Curso", "🏥 Morbilidad y Derivaciones", "📋 Reporte Ejecutivo"])
    with inf_tab1:
        st.markdown("### Distribución de Cadetes e Intervenciones por Curso")
        if not df_c_rep.empty:
            st.dataframe(df_c_rep['curso'].value_counts().reset_index(), use_container_width=True)
    with inf_tab2:
        st.markdown("### Análisis de Motivos y Centros de Derivación")
        if not df_i_rep.empty:
            st.dataframe(df_i_rep['derivacion'].value_counts().reset_index(), use_container_width=True)
    with inf_tab3:
        st.markdown("### Generación de Reporte Consolidado")
        if st.button("📥 Descargar Reporte CSV"):
            if not df_i_rep.empty:
                st.download_button("Descargar archivo", data=df_i_rep.to_csv(index=False).encode('utf-8'), file_name="reporte.csv", mime="text/csv")
else:
    st.markdown(f"## Módulo: {menu}")
