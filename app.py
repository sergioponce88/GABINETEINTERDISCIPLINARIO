from datetime import datetime, date, timedelta
import os
import sqlite3
import pandas as pd
import streamlit as st
import html as _html
import reportlab
import seguridad as sec
import analitica
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

def _buscar_logo(nombre):
  for carpeta in ('.', 'assets', 'imagenes', 'img'):
    if os.path.isdir(carpeta):
      for f in os.listdir(carpeta):
        if f.lower() == nombre.lower():
          return os.path.join(carpeta, f)
  return None

@st.cache_data(show_spinner=False)
def logo_uri(nombre, alto=120):
  ruta = _buscar_logo(nombre)
  if not ruta:
    return ''
  try:
    import base64
    import io
    from PIL import Image, ImageDraw, ImageFilter
    im = Image.open(ruta).convert('RGBA')
    m = im.getchannel('A').point(lambda a: 255 if a < 16 else 0)
    if m.getpixel((0, 0)) == 255:
      ImageDraw.floodfill(m, (0, 0), 128)
      huecos = m.point(lambda v: 255 if v == 255 else 0).filter(ImageFilter.MaxFilter(5))
      blanco = Image.new('RGBA', im.size, (255, 255, 255, 255))
      im = Image.composite(Image.alpha_composite(blanco, im), im, huecos)
    ancho = max(1, round(im.width * alto / im.height))
    im = im.resize((ancho, alto), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format='PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
  except Exception:
    return ''

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

st.markdown("""<style>
@import url("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap");
:root {
  --bg: #05070D; --surface: #0C1220; --surface-2: #111A2E; --border: #1C2740;
  --text: #FFFFFF; --muted: #E2E8F0; --accent: #3B82F6; --accent-2: #22D3EE;
  --ok: #10B981; --warn: #F59E0B; --crit: #EF4444; --info: #38BDF8;
}
html, body, [class*="css"], .stApp, button, input, textarea, select, label, p, span, div {
  font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif !important;
  color: #FFFFFF !important;
}
.stApp {
  background: radial-gradient(900px 400px at 85% -10%, rgba(59,130,246,0.10), transparent 60%),
              radial-gradient(700px 380px at -5% 0%, rgba(34,211,238,0.06), transparent 60%), var(--bg);
  color: #FFFFFF !important;
}
[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1400px; }
h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  color: #FFFFFF !important; font-weight: 800 !important;
}
p, span, label, div[data-testid="stMarkdownContainer"] {
  color: #FFFFFF !important;
}

/* Etiquetas de formularios en cian brillante */
label, .stTextInput label, .stSelectbox label, .stMultiSelect label, .stDateInput label, .stTextArea label, .stNumberInput label {
  color: #38BDF8 !important;
  font-size: 0.82rem !important;
  font-weight: 700 !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0A1020 0%, #070B16 100%) !important;
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
  color: #FFFFFF !important;
}
[data-testid="stSidebar"] label[data-baseweb="radio"] p,
[data-testid="stSidebar"] label[data-baseweb="radio"] div {
  color: #FFFFFF !important;
  font-weight: 700 !important;
  font-size: 0.95rem !important;
}

.brand { display: flex; align-items: center; gap: 0.85rem; padding: 0.4rem 0.2rem 1.1rem 0.2rem; border-bottom: 1px solid var(--border); margin-bottom: 1.2rem; }
.brand-logo { width: 46px; height: 46px; border-radius: 13px; display: grid; place-items: center; font-size: 1.5rem; background: linear-gradient(135deg, #2563EB, #22D3EE); box-shadow: 0 8px 24px rgba(37,99,235,0.45); }
.brand-name { font-weight: 800; font-size: 1.02rem; color: #FFFFFF !important; }
.brand-sub { font-size: 0.74rem; color: #E2E8F0 !important; margin-top: 0.15rem; }
.nav-label { font-size: 0.72rem; font-weight: 800; color: #38BDF8 !important; text-transform: uppercase; letter-spacing: 0.12em; margin: 0 0 0.5rem 0.3rem; }
.side-foot { margin-top: 2rem; padding: 0.8rem 0.9rem; border: 1px solid var(--border); border-radius: 12px; font-size: 0.78rem; color: #FFFFFF !important; background: rgba(17,26,46,0.8); }

.hero { position: relative; overflow: hidden; display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; flex-wrap: wrap; padding: 2rem 2.2rem; border-radius: 22px; margin-bottom: 1.4rem; border: 1px solid #22305A; background: radial-gradient(600px 220px at 100% 0%, rgba(34,211,238,0.18), transparent 65%), radial-gradient(500px 260px at 0% 100%, rgba(99,102,241,0.25), transparent 65%), linear-gradient(135deg, #0B1330 0%, #121B45 100%); }
.kpi { position: relative; overflow: hidden; display: flex; align-items: center; gap: 1rem; padding: 1.15rem 1.3rem; border-radius: 18px; border: 1px solid var(--border); background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); }
.kpi-value { font-size: 2rem; font-weight: 800; color: #FFFFFF !important; }
.kpi-label { font-size: 0.72rem; font-weight: 700; color: #E2E8F0 !important; text-transform: uppercase; }
.panel { border: 1px solid var(--border); border-radius: 18px; padding: 1.2rem 1.3rem; margin-bottom: 1rem; background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); color: #FFFFFF !important; }
.pro-header { background: linear-gradient(135deg, #0B1330 0%, #121B45 100%); padding: 2rem; border-radius: 20px; border: 1px solid #22305A; color: white; margin-bottom: 1.5rem; }
.pro-title { font-size: 2rem; font-weight: 800; margin: 0; color: #FFFFFF !important; }
.pro-subtitle { font-size: 1rem; color: #93C5FD !important; margin-top: 0.4rem; }
.profile-card { background: linear-gradient(135deg, #0F172A 0%, #111B33 100%); padding: 1.5rem 1.75rem; border-radius: 18px; border: 1px solid var(--border); border-left: 4px solid var(--accent); margin-bottom: 1.5rem; color: #FFFFFF !important; }

input, textarea, select, div[data-baseweb="select"] span, div[data-baseweb="select"] div {
  color: #FFFFFF !important;
  background-color: #0C1220 !important;
  -webkit-text-fill-color: #FFFFFF !important;
}
.stTextInput input, .stTextArea textarea, .stDateInput input {
  color: #FFFFFF !important;
  background-color: #0C1220 !important;
  -webkit-text-fill-color: #FFFFFF !important;
}
</style>""", unsafe_allow_html=True)

DB_NAME = 'gabinete_iesp.db'
EXCEL_FILE = 'LISTADO DE COMPAÑIA DE CADETES AÑO 2026 PARA D1.xlsx'
UPLOAD_DIR = 'documentos_legajos'
if not os.path.exists(UPLOAD_DIR):
  os.makedirs(UPLOAD_DIR)

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
  conn.commit()
  conn.close()

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

def generar_pdf_historia_clinica(cad_info, df_notas, df_intervenciones, anio_filtro=None):
    pdf_filename = sec.nombre_seguro(f"Historia_Clinica_Completa_{cad_info['id_legajo']}_{anio_filtro if anio_filtro else 'Historica'}.pdf", unico=False)
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    
    title_style = ParagraphStyle('DocTitle', parent=normal_style, fontName='Helvetica-Bold', fontSize=14, leading=16, textColor=colors.HexColor('#1E3A8A'), alignment=1)
    subtitle_style = ParagraphStyle('DocSubtitle', parent=normal_style, fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#64748B'), alignment=1)
    section_heading = ParagraphStyle('SectionHeading', parent=normal_style, fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=colors.HexColor('#1E3A8A'), spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle('BodyPro', parent=normal_style, fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#1F2937'))
    
    elements = []
    elements.append(Paragraph("INSTITUTO DE ENSEÑANZA SUPERIOR DE POLICÍA", title_style))
    elements.append(Paragraph("«Gral. José Francisco de San Martín»<br/>Dirección de Gabinete Interdisciplinario - Historia Clínica Sanitaria Integral", subtitle_style))
    elements.append(Spacer(1, 10))
    
    cadet_info_data = [
        [Paragraph(f"<b>Cadete:</b> {cad_info['apellido_nombre']}", body_style), Paragraph(f"<b>Legajo:</b> {cad_info['id_legajo']}", body_style)],
        [Paragraph(f"<b>Curso:</b> {cad_info['curso']}", body_style), Paragraph(f"<b>DNI:</b> {cad_info['dni']}", body_style)],
        [Paragraph(f"<b>Género:</b> {cad_info['genero']}", body_style), Paragraph(f"<b>Período del Reporte:</b> {'Año ' + str(anio_filtro) if anio_filtro else 'Historial Clínico Completo'}", body_style)]
    ]
    t_cadet = Table(cadet_info_data, colWidths=[270, 270])
    t_cadet.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))
    elements.append(t_cadet)
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("1. REGISTRO COMPLETO DE NOTAS MÉDICAS Y REPOSOS", section_heading))
    if not df_notas.empty:
        if anio_filtro:
            df_notas_pdf = df_notas[df_notas['fecha_desde'].astype(str).str.contains(str(anio_filtro), na=False)]
        else:
            df_notas_pdf = df_notas.copy()
            
        if not df_notas_pdf.empty:
            for _, r in df_notas_pdf.iterrows():
                exp_txt = f"<b>Expediente:</b> {r['nro_expediente']} | <b>Estado:</b> {r['estado_alta']}"
                med_txt = f"<b>Médico:</b> {r['medico']} | <b>Tipo:</b> {r['tipo_reposo']} ({r['fecha_desde']} al {r['fecha_hasta']})"
                diag_txt = f"<b>Diagnóstico:</b> {r['diagnostico']}"
                cert_txt = f"<b>Certificado/Indicaciones:</b> {r.get('certificados_indicaciones', 'Sin anexos')}"
                est_txt = f"<b>Estudios:</b> {r.get('analisis_estudios', 'Sin estudios')}"
                
                detalles_nota = [
                    [Paragraph(exp_txt, body_style)],
                    [Paragraph(med_txt, body_style)],
                    [Paragraph(diag_txt, body_style)],
                    [Paragraph(cert_txt, body_style)],
                    [Paragraph(est_txt, body_style)]
                ]
                t_single_nota = Table(detalles_nota, colWidths=[540])
                t_single_nota.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
                    ('PADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4)
                ]))
                elements.append(t_single_nota)
                elements.append(Spacer(1, 6))
        else:
            elements.append(Paragraph("No hay notas médicas para el período seleccionado.", body_style))
    else:
        elements.append(Paragraph("Sin registros de notas médicas.", body_style))
        
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("2. INTERVENCIONES Y ATENCIONES DE GUARDIA", section_heading))
    if not df_intervenciones.empty:
        if anio_filtro:
            df_int_pdf = df_intervenciones[df_intervenciones['fecha_hora'].astype(str).str.contains(str(anio_filtro), na=False)]
        else:
            df_int_pdf = df_intervenciones.copy()
            
        if not df_int_pdf.empty:
            inter_table_data = [["Fecha / Hora", "Profesional", "Síntomas / Signos", "Derivación"]]
            for _, r in df_int_pdf.iterrows():
                signos = f"PA: {r.get('presion','-')} | SpO2: {r.get('saturacion','-')} | T: {r.get('temperatura','-')}°C"
                inter_table_data.append([
                    Paragraph(str(r['fecha_hora']), body_style),
                    Paragraph(str(r['profesional_atiende']), body_style),
                    Paragraph(f"{r['sintomas']}<br/><i>{signos}</i>", body_style),
                    Paragraph(str(r['derivacion']), body_style)
                ])
            t_i = Table(inter_table_data, colWidths=[100, 100, 220, 120])
            t_i.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 8.5),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 4)
            ]))
            elements.append(t_i)
        else:
            elements.append(Paragraph("No hay intervenciones para el período seleccionado.", body_style))
    else:
        elements.append(Paragraph("Sin registros de guardia.", body_style))
        
    elements.append(Spacer(1, 15))
    sig_data = [[
        Paragraph("____________________________________________<br/><b>Firma y Sello Médico / Gabinete</b>", body_style),
        Paragraph("____________________________________________<br/><b>Firma y Sello Dirección de Gabinete</b>", body_style)
    ]]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'BOTTOM')]))
    elements.append(KeepTogether(t_sig))
    
    doc.build(elements)
    return pdf_filename

def generar_pdf_legajo(cad_info, nota_info):
  pdf_filename = sec.nombre_seguro(
      f"Legajo_Medico_{cad_info['id_legajo']}_{nota_info.get('nro_expediente', '')}.pdf",
      unico=False,
  )
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
      else 'Sin transcripción'
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
          Paragraph(f"<b>Fecha:</b> {str(sec.ahora_local().date())}", body_style),
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

_logo_gab = logo_uri('GABINETE.png', 116)
_brand_logo = (
    f'<div class="brand-logo has-img"><img src="{_logo_gab}" alt="Gabinete"></div>'
    if _logo_gab
    else '<div class="brand-logo">🛡️</div>'
)
sec.init_seguridad(DB_NAME)
sec.exigir_login(_brand_logo)

st.sidebar.markdown(
    f'<div class="brand">{_brand_logo}<div><div'
    ' class="brand-name">I.E.S.P. G.J.F.S.M.</div><div class="brand-sub">Dirección'
    ' de Gabinete Médico</div></div></div><div class="nav-label">Navegación'
    ' principal</div>',
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
    sec.menu_disponible(),
    format_func=lambda x: f"{ICONOS_MENU.get(x, '•')}  {x}",
    label_visibility='collapsed',
)
st.sidebar.markdown(
    '<div class="side-foot">🔒 Información sanitaria confidencial.<br>Uso'
    ' exclusivo del personal autorizado.</div>',
    unsafe_allow_html=True,
)
sec.render_sidebar_usuario()
if not sec.autorizar_menu(menu):
  st.stop()

DIAS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
            'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

def fecha_larga_es(d):
  return f'{DIAS_ES[d.weekday()]} {d.day} de {MESES_ES[d.month - 1]} de {d.year}'

def kpi_card(icono, valor, rotulo, color='#38BDF8', sub=''):
  sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ''
  return (
      f'<div class="kpi" style="--c: {color};"><div class="kpi-icon">{icono}</div>'
      f'<div><div class="kpi-value">{valor}</div><div class="kpi-label">{rotulo}</div>'
      f'{sub_html}</div></div>'
  )

def construir_alertas(df_n, df_e, df_i, hoy):
  def _txt(valor, defecto='-'):
    return defecto if pd.isna(valor) or str(valor).strip() == '' else str(valor)

  alertas = []
  if not df_n.empty:
    pend = df_n[df_n['estado_alta'] == 'Pendiente']
    for _, r in pend.iterrows():
      base = {
          'cadete': _txt(r.get('apellido_nombre'), 'Cadete sin datos'),
          'curso': _txt(r.get('curso')),
          'legajo': _txt(r.get('id_legajo')),
      }
      tipo_rep = _txt(r.get('tipo_reposo'), 'reposo')
      f_h = pd.to_datetime(r.get('fecha_hasta'), errors='coerce')
      if pd.isna(f_h):
        alertas.append({**base, 'nivel': 1, 'tipo': 'Reposo sin fecha de fin',
                        'detalle': f'El reposo ({tipo_rep}) no tiene fecha de finalización cargada.',
                        'orden': 0})
        continue
      f_h = f_h.date()
      dias = (hoy - f_h).days
      if dias > 0:
        alertas.append({**base, 'nivel': 0, 'tipo': 'Alta vencida',
                        'detalle': f'Reposo ({tipo_rep}) finalizó el {f_h:%d/%m/%Y} (hace {dias} días) sin convalidar el alta.',
                        'orden': dias})
      elif dias >= -3:
        cuando = 'vence hoy' if dias == 0 else f'vence en {-dias} día(s)'
        alertas.append({**base, 'nivel': 1, 'tipo': 'Reposo por vencer',
                        'detalle': f'Reposo ({tipo_rep}) {cuando} ({f_h:%d/%m/%Y}). Preparar convalidación de alta.',
                        'orden': 100 + dias})
      else:
        alertas.append({**base, 'nivel': 2, 'tipo': 'Reposo vigente',
                        'detalle': f'Reposo ({tipo_rep}) hasta el {f_h:%d/%m/%Y} (faltan {-dias} días).',
                        'orden': -dias})

  if not df_e.empty:
    fem = df_e[df_e['genero'] == 'Femenino'].copy()
    if not fem.empty:
      fem['_f'] = pd.to_datetime(fem['fecha_registro'], errors='coerce')
      ultimos = fem.sort_values('_f').groupby('id_legajo').tail(1)
      for _, r in ultimos.iterrows():
        if pd.isna(r['_f']):
          continue
        dias = (pd.Timestamp(hoy) - r['_f']).days
        if dias > 90:
          alertas.append({
              'cadete': _txt(r.get('apellido_nombre'), 'Cadete sin datos'),
              'curso': _txt(r.get('curso')),
              'legajo': _txt(r.get('id_legajo')),
              'nivel': 1, 'tipo': 'Control Beta HCG vencido',
              'detalle': f'Último control el {r["_f"]:%d/%m/%Y} (hace {dias} días). Supera el control trimestral.',
              'orden': dias})

  if not df_i.empty:
    di = df_i.copy()
    di['_f'] = pd.to_datetime(di['fecha_hora'], errors='coerce')
    rec = di[di['_f'] >= pd.Timestamp(hoy) - pd.Timedelta(days=30)]
    for leg, g in rec.groupby('id_legajo'):
      if len(g) >= 3:
        r = g.iloc[-1]
        alertas.append({
            'cadete': _txt(r.get('apellido_nombre'), 'Cadete sin datos'),
            'curso': _txt(r.get('curso')),
            'legajo': _txt(leg),
            'nivel': 1, 'tipo': 'Consultas frecuentes',
            'detalle': f'{len(g)} intervenciones en los últimos 30 días. Evaluar derivación o seguimiento.',
            'orden': len(g)})

  alertas.sort(key=lambda a: (a['nivel'], -a['orden']))
  return alertas

if menu == 'Dashboard General':
  _l_dir = logo_uri('DIRECCION.png', 200)
  _l_gab = logo_uri('GABINETE.png', 200)
  _logos_html = ''.join(
      f'<img src="{u}" alt="{a}">'
      for u, a in ((_l_dir, 'Dirección General de Institutos e Instrucción'),
                   (_l_gab, 'Gabinete Interdisciplinario'))
      if u
  )
  _logos_html = f'<div class="hero-logos">{_logos_html}</div>' if _logos_html else ''
  st.markdown(
      f'<div class="hero"><div class="hero-main">{_logos_html}<div>'
      '<div class="hero-eyebrow">Panel de control</div>'
      '<div class="hero-title">Dirección de Gabinete Interdisciplinario de Asesoramiento Psicopedagógico y Psicológico</div>'
      '<div class="hero-org">Dirección General de Institutos e Instrucción · Policía de Tucumán</div></div></div><div'
      ' class="hero-right"><div class="chip"><span class="dot"></span>Sistema operativo</div>'
      f'<div class="hero-date">{fecha_larga_es(sec.ahora_local().date())}</div>'
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

  pendientes_alta = len(df_n[df_n['estado_alta'] == 'Pendiente']) if not df_n.empty else 0
  col1, col2, col3, col4 = st.columns(4)
  with col1: st.markdown(kpi_card('🎓', len(df_c), 'Cadetes en compañía', '#38BDF8', 'Total en base de datos'), unsafe_allow_html=True)
  with col2: st.markdown(kpi_card('🩺', len(df_i), 'Intervenciones de guardia', '#A78BFA', 'Registradas en total'), unsafe_allow_html=True)
  with col3: st.markdown(kpi_card('🧑‍⚕️', len(df_p), 'Staff del gabinete', '#34D399', 'Personal activo'), unsafe_allow_html=True)
  with col4: st.markdown(kpi_card('⏳', pendientes_alta, 'Altas pendientes', '#FBBF24', 'Requieren convalidación'), unsafe_allow_html=True)

  st.markdown('<br>', unsafe_allow_html=True)
  dash_tab1, dash_tab2, dash_tab3 = st.tabs([
      '🚨 Centro de Alertas y Vencimientos',
      '📋 Consulta General de Compañía',
      '⚡ Acciones Rápidas y Sincronización',
  ])
  with dash_tab1:
    from html import escape as _esc
    hoy = sec.ahora_local().date()
    alertas = construir_alertas(df_n, df_e, df_i, hoy)
    n_crit = sum(1 for a in alertas if a['nivel'] == 0)
    n_warn = sum(1 for a in alertas if a['nivel'] == 1)
    n_info = sum(1 for a in alertas if a['nivel'] == 2)

    k1, k2, k3 = st.columns(3)
    with k1: st.markdown(kpi_card('🚨', n_crit, 'Alertas críticas', '#EF4444', 'Acción inmediata'), unsafe_allow_html=True)
    with k2: st.markdown(kpi_card('⚠️', n_warn, 'Requieren atención', '#F59E0B', 'Seguimiento próximo'), unsafe_allow_html=True)
    with k3: st.markdown(kpi_card('🛌', n_info, 'Reposos vigentes', '#38BDF8', 'Informativo'), unsafe_allow_html=True)
    st.markdown('<br>', unsafe_allow_html=True)

    f1, f2 = st.columns([2, 1])
    with f1:
      niveles_sel = st.multiselect('Mostrar', ['Críticas', 'Requieren atención', 'Informativas'], default=['Críticas', 'Requieren atención'])
    with f2:
      cursos = sorted({a['curso'] for a in alertas})
      curso_sel = st.selectbox('Curso', ['Todos'] + cursos)

    mapa_nivel = {'Críticas': 0, 'Requieren atención': 1, 'Informativas': 2}
    permitidos = {mapa_nivel[n] for n in niveles_sel}
    visibles = [a for a in alertas if a['nivel'] in permitidos and (curso_sel == 'Todos' or a['curso'] == curso_sel)]
    iconos_nivel = {0: '🚨', 1: '⏰', 2: '🛌'}
    etiquetas_nivel = {0: 'Crítica', 1: 'Atención', 2: 'Informativa'}

    anio_actual = str(hoy.year)
    con_examen = set(df_e.loc[df_e['anio'].astype(str) == anio_actual, 'id_legajo'].astype(str)) if not df_e.empty else set()
    ids_cadetes = set(df_c['id_legajo'].astype(str))
    con_examen &= ids_cadetes
    pct_cob = round(100 * len(con_examen) / len(ids_cadetes)) if ids_cadetes else 0

    col_izq, col_der = st.columns([2.1, 1], gap='large')
    with col_izq:
      st.markdown(f'<div class="section-head"><div><div class="t">Centro de alertas</div><div class="s">{len(visibles)} alerta(s) según los filtros seleccionados</div></div></div>', unsafe_allow_html=True)
      if not visibles:
        st.markdown('<div class="alert-ok"><span class="big">✅</span><div>Sin alertas para los filtros seleccionados.<br><span style="font-weight:400; opacity:.8;">Todo en orden.</span></div></div>', unsafe_allow_html=True)
      else:
        for a in visibles[:60]:
          st.markdown(f'<div class="al al-{a["nivel"]}"><div class="al-icon">{iconos_nivel[a["nivel"]]}</div><div class="al-main"><span class="al-pill">{etiquetas_nivel[a["nivel"]]} · {_esc(a["tipo"])}</span><div class="al-name">{_esc(a["cadete"])}</div><div class="al-detail">{_esc(a["detalle"])}</div></div><div class="al-meta"><span class="tag">Curso {_esc(a["curso"])}</span><span class="tag">Legajo {_esc(a["legajo"])}</span></div></div>', unsafe_allow_html=True)
        if len(visibles) > 60:
          st.caption(f'Mostrando 60 de {len(visibles)} alertas.')
        df_alertas = pd.DataFrame(visibles).drop(columns=['nivel', 'orden'])
        df_alertas.columns = ['Cadete', 'Curso', 'Legajo', 'Tipo', 'Detalle']
        st.download_button('⬇️ Descargar alertas (CSV)', df_alertas.to_csv(index=False).encode('utf-8-sig'), file_name=f'alertas_{hoy}.csv', mime='text/csv')

    with col_der:
      st.markdown(f'<div class="panel"><div class="panel-title">Exámenes periódicos {anio_actual}</div><div class="panel-big">{pct_cob}%</div><div class="bar"><div style="width: {pct_cob}%;"></div></div><div class="panel-note">{len(con_examen)} de {len(ids_cadetes)} cadetes con examen</div></div>', unsafe_allow_html=True)

  with dash_tab2:
    st.markdown('### 👥 Consulta Rápida de Compañía')
    if not df_c.empty:
      busq_dash = st.text_input('🔍 Filtrar por Apellido, Nombre o Legajo')
      df_c_view = df_c.copy()
      if busq_dash:
        df_c_view = df_c_view[df_c_view['apellido_nombre'].str.contains(busq_dash, case=False, na=False) | df_c_view['id_legajo'].astype(str).str.contains(busq_dash, case=False, na=False)]
      st.dataframe(df_c_view, use_container_width=True)
  with dash_tab3:
    if st.button('Sincronizar Base de Cadetes'):
      ex, ms = importar_excel_directo()
      if ex: st.success(ms); st.rerun()
      else: st.error(ms)

elif menu == 'Gestión de Legajos':
  st.markdown('<div class="pro-header"><p class="pro-title">📁 Gestión de Legajos</p></div>', unsafe_allow_html=True)
  df_cadetes = obtener_cadetes()
  if not df_cadetes.empty:
    busqueda = st.text_input('🔍 Buscar por Apellido o Legajo')
    if busqueda:
      df_cadetes = df_cadetes[df_cadetes['apellido_nombre'].str.contains(busqueda, case=False, na=False) | df_cadetes['id_legajo'].astype(str).str.contains(busqueda, case=False, na=False)]
    st.dataframe(df_cadetes, use_container_width=True)

elif menu == 'Personal del Gabinete':
  st.markdown('<div class="pro-header"><p class="pro-title">👥 Staff Médico</p></div>', unsafe_allow_html=True)
  df_personal = obtener_personal()
  if not df_personal.empty:
    st.dataframe(df_personal, use_container_width=True)
  else:
    st.info('Sin personal registrado.')

elif menu == '1. Primera Intervención':
  st.markdown('## 🩺 Primera Intervención en Guardia')
  df_c = obtener_cadetes()
  df_p = obtener_personal()
  if not df_c.empty:
    lista_c = (df_c['id_legajo'].astype(str) + ' - ' + df_c['apellido_nombre']).tolist()
    sel = st.selectbox('Cadete', lista_c)
    id_leg = sel.split(' - ')[0]
    lista_prof = df_p['apellido_nombre'].tolist() if not df_p.empty else ['Sin personal']
    with st.form('f_int'):
      f_h = st.text_input('Fecha y Hora', value=sec.ahora_local().strftime('%Y-%m-%d %H:%M'))
      prof = st.selectbox('Profesional', lista_prof)
      sint = st.text_area('Síntomas')
      pres = st.text_input('Presión')
      sat = st.text_input('Saturación')
      temp = st.text_input('Temperatura (°C)')
      der = st.selectbox('Derivación', ['Clínica', 'Traumatología', 'Psicología', 'Otro'])
      if st.form_submit_button('Registrar') and sec.exigir('primera_intervencion'):
        conn = sqlite3.connect(DB_NAME)
        conn.execute('INSERT INTO primera_intervencion (id_legajo, fecha_hora, profesional_atiende, sintomas, presion, saturacion, temperatura, derivacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                     (id_leg, f_h, prof, sint, pres, sat, temp, der))
        conn.commit()
        conn.close()
        sec.registrar_auditoria('Intervención', 'INSERT', 'Intervención guardada', id_leg)
        st.success('Registrado con éxito!')
        st.rerun()

elif menu == '2. Notas Médicas y Reposos':
  st.markdown('## 📋 Registro de Notas Médicas y Reposos')
  df_cadetes = obtener_cadetes()
  if not df_cadetes.empty:
    lista_c = (df_cadetes['id_legajo'].astype(str) + ' - ' + df_cadetes['apellido_nombre']).tolist()
    sel = st.selectbox('Cadete', lista_c)
    id_leg = sel.split(' - ')[0]
    cad_sel = df_cadetes[df_cadetes['id_legajo'].astype(str) == id_leg].iloc[0]
    st.markdown(
        f'<div class="profile-card"><h3 style="margin: 0; color: #FFFFFF;">{cad_sel["apellido_nombre"]}</h3><p style="margin: 0.25rem 0 0 0; color: #94A3B8;">Legajo: <b>{cad_sel["id_legajo"]}</b> | Curso: <b>{cad_sel["curso"]}</b></p></div>',
        unsafe_allow_html=True,
    )
    
    with st.form('form_nota', clear_on_submit=True):
      col1, col2 = st.columns(2)
      with col1:
        nro_exp = st.text_input('Número de Expediente* (Ej: EXP-2026-XX)')
        med = st.text_input('Médico Tratante / Matrícula*')
        diag = st.text_area('Diagnóstico Médico*')
        tipo_rep = st.selectbox('Tipo de Reposo', ['Reposo Domiciliario', 'Reposo Académico', 'Internación', 'ART'])
      with col2:
        f_des = st.date_input('Reposo Desde', value=sec.ahora_local().date())
        f_has = st.date_input('Reposo Hasta', value=sec.ahora_local().date())
        cert = st.text_area('Certificados e Indicaciones Médicas')
        anal = st.text_area('Análisis y Estudios Complementarios')
      
      medicamentos = st.text_input('Medicamentos Recetados')
      
      st.markdown('<br>', unsafe_allow_html=True)
      uploaded_file = st.file_uploader(
          '📎 Adjuntar Archivo PDF Externo (Certificado / Análisis / Estudio escaneado)',
          type=['pdf'],
      )
      
      st.markdown('<br>', unsafe_allow_html=True)
      submitted_nota = st.form_submit_button('💾 Guardar Nota Médica y Expediente')

    if submitted_nota:
      uploaded_file_valid = sec.validar_pdf(uploaded_file)
      if nro_exp and med and diag:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
                INSERT INTO notas_medicas (id_legajo, nro_expediente, medico, diagnostico, tipo_reposo, fecha_desde, fecha_hasta, medicamentos, certificados_indicaciones, analisis_estudios, estado_alta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente')
            """,
            (
                id_leg,
                nro_exp,
                med,
                diag,
                tipo_rep,
                str(f_des),
                str(f_has),
                medicamentos,
                cert,
                anal,
            ),
        )
        conn.commit()
        nota_dict = {
            'nro_expediente': nro_exp,
            'medico': med,
            'diagnostico': diag,
            'tipo_reposo': tipo_rep,
            'fecha_desde': str(f_des),
            'fecha_hasta': str(f_has),
            'medicamentos': medicamentos,
            'certificados_indicaciones': cert,
            'analisis_estudios': anal,
        }
        pdf_path = generar_pdf_legajo(cad_sel, nota_dict)
        cursor.execute(
            'INSERT INTO legajo_documentos (id_legajo, titulo_documento, tipo_documento, fecha_subida, archivo_nombre, observaciones)'
            ' VALUES (?, ?, ?, ?, ?, ?)',
            (
                id_leg,
                f'Expediente {nro_exp} - Nota Médica y Certificado',
                'PDF Oficial',
                str(sec.ahora_local().date()),
                pdf_path,
                'Generado automáticamente',
            ),
        )
        if uploaded_file_valid is not None:
          ext_path = os.path.join(
              UPLOAD_DIR,
              sec.nombre_seguro(f'{id_leg}_{nro_exp}_{uploaded_file_valid.name}'),
          )
          with open(ext_path, 'wb') as f_ext:
            f_ext.write(uploaded_file_valid.getbuffer())
          cursor.execute(
              'INSERT INTO legajo_documentos (id_legajo, titulo_documento, tipo_documento, fecha_subida, archivo_nombre, observaciones)'
              ' VALUES (?, ?, ?, ?, ?, ?)',
              (
                  id_leg,
                  f'Expediente {nro_exp} - Archivo Externo Adjunto',
                  'PDF Externo',
                  str(sec.ahora_local().date()),
                  ext_path,
                  'Subido por usuario',
              ),
          )
        conn.commit()
        conn.close()
        sec.registrar_auditoria('Notas Médicas', 'INSERT', f'Nota médica / expediente {nro_exp} registrado', id_leg)
        
        # Generamos el texto institucional exacto para WhatsApp
        hora_actual_str = sec.ahora_local().strftime('%H:%M')
        fecha_actual_str = fecha_larga_es(sec.ahora_local().date())
        usuario_que_informa = (st.session_state.get('auth_user') or {}).get('nombre_completo', 'Personal de Guardia')
        
        texto_wa = f"""🇦🇷 *Dirección de Gabinete Interdisciplinario de Asesoramiento Psicopedagógico y Psicológico* 🇦🇷
➖➖➖➖➖➖➖➖
🇦🇷 *GUARDIA MEDICA* 🇦🇷
➖➖➖➖➖➖➖
*FECHA:* {fecha_actual_str}
 
_______________________
*Ref.:* Nota Medica
 
Para conocimiento de la Superioridad, en el día de la fecha, siendo horas {hora_actual_str} se hizo presente en el recinto de guardia el/la cadete de {cad_sel['curso']} {cad_sel['apellido_nombre']} (Legajo: {cad_sel['id_legajo']}) quien presenta certificado medico expedido por {med} en el cual diagnóstica {diag}, con reposo por {tipo_rep} a partir de la fecha (Expediente Nro: {nro_exp}).

*Obs:* {cert if cert else 'Sin observaciones adicionales'}.

➖➖➖➖➖➖➖➖
*SUPERVISOR GENERAL:* 
Comisario Correa María de los Angeles
_*(Directora del D.G.I.A.P.P.")*_

*INFORMA:*
{usuario_que_informa}"""

        st.success('✅ ¡Nota médica guardada con éxito, expediente generado y campos limpios!')
        st.markdown('### 📱 Parte Institucional para WhatsApp')
        st.info('Copie el siguiente texto o presione el botón para enviarlo directamente por WhatsApp.')
        st.code(texto_wa, language='markdown')
        
        import urllib.parse
        wa_link = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"
        st.markdown(f'<a href="{wa_link}" target="_blank"><button style="background-color:#25D366; color:white; padding:0.6rem 1.4rem; border:none; border-radius:12px; font-weight:700; cursor:pointer; font-size:1rem;">💬 Enviar Parte por WhatsApp</button></a>', unsafe_allow_html=True)
      else:
        st.warning('Complete los campos obligatorios (*).')

elif menu == '3. Control de Alta':
  st.markdown('## ✅ Control de Alta')
  conn = sqlite3.connect(DB_NAME)
  df_p = pd.read_sql_query("SELECT n.*, c.apellido_nombre FROM notas_medicas n LEFT JOIN cadetes c ON n.id_legajo = c.id_legajo WHERE n.estado_alta = 'Pendiente'", conn)
  conn.close()
  if not df_p.empty:
    st.dataframe(df_p[['id', 'nro_expediente', 'id_legajo', 'apellido_nombre', 'tipo_reposo', 'fecha_hasta']], use_container_width=True)
    sel_exp = st.selectbox('Expediente a Convalidar', df_p['id'].astype(str) + " - " + df_p['apellido_nombre'] + " (Exp: " + df_p['nro_expediente'] + ")")
    eid = int(sel_exp.split(' - ')[0])
    with st.form('form_alta'):
      m_alta = st.text_input('Médico que otorga el alta*')
      f_alta = st.date_input('Fecha de Alta', value=sec.ahora_local().date())
      obs_alta = st.text_area('Observaciones')
      if st.form_submit_button('Convalidar Alta') and sec.exigir('control_alta'):
        if m_alta:
          conn = sqlite3.connect(DB_NAME)
          conn.execute("UPDATE notas_medicas SET estado_alta = 'Alta Convalidada', fecha_alta_efectiva = ?, medico_alta = ?, observaciones_alta = ? WHERE id = ?",
                       (str(f_alta), m_alta, obs_alta, eid))
          conn.commit()
          conn.close()
          sec.registrar_auditoria('Control de Alta', 'UPDATE', f'Alta convalidada expediente ID {eid}', None)
          st.success('¡Alta convalidada con éxito!')
          st.rerun()
        else:
          st.warning('Indique el médico otorgante.')
  else:
    st.info('Sin expedientes pendientes de alta.')

elif menu == '4. Exámenes Periódicos y Anuales':
  st.markdown('## 🧪 Exámenes Periódicos')
  df_c = obtener_cadetes()
  if not df_c.empty:
    sel = st.selectbox('Cadete', (df_c['id_legajo'].astype(str) + ' - ' + df_c['apellido_nombre']).tolist())
    id_l = sel.split(' - ')[0]
    with st.form('f_ex'):
      ddjj = st.selectbox('DDJJ', ['Aprobada', 'Observada'])
      visus = st.text_input('Visus')
      hem = st.selectbox('Hemograma', ['Normal', 'Alterado'])
      el = st.selectbox('Electro', ['Normal', 'Patológico'])
      apt = st.selectbox('Aptitud', ['Apto', 'No Apto'])
      if st.form_submit_button('Guardar') and sec.exigir('examenes_periodicos'):
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT INTO examenes_periodicos (id_legajo, anio, ddjj_enfermedades, visus, hemograma, orina, electrocardiograma, aptitud_fisica, toxicologico, beta_hcg, fecha_registro) VALUES (?, '2026', ?, ?, ?, 'Normal', ?, ?, 'Negativo', 'Negativo', ?)",
                     (id_l, ddjj, visus, hem, el, apt, str(sec.ahora_local())))
        conn.commit()
        conn.close()
        sec.registrar_auditoria('Exámenes', 'INSERT', 'Examen periódico guardado', id_l)
        st.success('¡Guardado!')

elif menu == '5. Historia Clínica Integral':
  st.markdown(
      '<div class="pro-header"><p class="pro-title">📁 Legajo e Historia Clínica Integral</p><p class="pro-subtitle">Informe consolidado por cadete, filtrado por año o histórico, con opciones de edición/eliminación y exportación a PDF oficial.</p></div>',
      unsafe_allow_html=True,
  )
  df_cadetes = obtener_cadetes()
  if not df_cadetes.empty:
    col_hc1, col_hc2 = st.columns([2, 1])
    with col_hc1:
      busq_hc = st.text_input('🔍 Buscar Cadete por Apellido o Legajo', placeholder='Escriba para buscar...')
    with col_hc2:
      anios_disp = ['Historial Completo', '2026', '2025', '2024']
      anio_seleccionado = st.selectbox('📅 Filtrar por Período / Año', anios_disp)
      filtro_anio = None if anio_seleccionado == 'Historial Completo' else anio_seleccionado
      
    df_hc_view = df_cadetes.copy()
    if busq_hc:
      busq_hc_str = str(busq_hc)
      df_hc_view = df_hc_view[
          df_hc_view['apellido_nombre'].str.contains(busq_hc_str, case=False, na=False)
          | df_hc_view['id_legajo'].astype(str).str.contains(busq_hc_str, case=False, na=False)
      ]
    if not df_hc_view.empty:
      lista_hc = (df_hc_view['id_legajo'].astype(str) + ' - ' + df_hc_view['apellido_nombre']).tolist()
      seleccion_hc = st.selectbox('Seleccione el Cadete', lista_hc)
      id_leg_hc = seleccion_hc.split(' - ')[0]
      sec.auditar_vista('Historia Clínica', f'Consulta historia clínica (Filtro: {anio_seleccionado})', id_leg_hc)
      cad_hc = df_cadetes[df_cadetes['id_legajo'].astype(str) == id_leg_hc].iloc[0]
      
      st.markdown(
          '<div class="profile-card"><h2>'
          + _html.escape(str(cad_hc['apellido_nombre']))
          + '</h2><p>Legajo: <b>'
          + _html.escape(str(cad_hc['id_legajo']))
          + '</b> | Curso: <b>'
          + _html.escape(str(cad_hc['curso']))
          + '</b> | DNI: <b>'
          + _html.escape(str(cad_hc['dni']))
          + '</b> | Período: <b>' + anio_seleccionado + '</b></p></div>',
          unsafe_allow_html=True,
      )
      
      conn = sqlite3.connect(DB_NAME)
      df_nm_hc = pd.read_sql_query('SELECT * FROM notas_medicas WHERE id_legajo = ?', conn, params=(id_leg_hc,))
      df_int_hc = pd.read_sql_query('SELECT * FROM primera_intervencion WHERE id_legajo = ?', conn, params=(id_leg_hc,))
      df_doc_hc = pd.read_sql_query('SELECT * FROM legajo_documentos WHERE id_legajo = ?', conn, params=(id_leg_hc,))
      conn.close()
      
      if st.button('📄 Generar e Imprimir Historia Clínica en PDF Oficial (Consolidado)'):
        pdf_hc_path = generar_pdf_historia_clinica(cad_hc, df_nm_hc, df_int_hc, filtro_anio)
        sec.registrar_auditoria('Historia Clínica', 'EXPORT', f'Generación de PDF de Historia Clínica Completa ({anio_seleccionado})', id_leg_hc)
        st.success('¡PDF de Historia Clínica Integral generado correctamente con todos los registros!')
        if os.path.exists(pdf_hc_path):
          with open(pdf_hc_path, 'rb') as f_pdf:
            st.download_button(
                label='⬇️ Descargar Archivo PDF de Historia Clínica',
                data=f_pdf.read(),
                file_name=os.path.basename(pdf_hc_path),
                mime='application/pdf',
                key='dl_pdf_hc_final'
            )
            
      st.markdown('<br>', unsafe_allow_html=True)
      st.markdown('### 📋 Notas Médicas, Certificados y Estudios Anexos (Gestión y Edición)')
      
      df_nm_vis = df_nm_hc.copy()
      if filtro_anio and not df_nm_vis.empty:
        df_nm_vis = df_nm_vis[df_nm_vis['fecha_desde'].astype(str).str.contains(str(filtro_anio), na=False)]
        
      if not df_nm_vis.empty:
        for _, r in df_nm_vis.iterrows():
          nota_id = int(r['id'])
          exp_no = _html.escape(str(r['nro_expediente']))
          diag = _html.escape(str(r['diagnostico']))
          med = _html.escape(str(r['medico']))
          rep = _html.escape(str(r['tipo_reposo']))
          f_des = _html.escape(str(r['fecha_desde']))
          f_has = _html.escape(str(r['fecha_hasta']))
          est = _html.escape(str(r['estado_alta']))
          cert_ind = str(r['certificados_indicaciones']) if pd.notna(r['certificados_indicaciones']) else 'Sin anexos'
          an_est = str(r['analisis_estudios']) if pd.notna(r['analisis_estudios']) else 'Sin estudios'
          
          card_html = (
              '<div class="panel" style="border-left: 4px solid #38BDF8;">'
              '<h4>Expediente: ' + exp_no + ' | Diagnóstico: ' + diag + '</h4>'
              '<p><b>ID Registro:</b> ' + str(nota_id) + ' | <b>Médico:</b> ' + med + ' | <b>Reposo:</b> ' + rep + ' (' + f_des + ' al ' + f_has + ') | <b>Estado:</b> ' + est + '</p>'
              '<p><b>Certificados e Indicaciones:</b><br>' + _html.escape(cert_ind) + '</p>'
              '<p><b>Análisis y Estudios:</b><br>' + _html.escape(an_est) + '</p></div>'
          )
          st.markdown(card_html, unsafe_allow_html=True)
          
          col_btn1, col_btn2 = st.columns(2)
          with col_btn1:
            with st.expander(f"✏️ Editar Nota / Expediente {r['nro_expediente']} (ID: {nota_id})"):
              with st.form(f"form_edit_nota_{nota_id}"):
                e_exp = st.text_input("Nro. Expediente", value=r['nro_expediente'], key=f"ex_{nota_id}")
                e_med = st.text_input("Médico", value=r['medico'], key=f"me_{nota_id}")
                e_diag = st.text_area("Diagnóstico", value=r['diagnostico'], key=f"di_{nota_id}")
                e_tipo = st.selectbox("Tipo Reposo", ['Reposo Domiciliario', 'Reposo Académico', 'Internación', 'ART'], index=['Reposo Domiciliario', 'Reposo Académico', 'Internación', 'ART'].index(r['tipo_reposo']) if r['tipo_reposo'] in ['Reposo Domiciliario', 'Reposo Académico', 'Internación', 'ART'] else 0, key=f"ti_{nota_id}")
                e_desde = st.date_input("Desde", value=datetime.strptime(r['fecha_desde'], '%Y-%m-%d').date() if r['fecha_desde'] else sec.ahora_local().date(), key=f"d_{nota_id}")
                e_hasta = st.date_input("Hasta", value=datetime.strptime(r['fecha_hasta'], '%Y-%m-%d').date() if r['fecha_hasta'] else sec.ahora_local().date(), key=f"h_{nota_id}")
                
                if st.form_submit_button("💾 Guardar Cambios") and sec.exigir('notas_medicas'):
                  conn = sqlite3.connect(DB_NAME)
                  conn.execute("UPDATE notas_medicas SET nro_expediente = ?, medico = ?, diagnostico = ?, tipo_reposo = ?, fecha_desde = ?, fecha_hasta = ? WHERE id = ?",
                               (e_exp, e_med, e_diag, e_tipo, str(e_desde), str(e_hasta), nota_id))
                  conn.commit()
                  conn.close()
                  sec.registrar_auditoria('Notas Médicas', 'UPDATE', f"Actualización de nota ID {nota_id}", id_leg_hc)
                  st.success("¡Nota médica actualizada con éxito!")
                  st.rerun()
          with col_btn2:
            with st.expander(f"🗑️ Eliminar Nota {r['nro_expediente']} (ID: {nota_id})"):
              with st.form(f"form_del_nota_{nota_id}"):
                st.warning("⚠️ Esta acción es irreversible. Ingrese su contraseña para confirmar la eliminación.")
                pw_conf = st.text_input("Contraseña del usuario actual", type="password", key=f"pw_del_{nota_id}")
                if st.form_submit_button("Confirmar Eliminación Segura") and sec.exigir('notas_medicas'):
                  usr_actual = st.session_state.get('auth_user', {})
                  if usr_actual:
                    conn_v = sqlite3.connect(DB_NAME)
                    conn_v.row_factory = sqlite3.Row
                    u_db = conn_v.execute("SELECT * FROM usuarios WHERE username = ?", (usr_actual.get('username'),)).fetchone()
                    conn_v.close()
                    
                    if u_db and sec.verify_password(pw_conf, u_db['password_hash']):
                      conn = sqlite3.connect(DB_NAME)
                      conn.execute("DELETE FROM notas_medicas WHERE id = ?", (nota_id,))
                      conn.commit()
                      conn.close()
                      sec.registrar_auditoria('Notas Médicas', 'DELETE', f"Eliminación segura de nota ID {nota_id} con contraseña confirmada", id_leg_hc)
                      st.success("¡Nota médica eliminada correctamente!")
                      st.rerun()
                    else:
                      st.error("Contraseña incorrecta. No se pudo autorizar la eliminación.")
                  else:
                    st.error("Sesión no válida.")
          st.markdown('<hr style="border-color: #1C2740; margin: 1.5rem 0;">', unsafe_allow_html=True)
      else:
        st.info(f'No hay notas médicas registradas para el período ({anio_seleccionado}).')
        
      st.markdown('### 🩺 Intervenciones de Guardia Registradas')
      df_int_vis = df_int_hc.copy()
      if filtro_anio and not df_int_vis.empty:
        df_int_vis = df_int_vis[df_int_vis['fecha_hora'].astype(str).str.contains(str(filtro_anio), na=False)]
      if not df_int_vis.empty:
        st.dataframe(df_int_vis[['id', 'fecha_hora', 'profesional_atiende', 'sintomas', 'presion', 'saturacion', 'temperatura', 'derivacion']], use_container_width=True)
        
        with st.form("form_del_intervencion"):
          id_inter_del = st.number_input("ID de Intervención a eliminar por error", min_value=1, step=1)
          if st.form_submit_button("🗑️ Eliminar Intervención de Guardia") and sec.exigir('primera_intervencion'):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("DELETE FROM primera_intervencion WHERE id = ? AND id_legajo = ?", (int(id_inter_del), id_leg_hc))
            conn.commit()
            conn.close()
            sec.registrar_auditoria('Intervención', 'DELETE', f"Eliminación de intervención ID {id_inter_del}", id_leg_hc)
            st.success("¡Intervención eliminada con éxito!")
            st.rerun()
      else:
        st.info(f'No hay atenciones de guardia para el período ({anio_seleccionado}).')
        
      st.markdown('### 📥 Documentos en PDF Anexados al Legajo Digital')
      if not df_doc_hc.empty:
        for _, doc_row in df_doc_hc.iterrows():
          t_doc = str(doc_row['titulo_documento'])
          f_sub = str(doc_row['fecha_subida'])
          f_path = str(doc_row['archivo_nombre'])
          doc_id = str(doc_row['id'])
          st.markdown(f'- **{t_doc}** (Subido el {f_sub})')
          c_d1, c_d2 = st.columns([2, 1])
          with c_d1:
            if os.path.exists(f_path):
              with open(f_path, 'rb') as f:
                st.download_button(
                    label=f'📥 Descargar PDF: {os.path.basename(f_path)}',
                    data=f.read(),
                    file_name=os.path.basename(f_path),
                    mime='application/pdf',
                    key=f'dl_{doc_id}',
                    on_click=sec.registrar_auditoria,
                    args=('Documentos', 'EXPORT', f'Descarga de PDF: {os.path.basename(f_path)}', id_leg_hc),
                )
          with c_d2:
            if st.button(f"🗑️ Borrar Archivo", key=f"del_doc_{doc_id}") and sec.exigir('notas_medicas'):
              try:
                if os.path.exists(f_path): os.remove(f_path)
              except Exception: pass
              conn = sqlite3.connect(DB_NAME)
              conn.execute("DELETE FROM legajo_documentos WHERE id = ?", (doc_id,))
              conn.commit()
              conn.close()
              sec.registrar_auditoria('Documentos', 'DELETE', f"Eliminación de documento ID {doc_id}", id_leg_hc)
              st.success("¡Documento borrado!")
              st.rerun()
      else:
        st.info('No hay documentos PDF en el legajo digital todavía.')

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
      if st.form_submit_button('Guardar Baja') and sec.exigir('examen_baja'):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO examen_baja (id_legajo, fecha_baja, motivo,'
            ' estado_salud_egreso, observaciones_medicas) VALUES (?, ?, ?, ?, ?)',
            (id_legajo, str(sec.ahora_local().date()), motivo, estado, ''),
        )
        conn.commit()
        conn.close()
        sec.registrar_auditoria('Examen de Baja', 'INSERT', f'Examen de baja registrado (motivo: {motivo})', id_legajo)
        st.success('¡Baja registrada con éxito!')

elif menu == '7. Informes y Análisis de Datos (Spark)':
  st.markdown(
      '<div class="pro-header"><p class="pro-title">📊 Inteligencia Sanitaria & Analytics</p><p class="pro-subtitle">Cuadro de mando directivo, morbilidad institucional y analítica avanzada de salud en tiempo real.</p></div>',
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
  df_e_rep = pd.read_sql_query(
      'SELECT e.*, c.curso, c.apellido_nombre, c.genero FROM examenes_periodicos e LEFT JOIN cadetes c ON e.id_legajo = c.id_legajo',
      conn,
  )
  conn.close()

  # Tarjetas superiores directivas
  col_s1, col_s2, col_s3, col_s4 = st.columns(4)
  with col_s1:
    st.markdown(kpi_card('👥', len(df_c_rep), 'Total compañía', '#38BDF8', 'Base activa'), unsafe_allow_html=True)
  with col_s2:
    st.markdown(kpi_card('🩺', len(df_i_rep), 'Atenciones guardia', '#A78BFA', 'Intervenciones'), unsafe_allow_html=True)
  with col_s3:
    st.markdown(kpi_card('📋', len(df_n_rep), 'Expedientes médicos', '#34D399', 'Notas y reposos'), unsafe_allow_html=True)
  with col_s4:
    pend_count = len(df_n_rep[df_n_rep['estado_alta'] == 'Pendiente']) if not df_n_rep.empty else 0
    st.markdown(kpi_card('⏳', pend_count, 'Altas pendientes', '#FBBF24', 'Sin convalidar'), unsafe_allow_html=True)

  st.markdown('<br>', unsafe_allow_html=True)
  spark_tab1, spark_tab2, spark_tab3, spark_tab4, spark_tab5 = st.tabs([
      '📈 Morbilidad y Diagnósticos',
      '🏥 Guardia y Derivaciones',
      '⏳ Tiempos y Reposos',
      '🧪 Prevención y Anuales',
      '🔬 Análisis Avanzado',
  ])

  with spark_tab1:
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><h3>Análisis de Morbilidad Institucional</h3><p style="color: var(--muted); font-size: 0.88rem;">Distribución de consultas por curso y principales diagnósticos registrados en notas médicas.</p></div>', unsafe_allow_html=True)
    
    col_m1, col_m2 = st.columns(2, gap='medium')
    with col_m1:
      st.markdown('#### 📚 Atenciones de Guardia por Curso')
      if not df_i_rep.empty:
        df_curso = df_i_rep.groupby('curso').size().reset_index(name='Atenciones')
        st.dataframe(df_curso, use_container_width=True)
        try:
          import altair as alt
          chart_curso = alt.Chart(df_curso).mark_bar(color='#38BDF8', cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=28).encode(
              x=alt.X('curso:N', axis=alt.Axis(title=None, labelColor='#8A97B1', domainColor='#1C2740', tickColor='#1C2740', labelAngle=0)),
              y=alt.Y('Atenciones:Q', axis=alt.Axis(title=None, tickMinStep=1, labelColor='#8A97B1', gridColor='#1C2740', domain=False)),
              tooltip=['curso:N', 'Atenciones:Q']
          ).properties(height=200, background='transparent').configure_view(strokeWidth=0)
          st.altair_chart(chart_curso, use_container_width=True, theme=None)
        except Exception:
          st.bar_chart(df_curso.set_index('curso'), color='#38BDF8')
      else:
        st.info('Sin registros de guardia suficientes.')
        
    with col_m2:
      st.markdown('#### 🩺 Tipos de Reposo Otorgados')
      if not df_n_rep.empty:
        df_rep = df_n_rep.groupby('tipo_reposo').size().reset_index(name='Cantidad')
        st.dataframe(df_rep, use_container_width=True)
        try:
          import altair as alt
          chart_rep = alt.Chart(df_rep).mark_bar(color='#A78BFA', cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=28).encode(
              x=alt.X('tipo_reposo:N', axis=alt.Axis(title=None, labelColor='#8A97B1', domainColor='#1C2740', tickColor='#1C2740', labelAngle=-10)),
              y=alt.Y('Cantidad:Q', axis=alt.Axis(title=None, tickMinStep=1, labelColor='#8A97B1', gridColor='#1C2740', domain=False)),
              tooltip=['tipo_reposo:N', 'Cantidad:Q']
          ).properties(height=200, background='transparent').configure_view(strokeWidth=0)
          st.altair_chart(chart_rep, use_container_width=True, theme=None)
        except Exception:
          st.bar_chart(df_rep.set_index('tipo_reposo'), color='#A78BFA')
      else:
        st.info('Sin registros de reposos suficientes.')

  with spark_tab2:
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><h3>Demanda en Centros de Derivación Sanitaria</h3><p style="color: var(--muted); font-size: 0.88rem;">Volumen y frecuencia de derivaciones externas e internas solicitadas por el gabinete.</p></div>', unsafe_allow_html=True)
    if not df_i_rep.empty:
      df_deriv = df_i_rep.groupby('derivacion').size().reset_index(name='Frecuencia').sort_values(by='Frecuencia', ascending=False)
      c_d1, c_d2 = st.columns([1, 1.5], gap='large')
      with c_d1:
        st.dataframe(df_deriv, use_container_width=True)
      with c_d2:
        try:
          import altair as alt
          chart_deriv = alt.Chart(df_deriv).mark_bar(color='#34D399', cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=28).encode(
              x=alt.X('derivacion:N', axis=alt.Axis(title=None, labelColor='#8A97B1', domainColor='#1C2740', tickColor='#1C2740', labelAngle=-15)),
              y=alt.Y('Frecuencia:Q', axis=alt.Axis(title=None, tickMinStep=1, labelColor='#8A97B1', gridColor='#1C2740', domain=False)),
              tooltip=['derivacion:N', 'Frecuencia:Q']
          ).properties(height=220, background='transparent').configure_view(strokeWidth=0)
          st.altair_chart(chart_deriv, use_container_width=True, theme=None)
        except Exception:
          st.bar_chart(df_deriv.set_index('derivacion'), color='#34D399')
    else:
      st.info('No hay datos de derivación suficientes.')

  with spark_tab3:
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><h3>Estado de Expedientes y Cierre de Reposos</h3><p style="color: var(--muted); font-size: 0.88rem;">Monitoreo del estado administrativo de alta para cada expediente médico.</p></div>', unsafe_allow_html=True)
    if not df_n_rep.empty:
      df_est = df_n_rep.groupby('estado_alta').size().reset_index(name='Total')
      st.dataframe(df_est, use_container_width=True)
      st.markdown('#### 📋 Visor Consolidado de Notas Médicas')
      st.dataframe(df_n_rep[['nro_expediente', 'id_legajo', 'apellido_nombre', 'curso', 'medico', 'tipo_reposo', 'fecha_desde', 'fecha_hasta', 'estado_alta']], use_container_width=True)
    else:
      st.info('No hay notas médicas registradas.')

  with spark_tab4:
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><h3>Salud Preventiva y Exámenes Anuales</h3><p style="color: var(--muted); font-size: 0.88rem;">Control de declaraciones juradas, aptitud física y trazabilidad de controles trimestrales (Beta HCG).</p></div>', unsafe_allow_html=True)
    if not df_e_rep.empty:
      st.markdown('#### 📊 Registro General de Exámenes Periódicos')
      st.dataframe(df_e_rep, use_container_width=True)
    else:
      st.info('No hay exámenes periódicos registrados todavía.')

  with spark_tab5:
    analitica.render(DB_NAME)

elif menu == '8. Gestión de Usuarios':
  sec.pagina_usuarios()

elif menu == '9. Auditoría del Sistema':
  sec.pagina_auditoria()

else:
  st.markdown(f'## Módulo: {menu}')
