from datetime import datetime, date
import os
import sqlite3
import pandas as pd
import streamlit as st
import reportlab
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

st.set_page_config(
    page_title="Gabinete Medico | I.E.S.P. G.J.F.S.M.",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #030712;
        color: #F3F4F6;
    }
    [data-testid="stSidebar"] {
        background-color: #0B0F19;
        border-right: 1px solid #1F2937;
    }
    .pro-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 100%);
        padding: 2.5rem;
        border-radius: 1.25rem;
        border: 1px solid #312E81;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .pro-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF;
    }
    .pro-subtitle {
        font-size: 1.1rem;
        color: #93C5FD;
        margin-top: 0.5rem;
        margin-bottom: 0;
    }
    .metric-card {
        background: #111827;
        padding: 1.5rem;
        border-radius: 1rem;
        border: 1px solid #1F2937;
        text-align: center;
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
        margin-top: 0.35rem;
    }
    .profile-card {
        background: #111827;
        padding: 1.75rem;
        border-radius: 1rem;
        border: 1px solid #1F2937;
        margin-bottom: 1.5rem;
    }
    .alert-card {
        background: rgba(120, 53, 15, 0.4);
        border: 1px solid #B45309;
        padding: 1.25rem;
        border-radius: 0.85rem;
        margin-bottom: 1rem;
        color: #FEF3C7;
    }
    .stTextInput input, .stSelectbox select, .stTextArea textarea, .stDateInput input {
        background-color: #111827 !important;
        color: #FFFFFF !important;
        border: 1px solid #374151 !important;
        border-radius: 0.75rem !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        font-weight: 700;
        border-radius: 0.75rem;
        padding: 0.65rem 1.5rem;
        border: none;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
    }
</style>""",
    unsafe_allow_html=True,
)

DB_NAME = 'gabinete_iesp.db'
EXCEL_FILE = 'LISTADO DE COMPAÑIA DE CADETES AÑO 2026 PARA D1.xlsx'


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
            certificados_indicaciones TEXT,
            analisis_estudios TEXT,
            estado_alta TEXT DEFAULT 'Pendiente'
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS legajo_documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_legajo TEXT,
            titulo_documento TEXT,
            tipo_documento TEXT,
            fecha_subida TEXT,
            archivo_nombre TEXT,
            observaciones TEXT,
            FOREIGN KEY(id_legajo) REFERENCES cadetes(id_legajo)
        )
    """)
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


def generar_pdf_legajo(cad_info, nota_info):
  pdf_filename = f"Legajo_Medico_{cad_info['id_legajo']}.pdf"
  doc = SimpleDocTemplate(
      pdf_filename,
      pagesize=letter,
      rightMargin=40,
      leftMargin=40,
      topMargin=40,
      bottomMargin=40,
  )
  styles = getSampleStyleSheet()
  normal_style = styles['Normal']
  title_style = ParagraphStyle(
      'DocTitle',
      parent=normal_style,
      fontName='Helvetica-Bold',
      fontSize=15,
      leading=18,
      textColor=colors.HexColor('#1E3A8A'),
      alignment=1,
  )
  subtitle_style = ParagraphStyle(
      'DocSubtitle',
      parent=normal_style,
      fontName='Helvetica',
      fontSize=9,
      leading=13,
      textColor=colors.HexColor('#64748B'),
      alignment=1,
  )
  section_heading = ParagraphStyle(
      'SectionHeading',
      parent=normal_style,
      fontName='Helvetica-Bold',
      fontSize=11,
      leading=15,
      textColor=colors.HexColor('#1E3A8A'),
      spaceBefore=8,
      spaceAfter=4,
  )
  body_style = ParagraphStyle(
      'BodyPro',
      parent=normal_style,
      fontName='Helvetica',
      fontSize=9,
      leading=13,
      textColor=colors.HexColor('#1F2937'),
  )
  elements = []
  elements.append(
      Paragraph('INSTITUTO DE ENSEÑANZA SUPERIOR DE POLICÍA', title_style)
  )
  elements.append(
      Paragraph(
          '«Gral. José Francisco de San Martín»<br/>Dirección de Gabinete'
          ' Interdisciplinario',
          subtitle_style,
      )
  )
  elements.append(Spacer(1, 10))
  cadet_info_data = [
      [
          Paragraph(f"<b>Cadete:</b> {cad_info['apellido_nombre']}", body_style),
          Paragraph(f"<b>Legajo:</b> {cad_info['id_legajo']}", body_style),
      ],
      [
          Paragraph(f"<b>Curso:</b> {cad_info['curso']}", body_style),
          Paragraph(f"<b>DNI:</b> {cad_info['dni']}", body_style),
      ],
  ]
  t_cadet = Table(cadet_info_data, colWidths=[270, 270])
  t_cadet.setStyle(
      TableStyle([
          ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
          ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
          ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
          ('PADDING', (0, 0), (-1, -1), 6),
      ])
  )
  elements.append(t_cadet)
  elements.append(Spacer(1, 10))
  elements.append(
      Paragraph('ANEXO DE EXPEDIENTE Y NOTA MÉDICA', section_heading)
  )
  cert = (
      nota_info['certificados_indicaciones']
      if nota_info['certificados_indicaciones']
      else 'Sin transcripcion'
  )
  anal = (
      nota_info['analisis_estudios']
      if nota_info['analisis_estudios']
      else 'Sin estudios'
  )
  note_data = [
      [
          Paragraph(
              f"<b>Nro. Expediente:</b> {nota_info['nro_expediente']}",
              body_style,
          ),
          Paragraph(f"<b>Fecha:</b> {str(datetime.today().date())}", body_style),
      ],
      [
          Paragraph(
              f"<b>Médico Tratante:</b> {nota_info['medico']}", body_style
          ),
          Paragraph(
              f"<b>Tipo de Reposo:</b> {nota_info['tipo_reposo']}"
              f" ({nota_info['fecha_desde']} al {nota_info['fecha_hasta']})",
              body_style,
          ),
      ],
      [
          Paragraph(
              f"<b>Diagnóstico Médico:</b><br/>{nota_info['diagnostico']}",
              body_style,
          ),
          Paragraph(
              f"<b>Medicamentos:</b><br/>{nota_info['medicamentos']}", body_style
          ),
      ],
      [
          Paragraph(
              f'<b>Certificados e Indicaciones:</b><br/>{cert}', body_style
          ),
          Paragraph(f'<b>Análisis y Estudios:</b><br/>{anal}', body_style),
      ],
  ]
  t_note = Table(note_data, colWidths=[270, 270])
  t_note.setStyle(
      TableStyle([
          ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFFFF')),
          ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8')),
          ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
          ('PADDING', (0, 0), (-1, -1), 6),
      ])
  )
  elements.append(t_note)
  elements.append(Spacer(1, 20))
  sig_data = [[
      Paragraph(
          '____________________________________________<br/><b>Firma y Sello'
          ' Profesional / Médico</b>',
          body_style,
      ),
      Paragraph(
          '____________________________________________<br/><b>Firma y Sello'
          ' Dirección de Gabinete</b>',
          body_style,
      ),
  ]]
  t_sig = Table(sig_data, colWidths=[270, 270])
  t_sig.setStyle(
      TableStyle([
          ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
          ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
      ])
  )
  elements.append(KeepTogether(t_sig))
  doc.build(elements)
  return pdf_filename


st.sidebar.image('https://img.icons8.com/color/96/police-badge.png', width=75)
st.sidebar.markdown('### I.E.S.P. G.J.F.S.M.')
menu = st.sidebar.radio(
    'Navegacion',
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
      '<div class="pro-header"><p class="pro-title">🏥 Centro Medico y'
      ' Gabinete I.E.S.P.</p><p class="pro-subtitle">Sistema integral de'
      ' gestion sanitaria.</p></div>',
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
  df_i = pd.read_sql_query(
      'SELECT i.*, c.apellido_nombre, c.curso FROM primera_intervencion i LEFT'
      ' JOIN cadetes c ON i.id_legajo = c.id_legajo',
      conn,
  )
  conn.close()
  col1, col2, col3, col4 = st.columns(4)
  with col1:
    st.metric('Cadetes', len(df_c))
  with col2:
    st.metric('Intervenciones', len(df_i))
  with col3:
    st.metric('Staff', len(df_p))
  with col4:
    st.metric(
        'Pendientes',
        len(df_n[df_n.estado_alta == 'Pendiente']) if not df_n.empty else 0,
    )
  if st.button('Sincronizar Base'):
    importar_excel_directo()
    st.rerun()

elif menu == 'Gestión de Legajos':
  st.markdown('## Legajos')
  st.dataframe(obtener_cadetes(), use_container_width=True)

elif menu == 'Personal del Gabinete':
  st.markdown('## Personal')
  st.dataframe(obtener_personal(), use_container_width=True)

elif menu == '2. Notas Médicas y Reposos':
  st.markdown(
      '<h2>📋 Registro de Notas Médicas, Certificados y Estudios</h2>',
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
    cad_sel = df_cadetes[df_cadetes['id_legajo'].astype(str) == id_legajo].iloc[
        0
    ]
    with st.form('form_nota_medica'):
      col1, col2 = st.columns(2)
      with col1:
        nro_expediente = st.text_input(
            'Número de Expediente* (Ej: EXP-2026-XX)'
        )
        medico = st.text_input('Médico Tratante / Matrícula*')
        diagnostico = st.text_area('Diagnóstico Médico*')
        tipo_reposo = st.selectbox(
            'Tipo de Reposo',
            ['Reposo Domiciliario', 'Reposo Académico', 'Internación', 'ART'],
        )
      with col2:
        fecha_desde = st.date_input('Reposo Desde', value=datetime.today().date())
        fecha_hasta = st.date_input('Reposo Hasta', value=datetime.today().date())
        certificados_indicaciones = st.text_area(
            'Certificados e Indicaciones Médicas'
        )
        analisis_estudios = st.text_area(
            'Análisis de Laboratorio y Estudios Complementarios'
        )
      medicamentos = st.text_input('Medicamentos Recetados')
      if st.form_submit_button(
          'Guardar Nota Médica y Generar PDF para Legajo'
      ):
        if nro_expediente and medico and diagnostico:
          conn = sqlite3.connect(DB_NAME)
          cursor = conn.cursor()
          cursor.execute(
              """
                        INSERT INTO notas_medicas (id_legajo, nro_expediente, medico, diagnostico, tipo_reposo, fecha_desde, fecha_hasta, medicamentos, certificados_indicaciones, analisis_estudios, estado_alta)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente')
                    """,
              (
                  id_legajo,
                  nro_expediente,
                  medico,
                  diagnostico,
                  tipo_reposo,
                  str(fecha_desde),
                  str(fecha_hasta),
                  medicamentos,
                  certificados_indicaciones,
                  analisis_estudios,
              ),
          )
          conn.commit()
          nota_dict = {
              'nro_expediente': nro_expediente,
              'medico': medico,
              'diagnostico': diagnostico,
              'tipo_reposo': tipo_reposo,
              'fecha_desde': str(fecha_desde),
              'fecha_hasta': str(fecha_hasta),
              'medicamentos': medicamentos,
              'certificados_indicaciones': certificados_indicaciones,
              'analisis_estudios': analisis_estudios,
          }
          pdf_path = generar_pdf_legajo(cad_sel, nota_dict)
          cursor.execute(
              'INSERT INTO legajo_documentos (id_legajo, titulo_documento,'
              ' tipo_documento, fecha_subida, archivo_nombre, observaciones)'
              ' VALUES (?, ?, ?, ?, ?, ?)',
              (
                  id_legajo,
                  f'Expediente {nro_expediente} - Nota Médica y Certificado',
                  'PDF Oficial',
                  str(datetime.today().date()),
                  pdf_path,
                  'Generado automáticamente',
              ),
          )
          conn.commit()
          conn.close()
          st.success(
              '¡Nota médica guardada, PDF oficial generado y anexado al legajo'
              ' digital del cadete!'
          )
        else:
          st.warning('Complete los campos obligatorios (*).')

elif menu == '5. Historia Clínica Integral':
  st.markdown(
      '<h2>📁 Historia Clínica e Legajo Digital</h2>', unsafe_allow_html=True
  )
  df_cadetes = obtener_cadetes()
  if not df_cadetes.empty:
    busq_hc = st.text_input('🔍 Buscar Cadete por Apellido o Legajo')
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
      seleccion_hc = st.selectbox('Seleccione Cadete', lista_hc)
      id_leg_hc = seleccion_hc.split(' - ')[0]
      cad_hc = df_cadetes[
          df_cadetes['id_legajo'].astype(str) == id_leg_hc
      ].iloc[0]
      st.markdown(
          f'<div class="profile-card"><h2>{cad_hc["apellido_nombre"]}</h2><p>Legajo:'
          f' <b>{cad_hc["id_legajo"]}</b> | Curso: <b>{cad_hc["curso"]}</b></p></div>',
          unsafe_allow_html=True,
      )
      conn = sqlite3.connect(DB_NAME)
      df_doc_hc = pd.read_sql_query(
          f"SELECT * FROM legajo_documentos WHERE id_legajo = '{id_leg_hc}'", conn
      )
      conn.close()
      st.markdown('### 📥 Documentos en PDF Anexados al Legajo Digital')
      if not df_doc_hc.empty:
        for _, doc_row in df_doc_hc.iterrows():
          st.markdown(
              f"- **{doc_row['titulo_documento']}** (Subido el"
              f" {doc_row['fecha_subida']})"
          )
          if os.path.exists(str(doc_row['archivo_nombre'])):
            with open(doc_row['archivo_nombre'], 'rb') as f:
              st.download_button(
                  label=f"📥 Descargar PDF: {doc_row['archivo_nombre']}",
                  data=f.read(),
                  file_name=doc_row['archivo_nombre'],
                  mime='application/pdf',
                  key=f"dl_{doc_row['id']}",
              )
      else:
        st.info('No hay documentos PDF en el legajo digital todavía.')
else:
  st.markdown(f'## Módulo: {menu}')
