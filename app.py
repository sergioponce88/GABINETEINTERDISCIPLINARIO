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
.chip .dot { width: 8px; height: 8px; border-radius: 50
