from datetime import datetime, date
import os
import sqlite3
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Gabinete Médico | I.E.S.P. G.J.F.S.M.",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- DISEÑO Y ESTILOS CSS PRO (UI/UX CLÍNICO) ---
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #F8FAFC;
        }

        .pro-header {
            background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
            padding: 2rem;
            border-radius: 1rem;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
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
            background: #FFFFFF;
            padding: 1.25rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            border: 1px solid #E2E8F0;
            text-align: center;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1E3A8A;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #64748B;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
        }

        .card-container {
            background: #FFFFFF;
            padding: 1.5rem;
            border-radius: 0.75rem;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
            margin-bottom: 1.5rem;
        }

        .stButton>button {
            background-color: #1E3A8A;
            color: white;
            font-weight: 600;
            border-radius: 0.5rem;
            padding: 0.5rem 1rem;
            border: none;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #0F172A;
            box-shadow: 0 4px 12px rgba(30, 58, 138, 0.2);
        }
    </style>
""",
    unsafe_allow_html=True,
)

# --- CONFIGURACIÓN Y PRECARGA DE LA BASE DE DATOS SQLITE ---
DB_NAME = "gabinete_iesp.db"
EXCEL_FILE = "LISTADO DE COMPAÑIA DE CADETES AÑO 2026 PARA D1.xlsx"


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  # 1. Tabla de Cadetes (Legajos)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS cadetes (
            id_legajo TEXT PRIMARY KEY,
            apellido_nombre TEXT NOT NULL,
            curso TEXT NOT NULL,
            dni TEXT,
            genero TEXT,
            fecha_nacimiento TEXT,
            observaciones TEXT
        )
    """)

  # 2. Primera Intervención
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS primera_intervencion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_legajo TEXT,
            fecha_hora TEXT,
            sintomas TEXT,
            presion TEXT,
            saturacion TEXT,
            derivacion TEXT,
            FOREIGN KEY(id_legajo) REFERENCES cadetes(id_legajo)
        )
    """)

  # 3. Notas Médicas y Reposos / Expedientes
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS notas_medicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_legajo TEXT,
            nro_expediente TEXT,
            medico TEXT,
            diagnostico TEXT,
            tipo_reposo TEXT,
            fecha_desde TEXT,
            fecha_hasta TEXT,
            medicamentos TEXT,
            estado_alta TEXT DEFAULT 'Pendiente',
            FOREIGN KEY(id_legajo) REFERENCES cadetes(id_legajo)
        )
    """)

  # 4. Exámenes Anuales y Periódicos
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS examenes_periodicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_legajo TEXT,
            anio TEXT,
            ddjj_enfermedades TEXT,
            visus TEXT,
            hemograma TEXT,
            orina TEXT,
            electrocardiograma TEXT,
            aptitud_fisica TEXT,
            toxicologico TEXT,
            beta_hcg TEXT,
            fecha_registro TEXT,
            FOREIGN KEY(id_legajo) REFERENCES cadetes(id_legajo)
        )
    """)

  # 5. Examen de Baja / Egreso
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS examen_baja (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_legajo TEXT,
            fecha_baja TEXT,
            motivo TEXT,
            estado_salud_egreso TEXT,
            observaciones_medicas TEXT,
            FOREIGN KEY(id_legajo) REFERENCES cadetes(id_legajo)
        )
    """)

  conn.commit()

  # PRECARGA AUTOMÁTICA DESDE EL EXCEL SI LA TABLA ESTÁ VACÍA O NECESITA ACTUALIZARSE
  if os.path.exists(EXCEL_FILE):
    try:
      df_excel = pd.read_excel(EXCEL_FILE, sheet_name="COMPAÑIA")
      for _, row in df_excel.iterrows():
        id_leg = str(row["CARGO"]).strip()  # Usamos el número de cargo/legajo
        ap_nom = f"{str(row['APELLIDO']).strip()}, {str(row['NOMBRES']).strip()}"
        curso = str(row["CURSO"]).strip()
        dni = str(row["DNI"]).strip()
        genero = "Masculino"  # Por defecto (configurable)
        f_nac = (
            str(row["FECHA DE NACIMIENTO"]).split(" ")[0]
            if pd.notna(row["FECHA DE NACIMIENTO"])
            else ""
        )
        obs = (
            f"Email: {row['EMAIL']} | Celular: {row['CELULAR']} | CUIL:"
            f" {row['CUIL']}"
        )

        cursor.execute(
            """INSERT OR IGNORE INTO cadetes (id_legajo, apellido_nombre, curso, dni, genero, fecha_nacimiento, observaciones)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (id_leg, ap_nom, curso, dni, genero, f_nac, obs),
        )
      conn.commit()
    except Exception as e:
      print(f"Error al precargar el Excel: {e}")

  conn.close()


init_db()


def obtener_cadetes():
  conn = sqlite3.connect(DB_NAME)
  df = pd.read_sql_query("SELECT * FROM cadetes", conn)
  conn.close()
  return df


# --- MENÚ LATERAL PRO ---
st.sidebar.image(
    "https://img.icons8.com/color/96/police-badge.png", width=70
)
st.sidebar.markdown("### I.E.S.P. G.J.F.S.M.")
st.sidebar.markdown(
    "<small style='color: #64748B;'>Dirección de Gabinete Interdisciplinario"
    " de Asesoramiento Psicopedagógico y Psicológico</small>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navegación Principal",
    [
        "Dashboard General",
        "Gestión de Legajos",
        "1. Primera Intervención",
        "2. Notas Médicas y Reposos",
        "3. Control de Alta",
        "4. Exámenes Periódicos y Anuales",
        "5. Historia Clínica Integral",
        "6. Examen de Baja / Egreso",
    ],
)


# ==========================================
# DASHBOARD GENERAL
# ==========================================
if menu == "Dashboard General":
  st.markdown(
      """
        <div class="pro-header">
            <p class="pro-title">🏥 Panel Médico del Gabinete I.E.S.P.</p>
            <p class="pro-subtitle">Sistema integral de seguimiento sanitario, historias clínicas y legajos de cadetes (1°, 2° y 3° Año).</p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  df_c = obtener_cadetes()
  conn = sqlite3.connect(DB_NAME)
  df_n = pd.read_sql_query("SELECT * FROM notas_medicas", conn)
  df_i = pd.read_sql_query("SELECT * FROM primera_intervencion", conn)
  conn.close()

  col1, col2, col3, col4 = st.columns(4)
  with col1:
    st.markdown(
        f"""
            <div class="metric-card">
                <div class="metric-value">{len(df_c)}</div>
                <div class="metric-label">Cadetes en Base</div>
            </div>
        """,
        unsafe_allow_html=True,
    )
  with col2:
    st.markdown(
        f"""
            <div class="metric-card">
                <div class="metric-value">{len(df_i)}</div>
                <div class="metric-label">Intervenciones</div>
            </div>
        """,
        unsafe_allow_html=True,
    )
  with col3:
    st.markdown(
        f"""
            <div class="metric-card">
                <div class="metric-value">{len(df_n)}</div>
                <div class="metric-label">Expedientes Médicos</div>
            </div>
        """,
        unsafe_allow_html=True,
    )
  with col4:
    pendientes_alta = (
        len(df_n[df_n["estado_alta"] == "Pendiente"]) if not df_n.empty else 0
    )
    st.markdown(
        f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #D97706;">{pendientes_alta}</div>
                <div class="metric-label">Altas Pendientes</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

  st.markdown("<br>", unsafe_allow_html=True)

  col_a, col_b = st.columns(2)
  with col_a:
    st.markdown(
        """
            <div class="card-container">
                <h3 style="color: #1E3A8A; margin-top: 0;">⚡ Base de Datos Precargada</h3>
                <p style="color: #475569;">El listado oficial de compañía de cadetes (1°, 2° y 3° año) se encuentra sincronizado con el archivo institucional. Puede consultar, editar o buscar cualquier cadete instantáneamente.</p>
            </div>
        """,
        unsafe_allow_html=True,
    )
  with col_b:
    st.markdown(
        """
            <div class="card-container">
                <h3 style="color: #1E3A8A; margin-top: 0;">🛡️ Instituto de Enseñanza Superior de Policía</h3>
                <p style="color: #475569;"><b>"Gral. José Francisco de San Martín"</b></p>
                <hr style="border: 0; border-top: 1px solid #E2E8F0;">
                <p style="font-size: 0.9rem; color: #64748B;">Dirección de Gabinete Interdisciplinario de Asesoramiento Psicopedagógico y Psicológico.</p>
            </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# MÓDULO 0: GESTIÓN DE LEGAJOS
# ==========================================
elif menu == "Gestión de Legajos":
  st.markdown(
      '<h2 style="color: #1E3A8A;">📁 Gestión y Legajos de Cadetes</h2>',
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748B;'>Listado oficial precargado y gestión de"
      " legajos institucionales.</p>",
      unsafe_allow_html=True,
  )

  tab1, tab2 = st.tabs(["🔍 Consultar / Listar Compañía", "➕ Registrar Nuevo"])

  with tab1:
    df_cadetes = obtener_cadetes()
    if not df_cadetes.empty:
      busqueda = st.text_input(
          "🔍 Búsqueda rápida por Apellido, Nombre o Número de Legajo/Cargo"
      )
      if busqueda:
        df_cadetes = df_cadetes[
            df_cadetes["apellido_nombre"]
            .str.contains(busqueda, case=False, na=False)
            | df_cadetes["id_legajo"]
            .str.contains(busqueda, case=False, na=False)
        ]
      st.dataframe(df_cadetes, use_container_width=True)
    else:
      st.warning(
          "⚠️ No se encontraron cadetes. Verifique que el archivo Excel de la"
          " compañía esté cargado en el repositorio."
      )

  with tab2:
    with st.form("form_nuevo_cadete"):
      col1, col2 = st.columns(2)
      with col1:
        id_legajo = st.text_input("Número de Legajo / Cargo*").strip()
        apellido_nombre = st.text_input("Apellido y Nombres*").strip()
        curso = st.selectbox("Curso", ["1 AÑO", "2 AÑO", "3 AÑO"])
      with col2:
        dni = st.text_input("DNI")
        genero = st.selectbox("Género", ["Masculino", "Femenino", "Otro"])
        fecha_nacimiento = st.date_input(
            "Fecha de Nacimiento", value=date(2000, 1, 1)
        )

      observaciones = st.text_area("Observaciones / Contacto / Antecedentes")
      submit_cadete = st.form_submit_button("Guardar Legajo")

      if submit_cadete:
        if id_legajo and apellido_nombre:
          try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO cadetes VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    id_legajo,
                    apellido_nombre,
                    curso,
                    dni,
                    genero,
                    str(fecha_nacimiento),
                    observaciones,
                ),
            )
            conn.commit()
            conn.close()
            st.success(f"✅ ¡Legajo {id_legajo} guardado con éxito!")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error(
                "❌ Error: El número de legajo ya se encuentra registrado."
            )
        else:
          st.warning("⚠️ Complete Legajo y Apellido y Nombres.")


# ==========================================
# MÓDULO 1: PRIMERA INTERVENCIÓN
# ==========================================
elif menu == "1. Primera Intervención":
  st.markdown(
      '<h2 style="color: #1E3A8A;">🩺 Primera Intervención en Gabinete</h2>',
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748B;'>Registro de síntomas, signos vitales y"
      " derivación clínica inicial.</p>",
      unsafe_allow_html=True,
  )

  df_cadetes = obtener_cadetes()
  if df_cadetes.empty:
    st.warning("⚠️ No hay cadetes en la base de datos.")
  else:
    lista_cadetes = (
        df_cadetes["id_legajo"] + " - " + df_cadetes["apellido_nombre"]
    ).tolist()
    seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
    id_legajo = seleccion.split(" - ")[0]

    with st.form("form_intervencion"):
      col1, col2 = st.columns(2)
      with col1:
        fecha_hora = st.text_input(
            "Fecha y Hora", value=str(datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        sintomas = st.text_area(
            "Síntomas / Motivo (Dolor de cabeza, lesiones, congestión, etc.)"
        )
      with col2:
        presion = st.text_input("Valores de Presión Arterial (Ej: 120/80)")
        saturacion = st.text_input("Saturación de Oxígeno (Ej: 98%)")
        derivacion = st.text_input("Derivación (Clínica / Especialista)")

      submit_int = st.form_submit_button("Registrar Primera Intervención")

      if submit_int:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO primera_intervencion (id_legajo, fecha_hora, sintomas, presion, saturacion, derivacion)
                       VALUES (?, ?, ?, ?, ?, ?)""",
            (
                id_legajo,
                fecha_hora,
                sintomas,
                presion,
                saturacion,
                derivacion,
            ),
        )
        conn.commit()
        conn.close()
        st.success("✅ ¡Primera intervención registrada con éxito!")

    st.markdown("### 📋 Historial de Intervenciones del Cadete")
    conn = sqlite3.connect(DB_NAME)
    df_ints = pd.read_sql_query(
        f"SELECT * FROM primera_intervencion WHERE id_legajo = '{id_legajo}'",
        conn,
    )
    conn.close()
    st.dataframe(df_ints, use_container_width=True)


# ==========================================
# MÓDULO 2: NOTAS MÉDICAS Y REPOSOS
# ==========================================
elif menu == "2. Notas Médicas y Reposos":
  st.markdown(
      '<h2 style="color: #1E3A8A;">📋 Registro de Notas Médicas y Expedientes</h2>',
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748B;'>Carga de nota médica de Detall, diagnósticos,"
      " tipos de reposo y medicamentos.</p>",
      unsafe_allow_html=True,
  )

  df_cadetes = obtener_cadetes()
  if df_cadetes.empty:
    st.warning("⚠️️ No hay cadetes en la base de datos.")
  else:
    lista_cadetes = (
        df_cadetes["id_legajo"] + " - " + df_cadetes["apellido_nombre"]
    ).tolist()
    seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
    id_legajo = seleccion.split(" - ")[0]

    with st.form("form_nota_medica"):
      col1, col2 = st.columns(2)
      with col1:
        nro_expediente = st.text_input("Número de Expediente (Ej: EXP-2026-XX)")
        medico = st.text_input("Médico Tratante / Matrícula")
        diagnostico = st.text_area("Diagnóstico Médico")
      with col2:
        tipo_reposo = st.selectbox(
            "Tipo de Reposo",
            [
                "Reposo Domiciliario",
                "Reposo Académico",
                "Internación",
                "ART",
            ],
        )
        fecha_desde = st.date_input(
            "Reposo Desde", value=datetime.today().date()
        )
        fecha_hasta = st.date_input(
            "Reposo Hasta", value=datetime.today().date()
        )
        medicamentos = st.text_input("Medicamentos Indicados")

      submit_nota = st.form_submit_button("Generar Expediente y Nota Médica")

      if submit_nota:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO notas_medicas (id_legajo, nro_expediente, medico, diagnostico, tipo_reposo, fecha_desde, fecha_hasta, medicamentos, estado_alta)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente')""",
            (
                id_legajo,
                nro_expediente,
                medico,
                diagnostico,
                tipo_reposo,
                str(fecha_desde),
                str(fecha_hasta),
                medicamentos,
            ),
        )
        conn.commit()
        conn.close()
        st.success(f"✅ ¡Expediente {nro_expediente} guardado con éxito!")

    st.markdown("### 📂 Expedientes y Notas Registradas")
    conn = sqlite3.connect(DB_NAME)
    df_notas = pd.read_sql_query(
        f"SELECT * FROM notas_medicas WHERE id_legajo = '{id_legajo}'", conn
    )
    conn.close()
    st.dataframe(df_notas, use_container_width=True)


# ==========================================
# MÓDULO 3: CONTROL DE ALTA
# ==========================================
elif menu == "3. Control de Alta":
  st.markdown(
      '<h2 style="color: #1E3A8A;">✅ Control y Convalidación de Alta Médica</h2>',
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748B;'>Evaluación del cadete tras los días de reposo"
      " y convalidación de alta o prórroga.</p>",
      unsafe_allow_html=True,
  )

  conn = sqlite3.connect(DB_NAME)
  df_pendientes = pd.read_sql_query(
      "SELECT * FROM notas_medicas WHERE estado_alta = 'Pendiente'", conn
  )
  conn.close()

  if df_pendientes.empty:
    st.info("ℹ️ No hay notas médicas pendientes de alta en este momento.")
  else:
    st.dataframe(df_pendientes, use_container_width=True)
    exp_id = st.selectbox(
        "Seleccione el ID de la Nota / Expediente a Evaluar",
        df_pendientes["id"].tolist(),
    )

    row_sel = df_pendientes[df_pendientes["id"] == exp_id].iloc[0]
    st.markdown(
        f"**Legajo:** {row_sel['id_legajo']} | **Diagnóstico:**"
        f" {row_sel['diagnostico']}"
    )

    decision = st.radio(
        "Dictamen del Gabinete:",
        ["Convalidar Alta", "Otorgar Prórroga de Reposo"],
    )

    if decision == "Convalidar Alta":
      if st.button("Confirmar Alta Médica"):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notas_medicas SET estado_alta = 'Alta Convalidada' WHERE id"
            " = ?",
            (exp_id,),
        )
        conn.commit()
        conn.close()
        st.success("✅ ¡Alta médica convalidada con éxito!")
        st.rerun()
    else:
      nueva_fecha_hasta = st.date_input("Nueva Fecha de Fin de Reposo")
      nueva_indicacion = st.text_input("Motivo / Nuevos Medicamentos")
      if st.button("Registrar Prórroga"):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notas_medicas SET fecha_hasta = ?, medicamentos = ?,"
            " estado_alta = 'Prórroga Otorgada' WHERE id = ?",
            (str(nueva_fecha_hasta), nueva_indicacion, exp_id),
        )
        conn.commit()
        conn.close()
        st.warning("⚠️ ¡Prórroga de reposo registrada correctamente!")
        st.rerun()


# ==========================================
# MÓDULO 4: EXÁMENES PERIÓDICOS Y ANUALES
# ==========================================
elif menu == "4. Exámenes Periódicos y Anuales":
  st.markdown(
      '<h2 style="color: #1E3A8A;">🧪 Exámenes Periódicos y Anuales</h2>',
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748B;'>Control de DDJJ de enfermedades, Visus,"
      " Laboratorio, Electrocardiograma, Toxicológico y Beta HCG"
      " trimestral.</p>",
      unsafe_allow_html=True,
  )

  df_cadetes = obtener_cadetes()
  if df_cadetes.empty:
    st.warning("⚠️ No hay cadetes.")
  else:
    lista_cadetes = (
        df_cadetes["id_legajo"] + " - " + df_cadetes["apellido_nombre"]
    ).tolist()
    seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
    id_legajo = seleccion.split(" - ")[0]

    cadete_info = df_cadetes[df_cadetes["id_legajo"] == id_legajo].iloc[0]
    es_femenino = cadete_info["genero"] == "Femenino"

    with st.form("form_examenes"):
      anio_eval = st.text_input("Año de Evaluación", "2026")

      col1, col2 = st.columns(2)
      with col1:
        ddjj = st.selectbox(
            "Declaración Jurada de Enfermedades",
            ["Aprobada / Sin Novedad", "Con Observaciones"],
        )
        visus = st.text_input("Examen de Visus (Agudeza Visual)")
        hemograma = st.selectbox(
            "Hemograma", ["Normal", "Alterado", "Pendiente"]
        )
        orina = st.selectbox("Examen de Orina", ["Normal", "Alterado", "Pendiente"])
      with col2:
        electro = st.selectbox(
            "Electrocardiograma", ["Normal", "Con Patología", "Pendiente"]
        )
        aptitud = st.selectbox(
            "Certificado de Aptitud Física", ["Apto", "No Apto"]
        )
        toxicologico = st.selectbox(
            "Examen Toxicológico", ["Negativo", "Positivo", "Pendiente"]
        )

        beta_hcg = "N/A (Masculino)"
        if es_femenino:
          beta_hcg = st.selectbox(
              "Examen Beta HCG (Embarazo - Trimestral)",
              ["Negativo", "Positivo", "No Realizado"],
          )

      submit_ex = st.form_submit_button("Guardar Exámenes Periódicos")

      if submit_ex:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO examenes_periodicos (id_legajo, anio, ddjj_enfermedades, visus, hemograma, orina, electrocardiograma, aptitud_fisica, toxicologico, beta_hcg, fecha_registro)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                id_legajo,
                anio_eval,
                ddjj,
                visus,
                hemograma,
                orina,
                electro,
                aptitud,
                toxicologico,
                beta_hcg,
                str(datetime.today()),
            ),
        )
        conn.commit()
        conn.close()
        st.success("✅ ¡Exámenes guardados con éxito!")

    st.markdown("### 📊 Historial de Exámenes del Cadete")
    conn = sqlite3.connect(DB_NAME)
    df_ex = pd.read_sql_query(
        f"SELECT * FROM examenes_periodicos WHERE id_legajo = '{id_legajo}'",
        conn,
    )
    conn.close()
    st.dataframe(df_ex, use_container_width=True)


# ==========================================
# MÓDULO 5: HISTORIA CLÍNICA INTEGRAL
# ==========================================
elif menu == "5. Historia Clínica Integral":
  st.markdown(
      '<h2 style="color: #1E3A8A;">📈 Historia Clínica y Legajo Sanitario'
      " Integral</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748B;'>Resumen cronológico de patologías, notas"
      " médicas y días de reposo durante los 3 años.</p>",
      unsafe_allow_html=True,
  )

  df_cadetes = obtener_cadetes()
  if df_cadetes.empty:
    st.warning("⚠️ No hay cadetes.")
  else:
    lista_cadetes = (
        df_cadetes["id_legajo"] + " - " + df_cadetes["apellido_nombre"]
    ).tolist()
    seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
    id_legajo = seleccion.split(" - ")[0]

    cadete = df_cadetes[df_cadetes["id_legajo"] == id_legajo].iloc[0]
    st.info(
        f"📌 **Cadete:** {cadete['apellido_nombre']} | **Legajo/Cargo:**"
        f" {cadete['id_legajo']} | **Curso:** {cadete['curso']}"
    )

    conn = sqlite3.connect(DB_NAME)
    df_nm = pd.read_sql_query(
        f"SELECT nro_expediente, medico, diagnostico, tipo_reposo, fecha_desde, fecha_hasta, medicamentos, estado_alta FROM notas_medicas WHERE id_legajo = '{id_legajo}'",
        conn,
    )
    df_int = pd.read_sql_query(
        f"SELECT fecha_hora, sintomas, presion, saturacion, derivacion FROM primera_intervencion WHERE id_legajo = '{id_legajo}'",
        conn,
    )
    conn.close()

    st.markdown("### 📋 Notas Médicas y Reposos")
    if not df_nm.empty:
      st.dataframe(df_nm, use_container_width=True)
    else:
      st.write("No registra notas médicas ni días de reposo.")

    st.markdown("### 🩺 Primera Intervención en Gabinete")
    if not df_int.empty:
      st.dataframe(df_int, use_container_width=True)
    else:
      st.write("No registra primeras intervenciones.")


# ==========================================
# MÓDULO 6: EXAMEN DE BAJA / EGRESO
# ==========================================
elif menu == "6. Examen de Baja / Egreso":
  st.markdown(
      '<h2 style="color: #1E3A8A;">🚪 Examen Médico de Baja / Egreso</h2>',
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748B;'>Registro de parámetros de salud y estado"
      " general al momento de la baja o egreso institucional.</p>",
      unsafe_allow_html=True,
  )

  df_cadetes = obtener_cadetes()
  if df_cadetes.empty:
    st.warning("⚠️ No hay cadetes.")
  else:
    lista_cadetes = (
        df_cadetes["id_legajo"] + " - " + df_cadetes["apellido_nombre"]
    ).tolist()
    seleccion = st.selectbox("Seleccionar Cadete", lista_cadetes)
    id_legajo = seleccion.split(" - ")[0]

    with st.form("form_baja"):
      fecha_baja = st.date_input("Fecha de Baja", value=datetime.today().date())
      motivo = st.selectbox(
          "Motivo de Baja",
          ["Egreso / Graduación", "Baja Voluntaria", "Baja Médica", "Otra"],
      )
      estado_salud_egreso = st.text_area(
          "Parámetros y Estado General de Salud al Egreso"
      )
      observaciones_medicas = st.text_area(
          "Observaciones / Cierre Definitivo de Historia Clínica"
      )

      submit_baja = st.form_submit_button("Guardar Examen de Baja")

      if submit_baja:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO examen_baja (id_legajo, fecha_baja, motivo, estado_salud_egreso, observaciones_medicas)
                       VALUES (?, ?, ?, ?, ?)""",
            (
                id_legajo,
                str(fecha_baja),
                motivo,
                estado_salud_egreso,
                observaciones_medicas,
            ),
        )
        conn.commit()
        conn.close()
        st.success("✅ ¡Examen de baja registrado con éxito!")

    st.markdown("### 📊 Historial de Egreso / Baja")
    conn = sqlite3.connect(DB_NAME)
    df_baja = pd.read_sql_query(
        f"SELECT * FROM examen_baja WHERE id_legajo = '{id_legajo}'", conn
    )
    conn.close()
    st.dataframe(df_baja, use_container_width=True)
