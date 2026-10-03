from datetime import datetime, date
import os
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Gabinete Médico | I.E.S.P. G.J.F.S.M.",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- DISEÑO UI/UX DE NIVEL CLÍNICO INTERNACIONAL (MODO OSCURO PRO) ---
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #030712;
        color: #F3F4F6;
    }
    
    /* Sidebar Estilo SaaS Médico */
    [data-testid="stSidebar"] {
        background-color: #0B0F19;
        border-right: 1px solid #1F2937;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #9CA3AF;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        color: #38BDF8;
    }

    /* Encabezado Pro */
    .pro-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 100%);
        padding: 2.5rem;
        border-radius: 1.25rem;
        border: 1px solid #312E81;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
    }
    .pro-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF;
        letter-spacing: -0.03em;
    }
    .pro-subtitle {
        font-size: 1.1rem;
        color: #93C5FD;
        margin-top: 0.5rem;
        margin-bottom: 0;
        font-weight: 400;
    }

    /* Tarjetas de Métricas (KPI Cards) */
    .metric-card {
        background: #111827;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        border: 1px solid #1F2937;
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        border-color: #3B82F6;
        transform: translateY(-3px);
        box-shadow: 0 15px 20px -3px rgba(59, 130, 246, 0.15);
    }
    .metric-value {
        font-size: 2.3rem;
        font-weight: 800;
        color: #38BDF8;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #9CA3AF;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.05em;
        margin-top: 0.35rem;
    }

    /* Tarjeta de Perfil / Ficha */
    .profile-card {
        background: #111827;
        padding: 1.75rem;
        border-radius: 1rem;
        border: 1px solid #1F2937;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        margin-bottom: 1.5rem;
    }

    /* Alertas Médicas */
    .alert-card {
        background: rgba(120, 53, 15, 0.4);
        border: 1px solid #B45309;
        padding: 1.25rem;
        border-radius: 0.85rem;
        margin-bottom: 1rem;
        color: #FEF3C7;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }

    /* Badges */
    .badge-active {
        background-color: rgba(6, 95, 70, 0.6);
        color: #34D399;
        border: 1px solid #059669;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    /* Formularios e Inputs estilizados */
    .stTextInput input, .stSelectbox select, .stTextArea textarea, .stDateInput input {
        background-color: #111827 !important;
        color: #FFFFFF !important;
        border: 1px solid #374151 !important;
        border-radius: 0.75rem !important;
        padding: 0.5rem 0.75rem !important;
    }
    .stTextInput input:focus, .stSelectbox select:focus, .stTextArea textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
    }

    /* Botones Pro */
    .stButton>button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        font-weight: 700;
        border-radius: 0.75rem;
        padding: 0.65rem 1.5rem;
        border: none;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.5);
        transform: translateY(-1px);
    }

    /* Pestañas de Streamlit */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0B0F19;
        padding: 6px;
        border-radius: 0.85rem;
        border: 1px solid #1F2937;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 0.5rem;
        color: #9CA3AF;
        font-weight: 600;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E293B !important;
        color: #38BDF8 !important;
    }
</style>
""", unsafe_allow_html=True)

DB_NAME = "gabinete_iesp.db"
EXCEL_FILE = "LISTADO DE COMPAÑIA DE CADETES AÑO 2026 PARA D1.xlsx"


def importar_excel_directo():
  if not os.path.exists(EXCEL_FILE):
    return False, f"No se encontró el archivo Excel: {EXCEL_FILE}"
  try:
    df_excel = pd.read_excel(EXCEL_FILE, sheet_name=0)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cargados = 0
    for _, row in df_excel.iterrows():
      if pd.isna(row.get('APELLIDO')) or pd.isna(row.get('NOMBRES')):
        continue
      id_leg = str(row.get('CARGO', row.get('N°', 'S/N'))).strip()
      ap_nom = (
          f"{str(row.get('APELLIDO', '')).strip()},"
          f" {str(row.get('NOMBRES', '')).strip()}"
      )
      curso = str(row.get('CURSO', '1 AÑO')).strip()
      dni = str(row.get('DNI', '')).strip()
      genero = 'Masculino'
      f_nac = (
          str(row.get('FECHA DE NACIMIENTO', '')).split(' ')[0]
          if pd.notna(row.get('FECHA DE NACIMIENTO'))
          else ''
      )
      obs = (
          f"Email: {row.get('EMAIL', '')} | Celular: {row.get('CELULAR', '')}"
          f" | CUIL: {row.get('CUIL', '')}"
      )
      cursor.execute(
          'INSERT OR IGNORE INTO cadetes (id_legajo, apellido_nombre, curso,'
          ' dni, genero, fecha_nacimiento, observaciones) VALUES (?, ?, ?, ?,'
          ' ?, ?, ?)',
          (id_leg, ap_nom, curso, dni, genero, f_nac, obs),
      )
      cargados += 1
    conn.commit()
    conn.close()
    return True, f'Se sincronizaron {cargados} cadetes correctamente.'
  except Exception as e:
    return False, f'Error al procesar el Excel: {str(e)}'


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      'CREATE TABLE IF NOT EXISTS cadetes (id_legajo TEXT PRIMARY KEY,'
      ' apellido_nombre TEXT NOT NULL, curso TEXT NOT NULL, dni TEXT, genero'
      ' TEXT, fecha_nacimiento TEXT, observaciones TEXT)'
  )
  cursor.execute(
      'CREATE TABLE IF NOT EXISTS personal_gabinete (id_legajo_personal TEXT'
      ' PRIMARY KEY, apellido_nombre TEXT NOT NULL, dni TEXT, matricula TEXT,'
      ' especialidad TEXT, telefono TEXT)'
  )
  cursor.execute(
      'CREATE TABLE IF NOT EXISTS primera_intervencion (id INTEGER PRIMARY KEY'
      ' AUTOINCREMENT, id_legajo TEXT, fecha_hora TEXT, profesional_atiende'
      ' TEXT, sintomas TEXT, presion TEXT, saturacion TEXT, derivacion TEXT)'
  )
  cursor.execute(
      'CREATE TABLE IF NOT EXISTS notas_medicas (id INTEGER PRIMARY KEY'
      ' AUTOINCREMENT, id_legajo TEXT, nro_expediente TEXT, medico TEXT,'
      " diagnostico TEXT, tipo_reposo TEXT, fecha_desde TEXT, fecha_hasta TEXT,"
      " medicamentos TEXT, estado_alta TEXT DEFAULT 'Pendiente')"
  )
  cursor.execute(
      'CREATE TABLE IF NOT EXISTS examenes_periodicos (id INTEGER PRIMARY KEY'
      ' AUTOINCREMENT, id_legajo TEXT, anio TEXT, ddjj_enfermedades TEXT, visus'
      ' TEXT, hemograma TEXT, orina TEXT, electrocardiograma TEXT,'
      ' aptitud_fisica TEXT, toxicologico TEXT, beta_hcg TEXT, fecha_registro'
      ' TEXT)'
  )
  cursor.execute(
      'CREATE TABLE IF NOT EXISTS examen_baja (id INTEGER PRIMARY KEY'
      ' AUTOINCREMENT, id_legajo TEXT, fecha_baja TEXT, motivo TEXT,'
      ' estado_salud_egreso TEXT, observaciones_medicas TEXT)'
  )
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


# --- NAVEGACIÓN LATERAL PRO ---
st.sidebar.image('https://img.icons8.com/color/96/police-badge.png', width=75)
st.sidebar.markdown('### I.E.S.P. G.J.F.S.M.')
st.sidebar.markdown(
    "<small style='color: #94A3B8;'>Dirección de Gabinete Médico e"
    ' Interdisciplinario</small>',
    unsafe_allow_html=True,
)
st.sidebar.markdown('---')

menu = st.sidebar.radio(
    'Navegación Principal',
    [
        'Dashboard General',
        'Gestión de Legajos',
        'Personal del Gabinete',
        '1. Primera Intervención',
        '2. Notas Médicas y Reposos',
        '3. Control de Alta',
        '4. Exámenes Periódicos y Anuales',
        '5. Historia Clínica Integral',
        '6. Examen de Baja / Egreso',
        '7. Informes y Análisis de Datos (Spark)',
    ],
)

if menu == 'Dashboard General':
  st.markdown(
      '<div class="pro-header"><p class="pro-title">🏥 Centro Médico y'
      ' Gabinete I.E.S.P.</p><p class="pro-subtitle">Sistema integral de'
      ' gestión sanitaria, control de guardia y legajos institucionales de'
      ' cadetes.</p></div>',
      unsafe_allow_html=True,
  )

  df_c = obtener_cadetes()
  df_p = obtener_personal()
  conn = sqlite3.connect(DB_NAME)
  df_n = pd.read_sql_query(
      'SELECT n.*, c.apellido_nombre, c.curso FROM notas_medicas n LEFT JOIN'
      ' cadetes c ON n.id_legajo = c.id_legajo',
      conn,
  )
  df_e = pd.read_sql_query(
      'SELECT e.*, c.apellido_nombre, c.curso, c.genero FROM examenes_periodicos'
      ' e LEFT JOIN cadetes c ON e.id_legajo = c.id_legajo',
      conn,
  )
  df_i = pd.read_sql_query(
      'SELECT i.*, c.apellido_nombre, c.curso FROM primera_intervencion i LEFT'
      ' JOIN cadetes c ON i.id_legajo = c.id_legajo',
      conn,
  )
  conn.close()

  col1, col2, col3, col4 = st.columns(4)
  with col1:
    st.markdown(
        f'<div class="metric-card"><div'
        f' class="metric-value">{len(df_c)}</div><div'
        ' class="metric-label">Cadetes en Compañía</div></div>',
        unsafe_allow_html=True,
    )
  with col2:
    st.markdown(
        f'<div class="metric-card"><div'
        f' class="metric-value">{len(df_i)}</div><div'
        ' class="metric-label">Intervenciones Guardia</div></div>',
        unsafe_allow_html=True,
    )
  with col3:
    st.markdown(
        f'<div class="metric-card"><div'
        f' class="metric-value">{len(df_p)}</div><div'
        ' class="metric-label">Staff Gabinete Activo</div></div>',
        unsafe_allow_html=True,
    )
  with col4:
    pendientes_alta = (
        len(df_n[df_n['estado_alta'] == 'Pendiente']) if not df_n.empty else 0
    )
    st.markdown(
        f'<div class="metric-card"><div class="metric-value" style="color:'
        f' #FBBF24;">{pendientes_alta}</div><div class="metric-label">Altas'
        ' Pendientes</div></div>',
        unsafe_allow_html=True,
    )

  st.markdown('<br>', unsafe_allow_html=True)

  dash_tab1, dash_tab2, dash_tab3 = st.tabs([
      '🚨 Centro de Alertas y Vencimientos',
      '📋 Consulta General de Compañía',
      '⚡ Acciones Rápidas y Sincronización',
  ])

  with dash_tab1:
    st.markdown('### 🚨 Alertas Clínicas y Control de Vencimientos')
    hoy = datetime.today().date()
    if not df_n.empty:
      pendientes = df_n[df_n['estado_alta'] == 'Pendiente'].copy()
      if not pendientes.empty:
        for _, row in pendientes.iterrows():
          f_hasta = (
              pd.to_datetime(row['fecha_hasta']).date()
              if pd.notna(row['fecha_hasta'])
              else hoy
          )
          dias_dif = (hoy - f_hasta).days
          if dias_dif > 0:
            st.markdown(
                f'<div class="alert-card"><b>⚠️ EXPEDIENTE VENCIDO / ALTA'
                f' VENCIDA:</b> El cadete <b>{row["apellido_nombre"]}</b>'
                f' (Curso: {row["curso"]}, Legajo: {row["id_legajo"]}) tiene'
                f' un reposo ({row["tipo_reposo"]}) finalizado el'
                f' <b>{row["fecha_hasta"]}</b> (hace {dias_dif} días) sin'
                ' convalidación de alta.</div>',
                unsafe_allow_html=True,
            )
          else:
            st.markdown(
                f'<div class="profile-card" style="border-left: 4px solid'
                f' #FBBF24; padding: 1rem; margin-bottom: 0.75rem;"><b>⏳ Reposo'
                f' Activo:</b> Cadete <b>{row["apellido_nombre"]}</b> | Vence:'
                f' <b>{row["fecha_hasta"]}</b></div>',
                unsafe_allow_html=True,
            )
      else:
        st.success('✅ No hay notas médicas pendientes de alta en este momento.')

    if not df_e.empty:
      femeninos_ex = df_e[df_e['genero'] == 'Femenino'].copy()
      if not femeninos_ex.empty:
        for _, row in femeninos_ex.iterrows():
          f_reg = (
              pd.to_datetime(row['fecha_registro']).date()
              if pd.notna(row['fecha_registro'])
              else hoy
          )
          dias_beta = (hoy - f_reg).days
          if dias_beta > 90:
            st.markdown(
                f'<div class="alert-card"><b>⚠️ VENCIMIENTO ANÁLISIS DE'
                ' GONADOTROPINA CORIÓNICA HUMANA (BETA HCG):</b> La cadete'
                f' <b>{row["apellido_nombre"]}</b> (Curso: {row["curso"]})'
                ' supera los 3 meses desde su último control trimestral.</div>',
                unsafe_allow_html=True,
            )

  with dash_tab2:
    st.markdown('### 👥 Consulta Rápida de Compañía de Cadetes')
    if not df_c.empty:
      busq_dash = st.text_input(
          '🔍 Filtrar por Apellido, Nombre o Número de Legajo en el Dashboard'
      )
      df_c_view = df_c.copy()
      if busq_dash:
        df_c_view = df_c_view[
            df_c_view['apellido_nombre']
            .str.contains(busq_dash, case=False, na=False)
            | df_c_view['id_legajo']
            .astype(str)
            .str.contains(busq_dash, case=False, na=False)
        ]
      st.dataframe(df_c_view, use_container_width=True)

  with dash_tab3:
    st.markdown('### ⚙️ Administración e Institución')
    if st.button('Sincronizar Base de Cadetes Ahora'):
      exito, msg = importar_excel_directo()
      if exito:
        st.success(msg)
        st.rerun()
      else:
        st.error(msg)

elif menu == 'Gestión de Legajos':
  st.markdown(
      '<h2 style="color: #FFFFFF;">📁 Gestión de Legajos de Cadetes</h2>',
      unsafe_allow_html=True,
  )
  tab1, tab2 = st.tabs(['🔍 Consultar / Listar Compañía', '➕ Registrar Nuevo'])
  with tab1:
    if st.button('🔄 Recargar Base'):
      ex, ms = importar_excel_directo()
      if ex:
        st.success(ms)
        st.rerun()
    df_cadetes = obtener_cadetes()
    if not df_cadetes.empty:
      busqueda = st.text_input(
          '🔍 Búsqueda rápida por Apellido, Nombre o Número de Legajo/Cargo'
      )
      if busqueda:
        df_cadetes = df_cadetes[
            df_cadetes['apellido_nombre']
            .str.contains(busqueda, case=False, na=False)
            | df_cadetes['id_legajo']
            .astype(str)
            .str.contains(busqueda, case=False, na=False)
        ]
      st.dataframe(df_cadetes, use_container_width=True)
    else:
      st.warning('No hay cadetes en la base.')
  with tab2:
    with st.form('form_nuevo_cadete'):
      col1, col2 = st.columns(2)
      with col1:
        id_legajo = st.text_input('Número de Legajo / Cargo*').strip()
        apellido_nombre = st.text_input('Apellido y Nombres*').strip()
        curso = st.selectbox('Curso', ['1 AÑO', '2 AÑO', '3 AÑO'])
      with col2:
        dni = st.text_input('DNI')
        genero = st.selectbox('Género', ['Masculino', 'Femenino', 'Otro'])
        fecha_nacimiento = st.date_input(
            'Fecha de Nacimiento', value=date(2000, 1, 1)
        )
      observaciones = st.text_area('Observaciones / Contacto / Antecedentes')
      if st.form_submit_button('Guardar Legajo'):
        if id_legajo and apellido_nombre:
          try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO cadetes VALUES (?, ?, ?, ?, ?, ?, ?)',
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
            st.success(f'¡Legajo {id_legajo} guardado con éxito!')
            st.rerun()
          except sqlite3.IntegrityError:
            st.error('Error: El número de legajo ya existe.')
        else:
          st.warning('Complete Legajo y Apellido y Nombres.')

elif menu == 'Personal del Gabinete':
  st.markdown(
      '<h2 style="color: #FFFFFF;">👥 Staff Médico y Personal del'
      ' Gabinete</h2>',
      unsafe_allow_html=True,
  )
  tab_p1, tab_p2 = st.tabs(['📋 Listado de Staff', '➕ Alta / Baja de Personal'])
  with tab_p1:
    df_personal = obtener_personal()
    if not df_personal.empty:
      st.dataframe(df_personal, use_container_width=True)
    else:
      st.info('No hay personal del gabinete registrado todavía.')
  with tab_p2:
    with st.form('form_personal'):
      col1, col2 = st.columns(2)
      with col1:
        leg_pers = st.text_input('Número de Legajo / ID Personal*').strip()
        ap_nom_pers = st.text_input('Apellido y Nombres*').strip()
        dni_pers = st.text_input('DNI').strip()
      with col2:
        mat_pers = st.text_input('Matrícula Profesional*').strip()
        esp_pers = st.selectbox(
            'Especialidad',
            [
                'Médico/a Clínico/a',
                'Psicólogo/a',
                'Psicopedagogo/a',
                'Psiquiatra',
                'Enfermero/a',
                'Administrativo/a',
                'Otro',
            ],
        )
        tel_pers = st.text_input('Teléfono de Contacto').strip()
      if st.form_submit_button('Registrar Profesional'):
        if leg_pers and ap_nom_pers and mat_pers:
          try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO personal_gabinete VALUES (?, ?, ?, ?, ?, ?)',
                (
                    leg_pers,
                    ap_nom_pers,
                    dni_pers,
                    mat_pers,
                    esp_pers,
                    tel_pers,
                ),
            )
            conn.commit()
            conn.close()
            st.success(f'¡Profesional {ap_nom_pers} registrado con éxito!')
            st.rerun()
          except sqlite3.IntegrityError:
            st.error('Error: El número de legajo ya existe.')
        else:
          st.warning('Complete los campos obligatorios (*).')
    st.markdown('---')
    st.markdown('### 🗑️ Baja de Personal')
    df_pers_del = obtener_personal()
    if not df_pers_del.empty:
      lista_del = (
          df_pers_del['id_legajo_personal'].astype(str)
          + ' - '
          + df_pers_del['apellido_nombre']
          + ' ('
          + df_pers_del['especialidad']
          + ')'
      ).tolist()
      sel_del = st.selectbox(
          'Seleccione el Profesional a Dar de Baja', lista_del
      )
      if st.button('Confirmar Baja'):
        id_elim = sel_del.split(' - ')[0]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM personal_gabinete WHERE id_legajo_personal = ?',
            (id_elim,),
        )
        conn.commit()
        conn.close()
        st.success('¡Personal dado de baja correctamente!')
        st.rerun()

elif menu == '1. Primera Intervención':
  st.markdown(
      '<h2 style="color: #FFFFFF;">🩺 Primera Intervención en Gabinete</h2>',
      unsafe_allow_html=True,
  )
  df_cadetes = obtener_cadetes()
  df_personal = obtener_personal()
  if df_cadetes.empty:
    st.warning('No hay cadetes en la base.')
  else:
    lista_cadetes = (
        df_cadetes['id_legajo'].astype(str)
        + ' - '
        + df_cadetes['apellido_nombre']
    ).tolist()
    seleccion = st.selectbox('Seleccionar Cadete', lista_cadetes)
    id_legajo = seleccion.split(' - ')[0]
    cad_sel = df_cadetes[df_cadetes['id_legajo'].astype(str) == id_legajo].iloc[
        0
    ]

    st.markdown(
        f'<div class="profile-card"><h3 style="margin: 0; color:'
        f' #FFFFFF;">{cad_sel["apellido_nombre"]}</h3><p style="margin:'
        f' 0.25rem 0 0 0; color: #94A3B8;">Legajo:'
        f' <b>{cad_sel["id_legajo"]}</b> | Curso: <b>{cad_sel["curso"]}</b> |'
        f' DNI: <b>{cad_sel["dni"]}</b></p></div>',
        unsafe_allow_html=True,
    )

    lista_profesionales = (
        df_personal['apellido_nombre'].tolist()
        if not df_personal.empty
        else ['Sin personal registrado']
    )

    with st.form('form_intervencion'):
      col1, col2 = st.columns(2)
      with col1:
        fecha_hora = st.text_input(
            'Fecha y Hora',
            value=str(datetime.now().strftime('%Y-%m-%d %H:%M')),
        )
        profesional_atiende = st.selectbox(
            'Profesional que Atiende*', lista_profesionales
        )
        sintomas = st.text_area('Síntomas / Motivo*')
      with col2:
        presion = st.text_input('Presión Arterial')
        saturacion = st.text_input('Saturación O2')
        derivacion = st.selectbox(
            'Derivación / Especialista*',
            [
                'Clínica Central',
                'Traumatología',
                'Cardiología',
                'Psicología',
                'Oftalmología',
                'Odontología',
                'Otro',
            ],
        )
        derivacion_detalles = st.text_input('Detalles específicos')
      if st.form_submit_button('Registrar Intervención'):
        if profesional_atiende and sintomas and derivacion:
          derivacion_final = (
              f'{derivacion} - {derivacion_detalles}'
              if derivacion_detalles
              else derivacion
          )
          conn = sqlite3.connect(DB_NAME)
          cursor = conn.cursor()
          cursor.execute(
              'INSERT INTO primera_intervencion (id_legajo, fecha_hora,'
              ' profesional_atiende, sintomas, presion, saturacion, derivacion)'
              ' VALUES (?, ?, ?, ?, ?, ?, ?)',
              (
                  id_legajo,
                  fecha_hora,
                  profesional_atiende,
                  sintomas,
                  presion,
                  saturacion,
                  derivacion_final,
              ),
          )
          conn.commit()
          conn.close()
          st.success('¡Intervención registrada con éxito!')
          st.rerun()
        else:
          st.warning('Complete los campos obligatorios (*).')
  st.markdown('### 📊 Historial de Guardia')
  conn = sqlite3.connect(DB_NAME)
  df_ints = pd.read_sql_query(
      f"SELECT * FROM primera_intervencion WHERE id_legajo = '{id_legajo}'",
      conn,
  )
  conn.close()
  if not df_ints.empty:
    st.dataframe(df_ints, use_container_width=True)

elif menu == '2. Notas Médicas y Reposos':
  st.markdown(
      '<h2 style="color: #FFFFFF;">📋 Registro de Notas Médicas y Reposos</h2>',
      unsafe_allow_html=True,
  )
  df_cadetes = obtener_cadetes()
  if not df_cadetes.empty:
    lista_cadetes = (
        df_cadetes['id_legajo'].astype(str)
        + ' - '
        + df_cadetes['apellido_nombre']
    ).tolist()
    seleccion = st.selectbox('Seleccionar Cadete', lista_cadetes)
    id_legajo = seleccion.split(' - ')[0]
    with st.form('form_nota_medica'):
      col1, col2 = st.columns(2)
      with col1:
        nro_expediente = st.text_input('Número de Expediente*')
        medico = st.text_input('Médico / Matrícula*')
        diagnostico = st.text_area('Diagnóstico*')
      with col2:
        tipo_reposo = st.selectbox(
            'Tipo de Reposo',
            ['Domiciliario', 'Académico', 'Internación', 'ART'],
        )
        fecha_desde = st.date_input('Desde', value=datetime.today().date())
        fecha_hasta = st.date_input('Hasta', value=datetime.today().date())
        medicamentos = st.text_input('Medicamentos')
      if st.form_submit_button('Guardar Nota Médica'):
        if nro_expediente and medico and diagnostico:
          conn = sqlite3.connect(DB_NAME)
          cursor = conn.cursor()
          cursor.execute(
              'INSERT INTO notas_medicas (id_legajo, nro_expediente, medico,'
              ' diagnostico, tipo_reposo, fecha_desde, fecha_hasta,'
              ' medicamentos, estado_alta) VALUES (?, ?, ?, ?, ?, ?, ?, ?,'
              " 'Pendiente')",
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
          st.success('¡Nota médica guardada con éxito!')

elif menu == '3. Control de Alta':
  st.markdown(
      '<h2 style="color: #FFFFFF;">✅ Control de Alta Médica</h2>',
      unsafe_allow_html=True,
  )
  conn = sqlite3.connect(DB_NAME)
  df_pendientes = pd.read_sql_query(
      "SELECT * FROM notas_medicas WHERE estado_alta = 'Pendiente'", conn
  )
  conn.close()
  if not df_pendientes.empty:
    st.dataframe(df_pendientes, use_container_width=True)
    exp_id = st.selectbox('ID Nota', df_pendientes['id'].tolist())
    if st.button('Convalidar Alta'):
      conn = sqlite3.connect(DB_NAME)
      cursor = conn.cursor()
      cursor.execute(
          "UPDATE notas_medicas SET estado_alta = 'Alta Convalidada' WHERE id ="
          ' ?',
          (exp_id,),
      )
      conn.commit()
      conn.close()
      st.success('¡Alta convalidada con éxito!')
      st.rerun()
  else:
    st.info('Sin notas pendientes de alta.')

elif menu == '4. Exámenes Periódicos y Anuales':
  st.markdown(
      '<h2 style="color: #FFFFFF;">🧪 Exámenes Periódicos y Anuales</h2>',
      unsafe_allow_html=True,
  )
  df_cadetes = obtener_cadetes()
  if not df_cadetes.empty:
    lista_cadetes = (
        df_cadetes['id_legajo'].astype(str)
        + ' - '
        + df_cadetes['apellido_nombre']
    ).tolist()
    seleccion = st.selectbox('Seleccionar Cadete', lista_cadetes)
    id_legajo = seleccion.split(' - ')[0]
    cadete_info = df_cadetes[
        df_cadetes['id_legajo'].astype(str) == id_legajo
    ].iloc[0]
    es_femenino = cadete_info['genero'] == 'Femenino'
    with st.form('form_examenes'):
      col1, col2 = st.columns(2)
      with col1:
        ddjj = st.selectbox('DDJJ', ['Aprobada', 'Observada'])
        visus = st.text_input('Visus')
        hemograma = st.selectbox('Hemograma', ['Normal', 'Alterado'])
      with col2:
        electro = st.selectbox('Electro', ['Normal', 'Patológico'])
        aptitud = st.selectbox('Aptitud', ['Apto', 'No Apto'])
        beta_hcg = (
            st.selectbox(
                'Cuantificación de Gonadotropina Coriónica Humana (Beta HCG)',
                ['Negativo', 'Positivo', 'No Realizado'],
            )
            if es_femenino
            else 'N/A'
        )
      if st.form_submit_button('Guardar Exámenes'):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO examenes_periodicos (id_legajo, anio,'
            ' ddjj_enfermedades, visus, hemograma, orina, electrocardiograma,'
            " aptitud_fisica, toxicologico, beta_hcg, fecha_registro) VALUES (?,"
            " '2026', ?, ?, ?, 'Normal', ?, ?, 'Negativo', ?, ?)",
            (
                id_legajo,
                ddjj,
                visus,
                hemograma,
                electro,
                aptitud,
                beta_hcg,
                str(datetime.today()),
            ),
        )
        conn.commit()
        conn.close()
        st.success('¡Exámenes guardados con éxito!')

elif menu == '5. Historia Clínica Integral':
  st.markdown(
      '<h2 style="color: #FFFFFF;">📁 Legajo e Historia Clínica Integral del'
      ' Cadete</h2>',
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #94A3B8;'>Visualización completa de atenciones,"
      ' intervenciones de guardia, expedientes y reposos médicos del cadete'
      ' seleccionado.</p>',
      unsafe_allow_html=True,
  )

  df_cadetes = obtener_cadetes()
  if not df_cadetes.empty:
    busq_hc = st.text_input(
        '🔍 Buscar Cadete por Apellido o Legajo para ver Historia Clínica'
    )
    df_hc_view = df_cadetes.copy()
    if busq_hc:
      df_hc_view = df_hc_view[
          df_hc_view['apellido_nombre'].str.contains(
              busq_hc, case=False, na=False
          )
          | df_hc_view['id_legajo']
          .astype(str)
          .str.contains(busq_hc, case=False, na=False)
      ]

    if not df_hc_view.empty:
      lista_hc = (
          df_hc_view['id_legajo'].astype(str)
          + ' - '
          + df_hc_view['apellido_nombre']
      ).tolist()
      seleccion_hc = st.selectbox('Seleccione el Cadete de la Lista', lista_hc)
      id_leg_hc = seleccion_hc.split(' - ')[0]

      cad_hc = df_cadetes[
          df_cadetes['id_legajo'].astype(str) == id_leg_hc
      ].iloc[0]

      st.markdown(
          f'<div class="profile-card"><div style="display: flex;'
          ' justify-content: space-between; align-items: center;"><div><h2'
          f' style="margin: 0; color: #FFFFFF;">{cad_hc["apellido_nombre"]}</h2><p'
          ' style="margin: 0.25rem 0 0 0; color: #94A3B8; font-size:'
          f' 0.95rem;">Legajo/Cargo: <b>{cad_hc["id_legajo"]}</b> | Curso:'
          f' <b>{cad_hc["curso"]}</b> | DNI: <b>{cad_hc["dni"]}</b> | F. Nac:'
          f' <b>{cad_hc["fecha_nacimiento"]}</b></p><p style="margin: 0.25rem 0 0'
          f' 0; color: #38BDF8; font-size: 0.85rem;"><b>Observaciones /'
          f' Contacto:</b> {cad_hc["observaciones"]}</p></div><div><span'
          ' class="badge-active">HISTORIAL CLÍNICO ACTIVO</span></div></div></div>',
          unsafe_allow_html=True,
      )

      conn = sqlite3.connect(DB_NAME)
      df_nm_hc = pd.read_sql_query(
          f"SELECT * FROM notas_medicas WHERE id_legajo = '{id_leg_hc}'", conn
      )
      df_int_hc = pd.read_sql_query(
          f"SELECT * FROM primera_intervencion WHERE id_legajo = '{id_leg_hc}'",
          conn,
      )
      df_ex_hc = pd.read_sql_query(
          f"SELECT * FROM examenes_periodicos WHERE id_legajo = '{id_leg_hc}'",
          conn,
      )
      df_bj_hc = pd.read_sql_query(
          f"SELECT * FROM examen_baja WHERE id_legajo = '{id_leg_hc}'", conn
      )
      conn.close()

      hc_tab1, hc_tab2, hc_tab3, hc_tab4 = st.tabs([
          '🩺 Intervenciones de Guardia',
          '📋 Notas Médicas y Reposos',
          '🧪 Exámenes Periódicos',
          '🚪 Bajas / Egresos',
      ])

      with hc_tab1:
        st.markdown('### Historial de Intervenciones y Triaje en Guardia')
        if not df_int_hc.empty:
          st.dataframe(df_int_hc, use_container_width=True)
        else:
          st.info('El cadete no registra atenciones de guardia en gabinete.')

      with hc_tab2:
        st.markdown('### Expedientes Médicos y Reposos (Detall)')
        if not df_nm_hc.empty:
          st.dataframe(df_nm_hc, use_container_width=True)
        else:
          st.info('El cadete no registra notas médicas ni días de reposo.')

      with hc_tab3:
        st.markdown('### Controles Periódicos y Anuales')
        if not df_ex_hc.empty:
          st.dataframe(df_ex_hc, use_container_width=True)
        else:
          st.info('El cadete no registra exámenes periódicos cargados.')

      with hc_tab4:
        st.markdown('### Examen Médico de Baja o Egreso')
        if not df_bj_hc.empty:
          st.dataframe(df_bj_hc, use_container_width=True)
        else:
          st.info(
              'El cadete no registra examen de baja o egreso (Activo en'
              ' service).'
          )
    else:
      st.warning('No se encontraron cadetes con ese criterio de búsqueda.')
  else:
    st.warning('No hay cadetes registrados en la base.')

elif menu == '6. Examen de Baja / Egreso':
  st.markdown(
      '<h2 style="color: #FFFFFF;">🚪 Examen Médico de Baja / Egreso</h2>',
      unsafe_allow_html=True,
  )
  df_cadetes = obtener_cadetes()
  if not df_cadetes.empty:
    lista_cadetes = (
        df_cadetes['id_legajo'].astype(str)
        + ' - '
        + df_cadetes['apellido_nombre']
    ).tolist()
    seleccion = st.selectbox('Seleccionar Cadete', lista_cadetes)
    id_legajo = seleccion.split(' - ')[0]
    with st.form('form_baja'):
      motivo = st.selectbox(
          'Motivo', ['Egreso', 'Baja Voluntaria', 'Baja Médica']
      )
      estado = st.text_area('Estado de Salud al Egreso')
      if st.form_submit_button('Guardar Baja'):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO examen_baja (id_legajo, fecha_baja, motivo,'
            ' estado_salud_egreso, observaciones_medicas) VALUES (?, ?, ?, ?, ?)',
            (id_legajo, str(datetime.today().date()), motivo, estado, ''),
        )
        conn.commit()
        conn.close()
        st.success('¡Baja registrada con éxito!')

elif menu == '7. Informes y Análisis de Datos (Spark)':
  st.markdown(
      '<h2 style="color: #FFFFFF;">📊 Análisis de Datos e Inteligencia'
      ' Sanitaria (Spark Analytics)</h2>',
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #94A3B8;'>Motor de analítica avanzada para procesamiento"
      ' masivo de datos de salud y morbilidad institucional.</p>',
      unsafe_allow_html=True,
  )

  conn = sqlite3.connect(DB_NAME)
  df_c_rep = pd.read_sql_query('SELECT * FROM cadetes', conn)
  df_i_rep = pd.read_sql_query(
      'SELECT i.*, c.curso, c.apellido_nombre FROM primera_intervencion i LEFT'
      ' JOIN cadetes c ON i.id_legajo = c.id_legajo',
      conn,
  )
  df_n_rep = pd.read_sql_query(
      'SELECT n.*, c.curso, c.apellido_nombre FROM notas_medicas n LEFT JOIN'
      ' cadetes c ON n.id_legajo = c.id_legajo',
      conn,
  )
  conn.close()

  spark_tab1, spark_tab2, spark_tab3, spark_tab4 = st.tabs([
      '⚡ Resumen Spark (DataFrame)',
      '📈 Morbilidad por Curso',
      '🏥 Centros de Derivación',
      '📋 Reporte Ejecutivo',
  ])

  with spark_tab1:
    st.markdown(
        '### ⚡ Análisis Masivo de Registros Sanitarios (Spark Engine'
        ' Simulation)'
    )
    st.info(
        'ℹ️ Motor analítico activo procesando registros institucionales en'
        ' memoria estructurada.'
    )

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
      st.markdown(
          f'<div class="metric-card"><div'
          f' class="metric-value">{len(df_c_rep)}</div><div'
          ' class="metric-label">Total Registros (Cadetes)</div></div>',
          unsafe_allow_html=True,
      )
    with col_s2:
      st.markdown(
          f'<div class="metric-card"><div'
          f' class="metric-value">{len(df_i_rep)}</div><div'
          ' class="metric-label">Total Atenciones (Guardia)</div></div>',
          unsafe_allow_html=True,
      )
    with col_s3:
      st.markdown(
          f'<div class="metric-card"><div'
          f' class="metric-value">{len(df_n_rep)}</div><div'
          ' class="metric-label">Total Expedientes Médicos</div></div>',
          unsafe_allow_html=True,
      )

    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('#### Vista previa de estructura analítica consolidada')
    if not df_i_rep.empty:
      st.dataframe(df_i_rep.head(10), use_container_width=True)
    else:
      st.write(
          'Aún no hay suficientes intervenciones registradas para mostrar'
          ' agregaciones analíticas.'
      )

  with spark_tab2:
    st.markdown('### 📈 Morbilidad y Distribución por Curso')
    if not df_i_rep.empty:
      curso_morbi = df_i_rep['curso'].value_counts().reset_index()
      curso_morbi.columns = ['Curso', 'Cantidad de Atenciones']
      st.dataframe(curso_morbi, use_container_width=True)
    else:
      st.info('Sin datos suficientes.')

  with spark_tab3:
    st.markdown('### 🏥 Demanda en Centros de Derivación')
    if not df_i_rep.empty:
      deriv_an = df_i_rep['derivacion'].value_counts().reset_index()
      deriv_an.columns = ['Especialidad / Centro Médico', 'Derivaciones']
      st.dataframe(deriv_an, use_container_width=True)
    else:
      st.info('Sin datos de derivación.')

  with spark_tab4:
    st.markdown('### 📋 Exportación de Inteligencia Sanitaria')
    if not df_i_rep.empty:
      csv_data = df_i_rep.to_csv(index=False).encode('utf-8')
      st.download_button(
          label='📥 Descargar Dataset Consolidado (CSV)',
          data=csv_data,
          file_name='analitica_sanitaria_iesp.csv',
          mime='text/csv',
      )
    else:
      st.warning('No hay datos para exportar.')
