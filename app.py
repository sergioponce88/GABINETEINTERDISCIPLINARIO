from datetime import datetime, date, timedelta
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

def _buscar_logo(nombre):
  """Busca el archivo (sin distinguir mayúsculas) en la raíz o en carpetas comunes."""
  for carpeta in ('.', 'assets', 'imagenes', 'img'):
    if os.path.isdir(carpeta):
      for f in os.listdir(carpeta):
        if f.lower() == nombre.lower():
          return os.path.join(carpeta, f)
  return None


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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

:root {
  --bg: #05070D;
  --surface: #0C1220;
  --surface-2: #111A2E;
  --border: #1C2740;
  --text: #E6EAF2;
  --muted: #8A97B1;
  --accent: #3B82F6;
  --accent-2: #22D3EE;
  --ok: #10B981;
  --warn: #F59E0B;
  --crit: #EF4444;
  --info: #38BDF8;
}

html, body, [class*="css"], .stApp, button, input, textarea, select {
  font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif !important;
}
.stApp {
  background:
    radial-gradient(900px 400px at 85% -10%, rgba(59,130,246,0.10), transparent 60%),
    radial-gradient(700px 380px at -5% 0%, rgba(34,211,238,0.06), transparent 60%),
    var(--bg);
  color: var(--text);
}
[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1400px; }

h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  color: #FFFFFF !important;
  font-weight: 800 !important;
  letter-spacing: -0.01em;
}
h3 { font-size: 1.25rem !important; }
p, li, label, span, div[data-testid="stMarkdownContainer"] { color: inherit; }
label, .stTextInput label, .stSelectbox label, .stMultiSelect label, .stDateInput label,
.stTextArea label, .stNumberInput label {
  color: var(--muted) !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0A1020 0%, #070B16 100%);
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
.brand { display: flex; align-items: center; gap: 0.85rem; padding: 0.4rem 0.2rem 1.1rem 0.2rem;
  border-bottom: 1px solid var(--border); margin-bottom: 1.2rem; }
.brand-logo { width: 46px; height: 46px; border-radius: 13px; display: grid; place-items: center;
  font-size: 1.5rem; background: linear-gradient(135deg, #2563EB, #22D3EE);
  box-shadow: 0 8px 24px rgba(37,99,235,0.45); }
.brand-name { font-weight: 800; font-size: 1.02rem; color: #FFFFFF; letter-spacing: 0.01em; line-height: 1.15; }
.brand-sub { font-size: 0.74rem; color: var(--muted); margin-top: 0.15rem; }
.brand-logo.has-img { background: none; box-shadow: none; width: 54px; height: 58px; }
.brand-logo img { width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(0 6px 14px rgba(0,0,0,0.55)); }
.nav-label { font-size: 0.68rem; font-weight: 700; color: #5F6C88; text-transform: uppercase;
  letter-spacing: 0.12em; margin: 0 0 0.5rem 0.3rem; }
.side-foot { margin-top: 2rem; padding: 0.8rem 0.9rem; border: 1px solid var(--border); border-radius: 12px;
  font-size: 0.74rem; color: var(--muted); background: rgba(17,26,46,0.6); }

[data-testid="stSidebar"] [role="radiogroup"] { gap: 0.2rem; }
[data-testid="stSidebar"] label[data-baseweb="radio"] {
  width: 100%; padding: 0.62rem 0.85rem; border-radius: 11px; border: 1px solid transparent;
  transition: all 0.15s ease; cursor: pointer; margin: 0;
}
[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child { display: none; }
[data-testid="stSidebar"] label[data-baseweb="radio"] p,
[data-testid="stSidebar"] label[data-baseweb="radio"] div[data-testid="stMarkdownContainer"] {
  color: #A9B4CC !important; font-weight: 600; font-size: 0.9rem; text-transform: none; letter-spacing: 0;
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:hover { background: rgba(59,130,246,0.08); }
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
  background: linear-gradient(90deg, rgba(59,130,246,0.22), rgba(59,130,246,0.05));
  border-color: rgba(59,130,246,0.35);
  box-shadow: inset 3px 0 0 var(--accent);
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) p,
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) div[data-testid="stMarkdownContainer"] {
  color: #FFFFFF !important;
}

/* ---------- Hero ---------- */
.hero { position: relative; overflow: hidden; display: flex; justify-content: space-between; align-items: center;
  gap: 1.5rem; flex-wrap: wrap; padding: 2rem 2.2rem; border-radius: 22px; margin-bottom: 1.4rem;
  border: 1px solid #22305A;
  background:
    radial-gradient(600px 220px at 100% 0%, rgba(34,211,238,0.18), transparent 65%),
    radial-gradient(500px 260px at 0% 100%, rgba(99,102,241,0.25), transparent 65%),
    linear-gradient(135deg, #0B1330 0%, #121B45 100%);
  box-shadow: 0 24px 50px -20px rgba(0,0,0,0.7); }
.hero::after { content: ''; position: absolute; inset: 0; pointer-events: none; opacity: 0.35;
  background-image: linear-gradient(rgba(148,163,184,0.07) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(148,163,184,0.07) 1px, transparent 1px);
  background-size: 34px 34px;
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 70%); mask-image: linear-gradient(90deg, transparent, #000 70%); }
.hero > * { position: relative; z-index: 1; }
.hero-eyebrow { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent-2); }
.hero-main > div:last-child { flex: 1 1 320px; min-width: 0; max-width: 640px; }
.hero-org { font-size: 0.95rem; font-weight: 600; color: #7DD3FC; margin-top: 0.55rem; letter-spacing: 0.01em; }
.hero-title { font-size: 1.6rem; font-weight: 800; color: #FFFFFF; margin: 0.25rem 0 0.35rem 0; letter-spacing: -0.02em; line-height: 1.15; }
.hero-sub { font-size: 0.98rem; color: #A5B4D4; margin: 0; max-width: 640px; }
.hero-right { text-align: right; display: flex; flex-direction: column; gap: 0.6rem; align-items: flex-end; }
.chip { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.85rem; border-radius: 999px;
  font-size: 0.76rem; font-weight: 700; border: 1px solid rgba(16,185,129,0.4); color: #6EE7B7; background: rgba(16,185,129,0.1); }
.chip .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 0 4px rgba(16,185,129,0.2); }
.hero-date { font-size: 0.9rem; font-weight: 600; color: #C7D2EE; }

.hero-main { display: flex; align-items: center; gap: 1.7rem; flex-wrap: wrap; }
.hero-logos { display: flex; align-items: center; gap: 1.1rem; padding-right: 1.7rem; border-right: 1px solid rgba(148,163,184,0.22); }
.hero-logos img { height: 98px; width: auto; filter: drop-shadow(0 10px 20px rgba(0,0,0,0.6)); transition: transform 0.2s ease; }
.hero-logos img:hover { transform: scale(1.06) translateY(-2px); }

/* ---------- KPI ---------- */
.kpi { position: relative; overflow: hidden; display: flex; align-items: center; gap: 1rem; padding: 1.15rem 1.3rem;
  border-radius: 18px; border: 1px solid var(--border);
  background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%);
  transition: transform 0.18s ease, border-color 0.18s ease; }
.kpi:hover { transform: translateY(-3px); border-color: var(--c); }
.kpi::before { content: ''; position: absolute; left: 0; top: 14%; bottom: 14%; width: 3px; border-radius: 0 4px 4px 0; background: var(--c); }
.kpi-icon { flex: 0 0 auto; width: 50px; height: 50px; border-radius: 14px; display: grid; place-items: center; font-size: 1.45rem;
  background: color-mix(in srgb, var(--c) 16%, transparent); border: 1px solid color-mix(in srgb, var(--c) 35%, transparent); }
.kpi-value { font-size: 2rem; font-weight: 800; color: #FFFFFF; line-height: 1; letter-spacing: -0.02em; }
.kpi-label { font-size: 0.72rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.4rem; }
.kpi-sub { font-size: 0.74rem; color: #64748B; margin-top: 0.15rem; }

/* ---------- Alertas ---------- */
.al { --c: var(--info); display: flex; gap: 1rem; align-items: flex-start; padding: 1rem 1.2rem; margin-bottom: 0.75rem;
  border-radius: 16px; border: 1px solid var(--border); position: relative; overflow: hidden;
  background: linear-gradient(90deg, color-mix(in srgb, var(--c) 10%, #0C1220) 0%, #0C1220 60%);
  transition: transform 0.15s ease, border-color 0.15s ease; }
.al:hover { transform: translateX(3px); border-color: color-mix(in srgb, var(--c) 55%, transparent); }
.al::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--c); }
.al-0 { --c: var(--crit); } .al-1 { --c: var(--warn); } .al-2 { --c: var(--info); }
.al-icon { flex: 0 0 auto; width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; font-size: 1.2rem;
  background: color-mix(in srgb, var(--c) 18%, transparent); }
.al-main { flex: 1 1 auto; min-width: 0; }
.al-pill { display: inline-block; padding: 0.18rem 0.6rem; border-radius: 999px; font-size: 0.66rem; font-weight: 800;
  text-transform: uppercase; letter-spacing: 0.07em; color: var(--c);
  background: color-mix(in srgb, var(--c) 14%, transparent); border: 1px solid color-mix(in srgb, var(--c) 40%, transparent); }
.al-name { font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin-top: 0.4rem; }
.al-detail { font-size: 0.88rem; color: #A9B4CC; margin-top: 0.15rem; line-height: 1.45; }
.al-meta { flex: 0 0 auto; display: flex; flex-direction: column; gap: 0.3rem; align-items: flex-end; }
.tag { font-size: 0.72rem; font-weight: 600; color: #B8C3DB; padding: 0.2rem 0.6rem; border-radius: 8px;
  background: rgba(148,163,184,0.1); border: 1px solid rgba(148,163,184,0.15); white-space: nowrap; }
.alert-ok { display: flex; align-items: center; gap: 1rem; padding: 1.4rem 1.5rem; border-radius: 16px;
  border: 1px solid rgba(16,185,129,0.35); background: linear-gradient(90deg, rgba(16,185,129,0.14), rgba(16,185,129,0.03));
  color: #A7F3D0; font-weight: 600; }
.alert-ok .big { font-size: 1.8rem; }

/* ---------- Paneles ---------- */
.panel { border: 1px solid var(--border); border-radius: 18px; padding: 1.2rem 1.3rem; margin-bottom: 1rem;
  background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); }
.panel-title { font-size: 0.74rem; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.2rem; }
.panel-big { font-size: 1.7rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em; }
.panel-note { font-size: 0.78rem; color: #64748B; margin-top: 0.35rem; }
.bar { height: 9px; border-radius: 99px; background: #18233D; overflow: hidden; margin-top: 0.7rem; }
.bar > div { height: 100%; border-radius: 99px; background: linear-gradient(90deg, #2563EB, #22D3EE); }
.section-head { display: flex; justify-content: space-between; align-items: end; margin: 0.3rem 0 0.9rem 0; }
.section-head .t { font-size: 1.15rem; font-weight: 800; color: #FFFFFF; }
.section-head .s { font-size: 0.82rem; color: var(--muted); }

/* ---------- Componentes Streamlit ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 0.4rem; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] { height: 46px; padding: 0 1rem; border-radius: 10px 10px 0 0; background: transparent; }
.stTabs [data-baseweb="tab"] p { color: var(--muted) !important; font-weight: 600; font-size: 0.92rem; }
.stTabs [data-baseweb="tab"]:hover p { color: #FFFFFF !important; }
.stTabs [aria-selected="true"] p { color: #FFFFFF !important; }
.stTabs [data-baseweb="tab-highlight"] { background: linear-gradient(90deg, #3B82F6, #22D3EE) !important; height: 3px; border-radius: 3px; }
.stTabs [data-baseweb="tab-border"] { background: transparent !important; }

.stTextInput input, .stTextArea textarea, .stDateInput input, .stNumberInput input,
[data-baseweb="select"] > div, [data-baseweb="input"] {
  background-color: var(--surface) !important; color: #FFFFFF !important;
  border: 1px solid var(--border) !important; border-radius: 12px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.2) !important; }
[data-baseweb="tag"] { background: rgba(59,130,246,0.2) !important; border-radius: 8px !important; }
[data-baseweb="tag"] span { color: #BFDBFE !important; text-transform: none; letter-spacing: 0; font-weight: 600; }
[data-baseweb="popover"] ul { background: var(--surface-2) !important; }

.stButton > button, .stFormSubmitButton > button {
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%); color: #FFFFFF; font-weight: 700; border: none;
  border-radius: 12px; padding: 0.6rem 1.4rem; box-shadow: 0 6px 18px rgba(37,99,235,0.35); transition: all 0.15s ease; }
.stButton > button:hover, .stFormSubmitButton > button:hover { transform: translateY(-1px); box-shadow: 0 10px 24px rgba(37,99,235,0.5); color: #FFFFFF; }
.stDownloadButton > button { background: var(--surface-2); color: #DCE4F5; font-weight: 600; border: 1px solid var(--border);
  border-radius: 12px; box-shadow: none; }
.stDownloadButton > button:hover { border-color: var(--accent); color: #FFFFFF; background: var(--surface-2); }

[data-testid="stExpander"] { border: 1px solid var(--border) !important; border-radius: 14px !important; background: var(--surface); }
[data-testid="stExpander"] summary p { color: #DCE4F5 !important; font-weight: 600; text-transform: none; letter-spacing: 0; font-size: 0.9rem; }
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
[data-testid="stForm"] { border: 1px solid var(--border); border-radius: 18px; background: var(--surface); padding: 1.3rem; }
[data-testid="stAlert"] { border-radius: 14px; }
hr { border-color: var(--border) !important; }

/* ---------- Compatibilidad con otras pantallas ---------- */
.pro-header { background: linear-gradient(135deg, #0B1330 0%, #121B45 100%); padding: 2rem; border-radius: 20px;
  border: 1px solid #22305A; color: white; margin-bottom: 1.5rem; }
.pro-title { font-size: 2rem; font-weight: 800; margin: 0; color: #FFFFFF; }
.pro-subtitle { font-size: 1rem; color: #93C5FD; margin-top: 0.4rem; margin-bottom: 0; }
.metric-card { background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); padding: 1.3rem; border-radius: 16px;
  border: 1px solid var(--border); text-align: center; }
.metric-value { font-size: 2.1rem; font-weight: 800; color: #38BDF8; }
.metric-label { font-size: 0.74rem; color: var(--muted); text-transform: uppercase; font-weight: 700; letter-spacing: 0.08em; margin-top: 0.35rem; }
.profile-card { background: linear-gradient(135deg, #0F172A 0%, #111B33 100%); padding: 1.5rem 1.75rem; border-radius: 18px;
  border: 1px solid var(--border); border-left: 4px solid var(--accent); margin-bottom: 1.5rem; }
.alert-card { background: rgba(120,53,15,0.35); border: 1px solid #B45309; padding: 1.1rem; border-radius: 14px; margin-bottom: 1rem; color: #FEF3C7; }

@media (max-width: 768px) {
  .hero-logos { border-right: none; padding-right: 0; } .hero-logos img { height: 64px; }
  .hero { padding: 1.4rem; } .hero-title { font-size: 1.25rem; } .hero-right { align-items: flex-start; text-align: left; }
  .al { flex-wrap: wrap; } .al-meta { flex-direction: row; align-items: flex-start; }
}

</style>
""", unsafe_allow_html=True)

DB_NAME = 'gabinete_iesp.db'
EXCEL_FILE = 'LISTADO DE COMPAÑIA DE CADETES AÑO 2026 PARA D1.xlsx'
UPLOAD_DIR = 'documentos_legajos'
if not os.path.exists(UPLOAD_DIR):
  os.makedirs(UPLOAD_DIR)


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
          'INSERT OR IGNORE INTO cadetes VALUES (?, ?, ?, ?, ?, ?, ?)',
          (id_leg, ap_nom, curso, dni, genero, f_nac, obs),
      )
      cargados += 1
    conn.commit()
    conn.close()
    return True, f'Sincronizados {cargados} cadetes.'
  except Exception as e:
    return False, str(e)


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
      ' diagnostico TEXT, tipo_reposo TEXT, fecha_desde TEXT, fecha_hasta TEXT,'
      ' medicamentos TEXT, certificados_indicaciones TEXT, analisis_estudios'
      ' TEXT, estado_alta TEXT DEFAULT "Pendiente")'
  )
  cursor.execute(
      'CREATE TABLE IF NOT EXISTS legajo_documentos (id INTEGER PRIMARY KEY'
      ' AUTOINCREMENT, id_legajo TEXT, titulo_documento TEXT, tipo_documento'
      ' TEXT, fecha_subida TEXT, archivo_nombre TEXT, observaciones TEXT)'
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

  for col, col_type in [
      ('certificados_indicaciones', 'TEXT'),
      ('analisis_estudios', 'TEXT'),
      ('medicamentos', 'TEXT'),
      ('estado_alta', 'TEXT DEFAULT "Pendiente"'),
  ]:
    try:
      cursor.execute(f'ALTER TABLE notas_medicas ADD COLUMN {col} {col_type};')
    except sqlite3.OperationalError:
      pass

  # Migración: asegurar columnas en primera_intervencion (DB con esquema viejo)
  for col, col_type in [
      ('id_legajo', 'TEXT'),
      ('fecha_hora', 'TEXT'),
      ('profesional_atiende', 'TEXT'),
      ('sintomas', 'TEXT'),
      ('presion', 'TEXT'),
      ('saturacion', 'TEXT'),
      ('derivacion', 'TEXT'),
  ]:
    try:
      cursor.execute(
          f'ALTER TABLE primera_intervencion ADD COLUMN {col} {col_type};'
      )
    except sqlite3.OperationalError:
      pass  # la columna ya existe

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


@st.cache_data(show_spinner=False)
def logo_uri(nombre, alto=120):
  """Devuelve el logo como data URI (PNG redimensionado) o '' si no existe."""
  ruta = _buscar_logo(nombre)
  if not ruta:
    return ''
  try:
    import base64
    import io
    from PIL import Image

    from PIL import ImageDraw, ImageFilter

    im = Image.open(ruta).convert('RGBA')
    # Los logos tienen zonas internas transparentes (ej. el círculo blanco).
    # Se rellenan de blanco para que se vean bien sobre el fondo oscuro.
    m = im.getchannel('A').point(lambda a: 255 if a < 16 else 0)
    if m.getpixel((0, 0)) == 255:
      ImageDraw.floodfill(m, (0, 0), 128)  # marca el exterior
      huecos = m.point(lambda v: 255 if v == 255 else 0).filter(
          ImageFilter.MaxFilter(5)
      )
      blanco = Image.new('RGBA', im.size, (255, 255, 255, 255))
      im = Image.composite(Image.alpha_composite(blanco, im), im, huecos)
    ancho = max(1, round(im.width * alto / im.height))
    im = im.resize((ancho, alto), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format='PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
  except Exception:
    return ''


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


_logo_gab = logo_uri('GABINETE.png', 116)
_brand_logo = (
    f'<div class="brand-logo has-img"><img src="{_logo_gab}" alt="Gabinete"></div>'
    if _logo_gab
    else '<div class="brand-logo">🛡️</div>'
)
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
}

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
    format_func=lambda x: f"{ICONOS_MENU.get(x, '•')}  {x}",
    label_visibility='collapsed',
)
st.sidebar.markdown(
    '<div class="side-foot">🔒 Información sanitaria confidencial.<br>Uso'
    ' exclusivo del personal autorizado.</div>',
    unsafe_allow_html=True,
)

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
  """Devuelve una lista de alertas ordenadas por gravedad."""

  def _txt(valor, defecto='-'):
    return defecto if pd.isna(valor) or str(valor).strip() == '' else str(valor)

  alertas = []

  # --- Reposos con alta pendiente (vencidos / por vencer / vigentes)
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

  # --- Beta HCG: último control por cadete (mujeres) con más de 90 días
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

  # --- Reincidencia: 3 o más intervenciones en 30 días
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
      '<div class="hero-title">Dirección de Gabinete Interdisciplinario de'
      ' Asesoramiento Psicopedagógico y Psicológico</div>'
      '<div class="hero-org">Dirección General de Institutos e Instrucción ·'
      ' Policía de Tucumán</div></div></div><div'
      ' class="hero-right"><div class="chip"><span class="dot"></span>Sistema'
      ' operativo</div>'
      f'<div class="hero-date">{fecha_larga_es(datetime.today().date())}</div>'
      '</div></div>',
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

  pendientes_alta = (
      len(df_n[df_n['estado_alta'] == 'Pendiente']) if not df_n.empty else 0
  )
  col1, col2, col3, col4 = st.columns(4)
  with col1:
    st.markdown(kpi_card('🎓', len(df_c), 'Cadetes en compañía', '#38BDF8', 'Total en base de datos'), unsafe_allow_html=True)
  with col2:
    st.markdown(kpi_card('🩺', len(df_i), 'Intervenciones de guardia', '#A78BFA', 'Registradas en total'), unsafe_allow_html=True)
  with col3:
    st.markdown(kpi_card('🧑‍⚕️', len(df_p), 'Staff del gabinete', '#34D399', 'Personal activo'), unsafe_allow_html=True)
  with col4:
    st.markdown(kpi_card('⏳', pendientes_alta, 'Altas pendientes', '#FBBF24', 'Requieren convalidación'), unsafe_allow_html=True)

  st.markdown('<br>', unsafe_allow_html=True)
  dash_tab1, dash_tab2, dash_tab3 = st.tabs([
      '🚨 Centro de Alertas y Vencimientos',
      '📋 Consulta General de Compañía',
      '⚡ Acciones Rápidas y Sincronización',
  ])
  with dash_tab1:
    from html import escape as _esc

    hoy = datetime.today().date()
    alertas = construir_alertas(df_n, df_e, df_i, hoy)
    n_crit = sum(1 for a in alertas if a['nivel'] == 0)
    n_warn = sum(1 for a in alertas if a['nivel'] == 1)
    n_info = sum(1 for a in alertas if a['nivel'] == 2)

    k1, k2, k3 = st.columns(3)
    with k1:
      st.markdown(kpi_card('🚨', n_crit, 'Alertas críticas', '#EF4444', 'Acción inmediata'), unsafe_allow_html=True)
    with k2:
      st.markdown(kpi_card('⚠️', n_warn, 'Requieren atención', '#F59E0B', 'Seguimiento próximo'), unsafe_allow_html=True)
    with k3:
      st.markdown(kpi_card('🛌', n_info, 'Reposos vigentes', '#38BDF8', 'Informativo'), unsafe_allow_html=True)
    st.markdown('<br>', unsafe_allow_html=True)

    f1, f2 = st.columns([2, 1])
    with f1:
      niveles_sel = st.multiselect(
          'Mostrar',
          ['Críticas', 'Requieren atención', 'Informativas'],
          default=['Críticas', 'Requieren atención'],
      )
    with f2:
      cursos = sorted({a['curso'] for a in alertas})
      curso_sel = st.selectbox('Curso', ['Todos'] + cursos)

    mapa_nivel = {'Críticas': 0, 'Requieren atención': 1, 'Informativas': 2}
    permitidos = {mapa_nivel[n] for n in niveles_sel}
    visibles = [
        a for a in alertas
        if a['nivel'] in permitidos
        and (curso_sel == 'Todos' or a['curso'] == curso_sel)
    ]
    iconos_nivel = {0: '🚨', 1: '⏰', 2: '🛌'}
    etiquetas_nivel = {0: 'Crítica', 1: 'Atención', 2: 'Informativa'}

    # Cobertura de exámenes periódicos del año
    anio_actual = str(hoy.year)
    con_examen = (
        set(df_e.loc[df_e['anio'].astype(str) == anio_actual, 'id_legajo'].astype(str))
        if not df_e.empty
        else set()
    )
    ids_cadetes = set(df_c['id_legajo'].astype(str))
    con_examen &= ids_cadetes
    pct_cob = round(100 * len(con_examen) / len(ids_cadetes)) if ids_cadetes else 0

    col_izq, col_der = st.columns([2.1, 1], gap='large')
    with col_izq:
      st.markdown(
          '<div class="section-head"><div><div class="t">Centro de alertas</div>'
          f'<div class="s">{len(visibles)} alerta(s) según los filtros'
          ' seleccionados</div></div></div>',
          unsafe_allow_html=True,
      )
      if not visibles:
        st.markdown(
            '<div class="alert-ok"><span class="big">✅</span><div>Sin alertas'
            ' para los filtros seleccionados.<br><span style="font-weight:400;'
            ' opacity:.8;">Todo en orden.</span></div></div>',
            unsafe_allow_html=True,
        )
      else:
        for a in visibles[:60]:
          st.markdown(
              f'<div class="al al-{a["nivel"]}"><div'
              f' class="al-icon">{iconos_nivel[a["nivel"]]}</div><div'
              f' class="al-main"><span'
              f' class="al-pill">{etiquetas_nivel[a["nivel"]]} ·'
              f' {_esc(a["tipo"])}</span><div'
              f' class="al-name">{_esc(a["cadete"])}</div><div'
              f' class="al-detail">{_esc(a["detalle"])}</div></div><div'
              f' class="al-meta"><span class="tag">Curso'
              f' {_esc(a["curso"])}</span><span class="tag">Legajo'
              f' {_esc(a["legajo"])}</span></div></div>',
              unsafe_allow_html=True,
          )
        if len(visibles) > 60:
          st.caption(f'Mostrando 60 de {len(visibles)} alertas. Filtre por curso para ver el resto.')
        df_alertas = pd.DataFrame(visibles).drop(columns=['nivel', 'orden'])
        df_alertas.columns = ['Cadete', 'Curso', 'Legajo', 'Tipo', 'Detalle']
        st.download_button(
            '⬇️ Descargar alertas (CSV)',
            df_alertas.to_csv(index=False).encode('utf-8-sig'),
            file_name=f'alertas_{hoy}.csv',
            mime='text/csv',
        )

    with col_der:
      # Actividad de guardia: últimos 14 días
      dias_idx = pd.date_range(end=pd.Timestamp(hoy), periods=14)
      conteo = {}
      if not df_i.empty:
        fechas = pd.to_datetime(df_i['fecha_hora'], errors='coerce').dt.normalize().dropna()
        conteo = fechas.value_counts().to_dict()
      serie = pd.DataFrame(
          {'Intervenciones': [int(conteo.get(d, 0)) for d in dias_idx]},
          index=dias_idx,
      )
      st.markdown(
          '<div class="panel"><div class="panel-title">Actividad de guardia</div>'
          f'<div class="panel-big">{int(serie["Intervenciones"].sum())}</div>'
          '<div class="panel-note">intervenciones en los últimos 14 días</div></div>',
          unsafe_allow_html=True,
      )
      try:
        import altair as alt

        serie.index.name = 'Fecha'
        df_graf = serie.reset_index()
        y_max = max(1, int(serie['Intervenciones'].max()))
        graf = (
            alt.Chart(df_graf)
            .mark_bar(color='#38BDF8', cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=14)
            .encode(
                x=alt.X('Fecha:T', axis=alt.Axis(
                    format='%d/%m', title=None, grid=False, labelAngle=0,
                    tickCount=5, labelColor='#8A97B1',
                    domainColor='#1C2740', tickColor='#1C2740')),
                y=alt.Y('Intervenciones:Q', scale=alt.Scale(domain=[0, y_max]),
                        axis=alt.Axis(title=None, tickMinStep=1, labelColor='#8A97B1',
                                      gridColor='#1C2740', domain=False, ticks=False)),
                tooltip=[alt.Tooltip('Fecha:T', format='%d/%m/%Y'),
                         alt.Tooltip('Intervenciones:Q')],
            )
            .properties(height=190, background='transparent')
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(graf, use_container_width=True, theme=None)
      except Exception:
        st.bar_chart(serie, color='#38BDF8', height=190)

      st.markdown(
          '<div class="panel"><div class="panel-title">Exámenes periódicos'
          f' {anio_actual}</div><div class="panel-big">{pct_cob}%</div>'
          f'<div class="bar"><div style="width: {pct_cob}%;"></div></div>'
          f'<div class="panel-note">{len(con_examen)} de {len(ids_cadetes)}'
          ' cadetes con examen registrado</div></div>',
          unsafe_allow_html=True,
      )

    df_sin = df_c[~df_c['id_legajo'].astype(str).isin(con_examen)]
    with st.expander(f'📋 Cadetes sin examen periódico {anio_actual} ({len(df_sin)})'):
      st.dataframe(df_sin[['id_legajo', 'apellido_nombre', 'curso']], use_container_width=True)
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
      '<div class="pro-header"><p class="pro-title">📁 Gestión de Legajos de Cadetes</p><p class="pro-subtitle">Directorio institucional de compañía, altas manuales y control de legajos sanitarios.</p></div>',
      unsafe_allow_html=True,
  )
  
  df_c_gen = obtener_cadetes()
  if not df_c_gen.empty:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
      st.markdown(kpi_card('👥', len(df_c_gen), 'Total compañía', '#38BDF8'), unsafe_allow_html=True)
    with c2:
      c_1 = len(df_c_gen[df_c_gen['curso'].str.contains('1', na=False)])
      st.markdown(kpi_card('1️⃣', c_1, 'Primer año', '#34D399'), unsafe_allow_html=True)
    with c3:
      c_2 = len(df_c_gen[df_c_gen['curso'].str.contains('2', na=False)])
      st.markdown(kpi_card('2️⃣', c_2, 'Segundo año', '#FBBF24'), unsafe_allow_html=True)
    with c4:
      c_3 = len(df_c_gen[df_c_gen['curso'].str.contains('3', na=False)])
      st.markdown(kpi_card('3️⃣', c_3, 'Tercer año', '#A78BFA'), unsafe_allow_html=True)
  
  st.markdown('<br>', unsafe_allow_html=True)
  tab1, tab2 = st.tabs(['🔍 Consultar / Listar Compañía', '➕ Registrar Nuevo Cadete'])
  
  with tab1:
    st.markdown('<br>', unsafe_allow_html=True)
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
      busqueda = st.text_input('🔍 Búsqueda rápida por Apellido, Nombre o Número de Legajo/Cargo', placeholder='Escriba para filtrar...')
    with col_t2:
      st.markdown('<div style="margin-top: 1.8rem;"></div>', unsafe_allow_html=True)
      if st.button('🔄 Sincronizar con Excel'):
        ex, ms = importar_excel_directo()
        if ex: st.success(ms); st.rerun()
        else: st.error(ms)
        
    df_cadetes = obtener_cadetes()
    if not df_cadetes.empty:
      if busqueda:
        df_cadetes = df_cadetes[
            df_cadetes['apellido_nombre'].str.contains(busqueda, case=False, na=False)
            | df_cadetes['id_legajo'].astype(str).str.contains(busqueda, case=False, na=False)
            | df_cadetes['dni'].astype(str).str.contains(busqueda, case=False, na=False)
        ]
      
      st.markdown('<div class="panel">', unsafe_allow_html=True)
      st.dataframe(df_cadetes, use_container_width=True)
      st.markdown('</div>', unsafe_allow_html=True)
      
      st.download_button(
          '⬇️ Descargar listado completo (CSV)',
          df_cadetes.to_csv(index=False).encode('utf-8-sig'),
          file_name=f'cadetes_iesp_{datetime.today().date()}.csv',
          mime='text/csv',
      )
    else:
      st.warning('No hay cadetes en la base de datos.')
      
  with tab2:
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><h3>Formulario de Alta Manual de Cadete</h3><p style="color: var(--muted); font-size: 0.88rem;">Complete los datos obligatorios para incorporar un nuevo legajo al sistema institucional.</p></div>', unsafe_allow_html=True)
    
    with st.form('form_nuevo_cadete'):
      col1, col2 = st.columns(2, gap='medium')
      with col1:
        id_legajo = st.text_input('Número de Legajo / Cargo *', placeholder='Ej: 20505').strip()
        apellido_nombre = st.text_input('Apellido y Nombres *', placeholder='Ej: PÉREZ, JUAN CARLOS').strip()
        curso = st.selectbox('Curso / Año', ['1 AÑO', '2 AÑO', '3 AÑO'])
      with col2:
        dni = st.text_input('Documento Nacional de Identidad (DNI)', placeholder='Ej: 42356789').strip()
        genero = st.selectbox('Género', ['Masculino', 'Femenino', 'Otro'])
        fecha_nacimiento = st.date_input('Fecha de Nacimiento', value=date(2002, 1, 1))
        
      observaciones = st.text_area('Observaciones / Contacto / Antecedentes Sanitarios', placeholder='Email, celular, grupo sanguíneo, etc.')
      
      st.markdown('<br>', unsafe_allow_html=True)
      if st.form_submit_button('💾 Guardar Legajo Institucional'):
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
            st.success(f'¡Legajo {id_legajo} de {apellido_nombre} guardado con éxito!')
          except sqlite3.IntegrityError:
            st.error('Error: El número de legajo ya existe en la base de datos.')
        else:
          st.warning('Debe completar obligatoriamente el Número de Legajo y los Apellidos y Nombres.')

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
        st.success('¡Personal dado de baja!')
        st.rerun()

elif menu == '1. Primera Intervención':
  st.markdown(
      '<h2 style="color: #FFFFFF;">🩺 Primera Intervención en Gabinete</h2>',
      unsafe_allow_html=True,
  )
  df_cadetes = obtener_cadetes()
  df_personal = obtener_personal()
  if df_cadetes.empty:
    st.warning('No hay cadetes.')
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
          guardado = False
          try:
            cursor.execute(
                'INSERT INTO primera_intervencion (id_legajo, fecha_hora,'
                ' profesional_atiende, sintomas, presion, saturacion,'
                ' derivacion) VALUES (?, ?, ?, ?, ?, ?, ?)',
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
            guardado = True
          except sqlite3.OperationalError as e:
            st.error(f'Error de base de datos: {e}')
            cols = [
                r[1]
                for r in cursor.execute(
                    'PRAGMA table_info(primera_intervencion)'
                ).fetchall()
            ]
            st.code(f'Columnas actuales: {cols}')
          finally:
            conn.close()
          if guardado:
            st.success('¡Intervención registrada!')
            st.rerun()
        else:
          st.warning('Complete campos obligatorios.')
  st.markdown('### 📊 Historial')
  conn = sqlite3.connect(DB_NAME)
  df_ints = pd.read_sql_query(
      'SELECT * FROM primera_intervencion WHERE id_legajo = ?',
      conn,
      params=(id_legajo,),
  )
  conn.close()
  if not df_ints.empty:
    st.dataframe(df_ints, use_container_width=True)

elif menu == '2. Notas Médicas y Reposos':
  st.markdown(
      '<h2 style="color: #FFFFFF;">📋 Registro de Notas Médicas, Certificados y'
      ' Estudios</h2>',
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
    st.markdown(
        f'<div class="profile-card"><h3 style="margin: 0; color:'
        f' #FFFFFF;">{cad_sel["apellido_nombre"]}</h3><p style="margin:'
        f' 0.25rem 0 0 0; color: #94A3B8;">Legajo: <b>{cad_sel["id_legajo"]}</b>'
        f' | Curso: <b>{cad_sel["curso"]}</b></p></div>',
        unsafe_allow_html=True,
    )
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
      submitted_nota = st.form_submit_button('Guardar Nota Médica y Expediente')

    uploaded_file = st.file_uploader(
        '📎 Adjuntar Archivo PDF Externo (Certificado / Análisis / Estudio'
        ' escaneado)',
        type=['pdf'],
    )

    if submitted_nota:
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
        if uploaded_file is not None:
          ext_path = os.path.join(
              UPLOAD_DIR, f'{id_legajo}_{nro_expediente}_{uploaded_file.name}'
          )
          with open(ext_path, 'wb') as f_ext:
            f_ext.write(uploaded_file.getbuffer())
          cursor.execute(
              'INSERT INTO legajo_documentos (id_legajo, titulo_documento,'
              ' tipo_documento, fecha_subida, archivo_nombre, observaciones)'
              ' VALUES (?, ?, ?, ?, ?, ?)',
              (
                  id_legajo,
                  f'Expediente {nro_expediente} - Archivo Externo Adjunto',
                  'PDF Externo',
                  str(datetime.today().date()),
                  ext_path,
                  'Subido por usuario',
              ),
          )
        conn.commit()
        conn.close()
        st.success(
            '¡Nota médica y documentación PDF anexadas con éxito al legajo'
            ' digital!'
        )
      else:
        st.warning('Complete los campos obligatorios (*).')

elif menu == '3. Control de Alta':
  st.markdown(
      '<h2 style="color: #FFFFFF;">✅ Control y Gestión de Altas Médicas</h2>',
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #94A3B8;'>Convalide el alta médica reglamentaria o"
      ' registre la extensión de reposo por presentación de nuevos'
      ' certificados o días adicionales.</p>',
      unsafe_allow_html=True,
  )

  conn = sqlite3.connect(DB_NAME)
  df_pendientes = pd.read_sql_query(
      "SELECT n.*, c.apellido_nombre, c.curso FROM notas_medicas n LEFT JOIN"
      " cadetes c ON n.id_legajo = c.id_legajo WHERE n.estado_alta = 'Pendiente'",
      conn,
  )
  conn.close()

  alta_tab1, alta_tab2 = st.tabs([
      '1️⃣ Convalidar Alta Médica',
      '2️⃣ Extensión de Reposo / Prórroga',
  ])

  with alta_tab1:
    st.markdown('### Convalidación de Alta por Cierre de Reposo')
    if not df_pendientes.empty:
      st.dataframe(
          df_pendientes[[
              'id',
              'nro_expediente',
              'id_legajo',
              'apellido_nombre',
              'curso',
              'medico',
              'tipo_reposo',
              'fecha_hasta',
          ]],
          use_container_width=True,
      )
      exp_id = st.selectbox(
          'Seleccione el ID del Expediente para Convalidar Alta',
          df_pendientes['id'].tolist(),
          key='sel_alta',
      )
      if st.button('Convalidar Alta Médica Oficial'):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notas_medicas SET estado_alta = 'Alta Convalidada' WHERE id"
            ' = ?',
            (exp_id,),
        )
        conn.commit()
        conn.close()
        st.success('¡Alta médica convalidada con éxito!')
        st.rerun()
    else:
      st.info('ℹ️ No hay expedientes pendientes de alta.')

  with alta_tab2:
    st.markdown('### Registro de Prórroga o Más Días de Reposo')
    st.markdown(
        "<p style='color: #94A3B8;'>Si el cadete presenta un nuevo certificado"
        ' médico extendiendo sus días de reposo o un nuevo parte, registre aquí'
        ' la ampliación del expediente.</p>',
        unsafe_allow_html=True,
    )
    if not df_pendientes.empty:
      cadetes_pendientes_lista = (
          df_pendientes['id_legajo'].astype(str)
          + ' - '
          + df_pendientes['apellido_nombre']
          + ' (Exp: '
          + df_pendientes['nro_expediente']
          + ')'
      ).tolist()
      sel_ext = st.selectbox(
          'Seleccione Expediente / Cadete para Extender Reposo',
          cadetes_pendientes_lista,
      )
      id_leg_ext = sel_ext.split(' - ')[0]
      exp_ref = sel_ext.split('Exp: ')[1].split(')')[0]

      with st.form('form_extension_reposo'):
        col_e1, col_e2 = st.columns(2)
        with col_e1:
          nuevo_medico = st.text_input('Médico Tratante de Prórroga*')
          nuevo_diagnostico = st.text_area(
              'Diagnóstico / Motivo de Extensión*'
          )
          dias_adicionales = st.number_input(
              'Días de Reposo Adicionales', min_value=1, max_value=90, value=7
          )
        with col_e2:
          nueva_fecha_hasta = st.date_input(
              'Nueva Fecha de Finalización de Reposo',
              value=datetime.today().date() + timedelta(days=7),
          )
          nuevos_certificados = st.text_area(
              '📄 Observaciones del Nuevo Certificado Presentado'
          )

        uploaded_ext = st.file_uploader(
            '📎 Adjuntar PDF del Nuevo Certificado de Prórroga',
            type=['pdf'],
            key='up_ext',
        )

        if st.form_submit_button('Registrar Prórroga y Extender Reposo'):
          if nuevo_medico and nuevo_diagnostico:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE notas_medicas SET fecha_hasta = ?, medicamentos = ?'
                ' WHERE id_legajo = ? AND nro_expediente = ? AND estado_alta ='
                " 'Pendiente'",
                (
                    str(nueva_fecha_hasta),
                    (
                        f'Prórroga de {dias_adicionales} días. Motivo:'
                        f' {nuevo_diagnostico}'
                    ),
                    id_leg_ext,
                    exp_ref,
                ),
            )

            if uploaded_ext is not None:
              ext_path = os.path.join(
                  UPLOAD_DIR,
                  f'{id_leg_ext}_PRORROGA_{uploaded_ext.name}',
              )
              with open(ext_path, 'wb') as f_ex:
                f_ex.write(uploaded_ext.getbuffer())
              cursor.execute(
                  'INSERT INTO legajo_documentos (id_legajo, titulo_documento,'
                  ' tipo_documento, fecha_subida, archivo_nombre, observaciones)'
                  ' VALUES (?, ?, ?, ?, ?, ?)',
                  (
                      id_leg_ext,
                      f'Expediente {exp_ref} - Prórroga de Reposo',
                      'PDF Prórroga',
                      str(datetime.today().date()),
                      ext_path,
                      nuevo_diagnostico,
                  ),
              )
            conn.commit()
            conn.close()
            st.success(
                '¡Prórroga de reposo registrada y legajo actualizado'
                ' correctamente!'
            )
            st.rerun()
          else:
            st.warning('Complete campos obligatorios (*).')
    else:
      st.info('No hay reposos activos para extender.')

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
  df_cadetes = obtener_cadetes()
  if not df_cadetes.empty:
    busq_hc = st.text_input(
        '🔍 Buscar Cadete por Apellido o Legajo para ver Historia Clínica'
    )
    df_hc_view = df_cadetes.copy()
    if busq_hc:
      busq_hc_str = str(busq_hc)
      df_hc_view = df_hc_view[
          df_hc_view['apellido_nombre'].str.contains(
              busq_hc_str, case=False, na=False
          )
          | df_hc_view['id_legajo']
          .astype(str)
          .str.contains(busq_hc_str, case=False, na=False)
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
          '<div class="profile-card"><h2>'
          + str(cad_hc['apellido_nombre'])
          + '</h2><p>Legajo: <b>'
          + str(cad_hc['id_legajo'])
          + '</b> | Curso: <b>'
          + str(cad_hc['curso'])
          + '</b> | DNI: <b>'
          + str(cad_hc['dni'])
          + '</b></p></div>',
          unsafe_allow_html=True,
      )
      conn = sqlite3.connect(DB_NAME)
      df_nm_hc = pd.read_sql_query(
          f"SELECT * FROM notas_medicas WHERE id_legajo = '{id_leg_hc}'", conn
      )
      df_doc_hc = pd.read_sql_query(
          f"SELECT * FROM legajo_documentos WHERE id_legajo = '{id_leg_hc}'", conn
      )
      conn.close()
      st.markdown('### 📋 Notas Médicas, Certificados y Estudios Anexos')
      if not df_nm_hc.empty:
        for _, r in df_nm_hc.iterrows():
          exp_no = str(r['nro_expediente'])
          diag = str(r['diagnostico'])
          med = str(r['medico'])
          rep = str(r['tipo_reposo'])
          f_des = str(r['fecha_desde'])
          f_has = str(r['fecha_hasta'])
          est = str(r['estado_alta'])
          cert_ind = (
              str(r['certificados_indicaciones'])
              if pd.notna(r['certificados_indicaciones'])
              else 'Sin anexos'
          )
          an_est = (
              str(r['analisis_estudios'])
              if pd.notna(r['analisis_estudios'])
              else 'Sin estudios'
          )
          card_html = (
              '<div class="profile-card" style="border-left: 4px solid #38BDF8;">'
              '<h4>Expediente: '
              + exp_no
              + ' | Diagnóstico: '
              + diag
              + '</h4><p><b>Médico:</b> '
              + med
              + ' | <b>Reposo:</b> '
              + rep
              + ' ('
              + f_des
              + ' al '
              + f_has
              + ') | <b>Estado:</b> '
              + est
              + '</p><p><b>Certificados e Indicaciones:</b><br>'
              + cert_ind
              + '</p><p><b>Análisis y Estudios:</b><br>'
              + an_est
              + '</p></div>'
          )
          st.markdown(card_html, unsafe_allow_html=True)
      else:
        st.write('Sin notas médicas.')
      st.markdown('### 📥 Documentos en PDF Anexados al Legajo Digital')
      if not df_doc_hc.empty:
        for _, doc_row in df_doc_hc.iterrows():
          t_doc = str(doc_row['titulo_documento'])
          f_sub = str(doc_row['fecha_subida'])
          f_path = str(doc_row['archivo_nombre'])
          doc_id = str(doc_row['id'])
          st.markdown(f'- **{t_doc}** (Subido el {f_sub})')
          if os.path.exists(f_path):
            with open(f_path, 'rb') as f:
              st.download_button(
                  label=f'📥 Descargar PDF: {f_path}',
                  data=f.read(),
                  file_name=f_path,
                  mime='application/pdf',
                  key=f'dl_{doc_id}',
              )
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

  col_s1, col_s2, col_s3 = st.columns(3)
  with col_s1:
    st.markdown(
        f'<div class="metric-card"><div class="metric-value">{len(df_c_rep)}</div><div'
        ' class="metric-label">Total Cadetes</div></div>',
        unsafe_allow_html=True,
    )
  with col_s2:
    st.markdown(
        f'<div class="metric-card"><div class="metric-value">{len(df_i_rep)}</div><div'
        ' class="metric-label">Atenciones Guardia</div></div>',
        unsafe_allow_html=True,
    )
  with col_s3:
    st.markdown(
        f'<div class="metric-card"><div class="metric-value">{len(df_n_rep)}</div><div'
        ' class="metric-label">Expedientes Médicos</div></div>',
        unsafe_allow_html=True,
    )

  st.markdown('<br>', unsafe_allow_html=True)
  spark_tab1, spark_tab2, spark_tab3 = st.tabs([
      '📈 Morbilidad por Cursos',
      '🏥 Distribución de Derivaciones',
      '📋 Visor de Datos Analíticos',
  ])

  with spark_tab1:
    st.markdown('### 📈 Concentración de Atenciones de Guardia por Curso')
    if not df_i_rep.empty:
      df_curso = df_i_rep.groupby('curso').size().reset_index(name='Atenciones')
      st.dataframe(df_curso, use_container_width=True)
      st.bar_chart(df_curso.set_index('curso'))
    else:
      st.info('No hay suficientes intervenciones registradas para graficar.')

  with spark_tab2:
    st.markdown('### 🏥 Demanda en Centros de Derivación Sanitaria')
    if not df_i_rep.empty:
      df_deriv = (
          df_i_rep.groupby('derivacion').size().reset_index(name='Frecuencia')
      )
      st.dataframe(df_deriv, use_container_width=True)
    else:
      st.info('No hay datos de derivación suficientes.')

  with spark_tab3:
    st.markdown('### 📋 Estructura de Datos Consolidados')
    if not df_i_rep.empty:
      st.dataframe(df_i_rep, use_container_width=True)
    else:
      st.info('Sin datos para mostrar.')
else:
  st.markdown(f'## Módulo: {menu}')
