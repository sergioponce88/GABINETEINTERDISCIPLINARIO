"""Fichas de ingreso (comienzo de año):
- Declaración Jurada de Salud y Condiciones Psicofísicas
- Ficha de Salud / Inspección para la incorporación (Anexo A: mapa corporal, Anexo B: locomotor)
Se cargan en pantalla con la misma estructura del papel, se guardan en la base, generan el PDF
oficial listo para imprimir y firmar, y se archivan solos en el legajo digital."""
import hashlib
import io
import json
import os
from datetime import date, datetime, time

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (Image as RLImage, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

import db
import seguridad as sec

BASE = os.path.dirname(os.path.abspath(__file__))
ASSET = lambda n: os.path.join(BASE, 'assets', n)  # noqa: E731
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre']
AZUL = colors.HexColor('#1F4E9E')

# --- Estructura idéntica a los formularios en papel --------------------------
SINTOMAS = [  # 3 columnas, como en la DDJJ
    ['Tos', 'Tuberculosis', 'Falta de aire', 'Enfermedades respiratorias', 'Escupir sangre', 'Asma', 'Alergias',
     'Palpitaciones', 'Dolor de pecho', 'Hipertensión', 'Chagas', 'Aumento de peso', 'Descenso de peso',
     'Úlcera gastroduodenal'],
    ['Diarreas', 'Cólicos renales', 'Infecciones urinarias', 'Reflujo', 'Acidez', 'Parasitosis', 'Epigastralgias',
     'Antecedentes de hepatitis', 'Sangre en la orina', 'Dolor de cabeza', 'Convulsiones', 'Temblores', 'Neuralgias',
     'Alteraciones del sueño'],
    ['Diabetes', 'Hipertiroidismo', 'Hipotiroidismo', 'Intoxicaciones', 'Cirugías', 'Pérdida de conocimiento',
     'Padecimientos psicológicos o psiquiátricos', 'Hernias inguinales - umbilical',
     'Enfermedad de transmisión sexual (E.T.S.)', 'Fracturas', 'Dolores óseos', 'Lumbalgias', 'Hernia de disco',
     'Otros'],
]
DETALLE = {'Alergias': '¿A qué?', 'Cirugías': '¿Cuál?', 'Otros': '¿Cuál?'}
ZONAS = ['Cráneo', 'Columna vertebral', 'Tórax', 'Pelvis', 'Miembros superiores (hombro, brazo, antebrazo, mano)',
         'Miembros inferiores (cadera, muslo, rodilla, pierna y pie)']
FAMILIA = ['Vivo', 'Fallecido', 'Diabetes', 'Hipertensión', 'Enfermedades cardíacas', 'Epilepsia', 'Tuberculosis',
           'Enfermedades psiquiátricas', 'Suicidios consumados - intentos']
PARIENTES = ['Padre', 'Madre', 'Abuelos', 'Hermanos']
GRUPOS = ['', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', '0+', '0-', 'No sabe']
ESTADO_CIVIL = ['', 'Soltero/a', 'Casado/a', 'Unión convivencial', 'Divorciado/a', 'Viudo/a']
GENEROS = ['', 'Masculino', 'Femenino', 'Otro']

TIPOS_HALLAZGO = {'Tatuaje': '#2563EB', 'Cicatriz': '#DC2626', 'Lunar / nevo': '#7C3AED', 'Lesión de piel': '#EA580C',
                  'Piercing': '#0891B2', 'Deformidad': '#B45309', 'Otro': '#475569'}
REGIONES = {  # coordenadas sobre assets/cuerpo_masculino.png (650×814)
    'Anterior · Cabeza / frente': (97, 65), 'Anterior · Cuello': (97, 115),
    'Anterior · Hombro derecho': (55, 140), 'Anterior · Hombro izquierdo': (140, 140),
    'Anterior · Tórax / pecho': (97, 172), 'Anterior · Abdomen': (97, 215), 'Anterior · Pelvis / ingle': (97, 268),
    'Anterior · Brazo derecho': (48, 185), 'Anterior · Brazo izquierdo': (147, 185),
    'Anterior · Antebrazo derecho': (42, 250), 'Anterior · Antebrazo izquierdo': (153, 250),
    'Anterior · Mano derecha': (38, 295), 'Anterior · Mano izquierda': (160, 295),
    'Anterior · Muslo derecho': (80, 340), 'Anterior · Muslo izquierdo': (115, 340),
    'Anterior · Rodilla derecha': (82, 385), 'Anterior · Rodilla izquierda': (113, 385),
    'Anterior · Pierna derecha': (85, 435), 'Anterior · Pierna izquierda': (110, 435),
    'Anterior · Pie derecho': (78, 500), 'Anterior · Pie izquierdo': (128, 500),
    'Posterior · Cabeza / nuca': (290, 85), 'Posterior · Espalda alta': (290, 160),
    'Posterior · Omóplato izquierdo': (262, 160), 'Posterior · Omóplato derecho': (318, 160),
    'Posterior · Zona lumbar': (290, 240), 'Posterior · Glúteos': (290, 285),
    'Posterior · Brazo izquierdo': (238, 190), 'Posterior · Brazo derecho': (343, 190),
    'Posterior · Antebrazo izquierdo': (226, 255), 'Posterior · Antebrazo derecho': (354, 255),
    'Posterior · Muslo izquierdo': (272, 345), 'Posterior · Muslo derecho': (308, 345),
    'Posterior · Pantorrilla izquierda': (272, 430), 'Posterior · Pantorrilla derecha': (308, 430),
    'Lateral izq. · Cabeza': (440, 75), 'Lateral izq. · Hombro': (450, 145), 'Lateral izq. · Brazo': (440, 205),
    'Lateral izq. · Tronco / flanco': (458, 240), 'Lateral izq. · Muslo': (445, 360), 'Lateral izq. · Pierna': (440, 440),
    'Lateral der. · Cabeza': (560, 75), 'Lateral der. · Hombro': (560, 145), 'Lateral der. · Brazo': (575, 205),
    'Lateral der. · Tronco / flanco': (545, 240), 'Lateral der. · Muslo': (560, 360), 'Lateral der. · Pierna': (565, 440),
    'Rostro · Mejilla izquierda': (95, 680), 'Rostro · Oreja izquierda': (145, 675), 'Rostro · Frente': (310, 610),
    'Rostro · Ojos / cejas': (310, 650), 'Rostro · Nariz / boca': (310, 700), 'Rostro · Mentón': (310, 750),
    'Rostro · Mejilla derecha': (560, 680), 'Rostro · Oreja derecha': (490, 675),
}
LOCOMOTOR = [('ms_izq', 'Miembro superior', 'Izquierdo'), ('ms_der', 'Miembro superior', 'Derecho'),
             ('mi_izq', 'Miembro inferior', 'Izquierdo'), ('mi_der', 'Miembro inferior', 'Derecho'),
             ('col_dorsal', 'Columna vertebral', 'Dorsal'), ('col_lumbo', 'Columna vertebral', 'Lumbo-sacra')]


# --- Base de datos -----------------------------------------------------------
def _asegurar():
    if st.session_state.get('fi_tabla_ok'):
        return
    conn = db.conectar(sec.DB_NAME)
    conn.execute('CREATE TABLE IF NOT EXISTS fichas_ingreso (id INTEGER PRIMARY KEY AUTOINCREMENT, id_legajo TEXT,'
                 ' tipo TEXT, anio TEXT, datos TEXT, resultado TEXT, alertas INTEGER, fecha_registro TEXT, usuario TEXT)')
    if db.USA_PG:  # datos sensibles: sin acceso por la API pública de Supabase
        conn.execute('ALTER TABLE fichas_ingreso ENABLE ROW LEVEL SECURITY')
    for c, t in [('contenido', 'BYTEA')]:
        try:
            conn.execute(f'ALTER TABLE legajo_documentos ADD COLUMN {c} {t}')
        except Exception:
            pass
    conn.commit()
    conn.close()
    st.session_state['fi_tabla_ok'] = True


def _cargar(id_leg, tipo, anio):
    conn = db.conectar(sec.DB_NAME)
    fila = conn.execute('SELECT datos FROM fichas_ingreso WHERE id_legajo = ? AND tipo = ? AND anio = ?'
                        ' ORDER BY id DESC LIMIT 1', (id_leg, tipo, str(anio))).fetchone()
    conn.close()
    return json.loads(fila[0]) if fila and fila[0] else None


def _guardar(id_leg, tipo, anio, datos, resultado, alertas, pdf, titulo):
    usuario = (st.session_state.get('auth_user') or {}).get('username', '')
    ahora = sec.ahora_local().strftime('%Y-%m-%d %H:%M')
    with db.transaccion(sec.DB_NAME) as cur:
        cur.execute('DELETE FROM fichas_ingreso WHERE id_legajo = ? AND tipo = ? AND anio = ?', (id_leg, tipo, str(anio)))
        cur.execute('INSERT INTO fichas_ingreso (id_legajo, tipo, anio, datos, resultado, alertas, fecha_registro, usuario)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (id_leg, tipo, str(anio), json.dumps(datos, ensure_ascii=False, default=str), resultado, alertas,
                     ahora, usuario))
        cur.execute('DELETE FROM legajo_documentos WHERE id_legajo = ? AND titulo_documento = ?', (id_leg, titulo))
        cur.execute('INSERT INTO legajo_documentos (id_legajo, titulo_documento, tipo_documento, fecha_subida,'
                    ' archivo_nombre, observaciones, contenido) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (id_leg, titulo, 'Ficha de Ingreso', ahora[:10], f'{tipo}_{anio}_{id_leg}.pdf',
                     f'Generado por el sistema ({usuario})', pdf))


def _resumen(anio):
    conn = db.conectar(sec.DB_NAME)
    df = pd.read_sql_query('SELECT id_legajo, tipo, resultado, alertas, fecha_registro FROM fichas_ingreso'
                           ' WHERE anio = ?', conn, params=(str(anio),))
    conn.close()
    return df


@st.cache_data(show_spinner=False)
def _padron_excel(ruta, _mtime):
    """APELLIDO/NOMBRES/datos de contacto exactos desde el listado oficial (para autocompletar)."""
    try:
        df = pd.read_excel(ruta, dtype=str)
    except Exception:
        return {}
    df.columns = [str(c).strip().upper() for c in df.columns]
    out = {}
    for _, r in df.iterrows():
        d = {k: ('' if pd.isna(r.get(k)) else str(r.get(k)).strip()) for k in df.columns}
        for clave in (d.get('DNI'), d.get('CARGO')):
            if clave:
                out[clave] = d
    return out


# --- Utilidades --------------------------------------------------------------
def _f(v):
    if not v:
        return None
    if isinstance(v, date):
        return v
    d = pd.to_datetime(v, errors='coerce')
    return None if pd.isna(d) else d.date()


def _dmy(v):
    d = _f(v)
    return d.strftime('%d/%m/%Y') if d else ''


def _alertas_ddjj(d):
    """Lo que el médico debería mirar: síntomas en SÍ, traumatismos, hábitos y condiciones declaradas."""
    a = [s + (f" ({d['detalle'].get(s)})" if d.get('detalle', {}).get(s) else '') for s in d.get('sintomas', [])]
    a += [f'Traumatismo: {z.split(" (")[0]}' for z, v in d.get('trauma', {}).items() if v.get('si')]
    h = d.get('habitos', {})
    for k, rot in [('tabaco', 'Tabaco'), ('alcohol', 'Alcohol / sustancias'), ('medicamentos', 'Medicación')]:
        if h.get(k):
            a.append(rot + (f": {h.get(k + '_cual')}" if h.get(k + '_cual') else ''))
    if d.get('condicion_especial'):
        a.append(f"Condición especial: {d['condicion_especial']}")
    if d.get('internaciones'):
        a.append(f"Internaciones: {d['internaciones']}")
    return a


def mapa_corporal(hallazgos, ancho=None):
    """Diagrama del Anexo A con los hallazgos numerados y coloreados por tipo."""
    im = Image.open(ASSET('cuerpo_masculino.png')).convert('RGB')
    dr = ImageDraw.Draw(im)
    fnt = None
    for nombre in ('DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        try:
            fnt = ImageFont.truetype(nombre, 13)
            break
        except Exception:
            pass
    if fnt is None:
        try:
            fnt = ImageFont.load_default(size=13)
        except TypeError:
            fnt = ImageFont.load_default()
    vistos = {}
    for i, h in enumerate(hallazgos, 1):
        x, y = REGIONES.get(h.get('region'), (None, None))
        if x is None:
            continue
        n = vistos.get((x, y), 0)
        vistos[(x, y)] = n + 1
        x, y = x + 24 * n, y  # varios hallazgos en la misma zona: se corren a la derecha
        col = TIPOS_HALLAZGO.get(h.get('tipo'), '#475569')
        dr.ellipse((x - 11, y - 11, x + 11, y + 11), fill='white', outline=col, width=3)
        tw = dr.textlength(str(i), font=fnt)
        dr.text((x - tw / 2, y - 8), str(i), fill=col, font=fnt)
    if ancho:
        im = im.resize((ancho, int(im.height * ancho / im.width)))
    return im


# --- PDF ---------------------------------------------------------------------
_E = {
    'n': ParagraphStyle('n', fontName='Helvetica', fontSize=9.5, leading=13),
    'j': ParagraphStyle('j', fontName='Helvetica', fontSize=9.5, leading=13.5, alignment=TA_JUSTIFY, firstLineIndent=28),
    'h': ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=10.5, leading=14, spaceBefore=6, spaceAfter=4),
    'c': ParagraphStyle('c', fontName='Helvetica', fontSize=9, leading=11, alignment=TA_CENTER),
    't': ParagraphStyle('t', fontName='Helvetica', fontSize=8.5, leading=10.5),
}


def _v(valor, ancho=28):
    """Valor completado en azul; si está vacío, línea de puntos como en el papel."""
    s = str(valor).strip() if valor not in (None, '') else ''
    return f'<font color="#1F3A93"><b>{_esc(s)}</b></font>' if s else '.' * ancho


def _esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _pdf(titulos, flujo, lateral, anio, codigo):
    buf = io.BytesIO()
    izq, der = ASSET('logo_izq.png'), ASSET('logo_der.png')

    def pagina(c, doc):
        w, h = A4
        c.saveState()
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.8)
        c.rect(1 * cm, 1 * cm, w - 2 * cm, h - 2 * cm)
        x0 = 2.6 * cm if lateral else 1.6 * cm
        bx, by, bw, bh = x0, h - 3.7 * cm, w - x0 - 1.6 * cm, 2.4 * cm
        c.rect(bx, by, bw, bh)
        if os.path.exists(izq):
            c.drawImage(izq, bx + 0.25 * cm, by + 0.45 * cm, 1.5 * cm, 1.5 * cm, mask='auto', preserveAspectRatio=True)
        if os.path.exists(der):
            c.drawImage(der, bx + bw - 1.75 * cm, by + 0.45 * cm, 1.5 * cm, 1.5 * cm, mask='auto', preserveAspectRatio=True)
        yy = by + bh - 0.65 * cm
        for i, (txt, font, size) in enumerate(titulos):
            c.setFont(font, size)
            c.drawCentredString(bx + bw / 2, yy, txt)
            yy -= size + 4
        if lateral:
            c.saveState()
            c.translate(1.85 * cm, 1.6 * cm)
            c.rotate(90)
            c.setFillColor(AZUL)
            c.setFont('Helvetica-Bold', 21)
            c.drawString(0, 0, 'JEFATURA DE COMPAÑÍA DE CADETES DEL I.E.S.P. "G.J.F.S.M."')
            c.restoreState()
        c.setFont('Helvetica', 6.5)
        c.setFillColor(colors.grey)
        c.drawRightString(w - 1.2 * cm, 0.6 * cm, f'Gabinete Interdisciplinario I.E.S.P. · {anio} · '
                                                  f'Pág. {doc.page} · Verificación {codigo}')
        c.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=(2.9 if lateral else 1.9) * cm, rightMargin=1.9 * cm,
                            topMargin=4.1 * cm, bottomMargin=1.6 * cm)
    doc.build(flujo, onFirstPage=pagina, onLaterPages=pagina)
    return buf.getvalue()


def _tabla(data, anchos, estilo_extra=()):
    t = Table(data, colWidths=anchos)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('FONTSIZE', (0, 0), (-1, -1), 8.5), ('TOPPADDING', (0, 0), (-1, -1), 2),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 2), *estilo_extra]))
    return t


def _firma(lineas):
    filas = [[Paragraph('.' * 60, _E['c'])], *[[Paragraph(x, _E['c'])] for x in lineas]]
    t = Table(filas, colWidths=[8 * cm], hAlign='RIGHT')
    t.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
    return t


def _si(v):
    return Paragraph('<font color="#B91C1C"><b>SÍ</b></font>' if v else '<font color="#6B7280">NO</font>', _E['c'])


def pdf_ddjj(d, anio):
    P = lambda t: Paragraph(t, _E['n'])  # noqa: E731
    f = [
        P(f"Fecha: {_v(_dmy(d.get('fecha')))} &nbsp;&nbsp; Documento: {_v(d.get('documento'))}"),
        P(f"Apellidos y nombres: {_v(d.get('apellidos_nombres'), 70)}"),
        P(f"Fecha de nacimiento: {_v(_dmy(d.get('fecha_nac')))} &nbsp;&nbsp; Género: {_v(d.get('genero'))}"),
        P(f"Lugar de nacimiento: {_v(d.get('lugar_nac'))} &nbsp;&nbsp; Nacionalidad: {_v(d.get('nacionalidad'))}"),
        P(f"Estado civil: {_v(d.get('estado_civil'))} &nbsp;&nbsp; Hijos: {_v(d.get('hijos'), 12)}"),
        P(f"Domicilio: {_v(d.get('domicilio'), 40)} &nbsp;&nbsp; Localidad: {_v(d.get('localidad'))}"),
        P(f"Teléfono fijo: {_v(d.get('tel_fijo'))} &nbsp;&nbsp; Celular: {_v(d.get('celular'))}"),
        P(f"Correo electrónico: {_v(d.get('email'), 60)}"),
        P(f"Grupo sanguíneo y factor: {_v(d.get('grupo'), 12)} &nbsp;&nbsp; Obra social: {_v(d.get('obra_social'))}"),
        Paragraph('1- Coloque sí o no según corresponda a los signos o enfermedades detallados', _E['h']),
    ]
    si = set(d.get('sintomas', []))
    det = d.get('detalle', {})
    filas = []
    for i in range(len(SINTOMAS[0])):
        fila = []
        for col in SINTOMAS:
            s = col[i]
            txt = s + (f"<br/><font size=7>{DETALLE[s]} <b>{_esc(det.get(s, ''))}</b></font>" if s in DETALLE else '')
            fila += [Paragraph(txt, _E['t']), _si(s in si)]
        filas.append(fila)
    f.append(_tabla(filas, [4.1 * cm, 1.05 * cm] * 3))
    t2 = d.get('trabajo', {})
    f += [Paragraph('2- Trabajo y accidentes', _E['h']),
          _tabla([[P('¿Tiene otro trabajo?'), _si(t2.get('otro')), P('¿Qué tipo de trabajo?'), P(_v(t2.get('tipo'), 20)), '', ''],
                  [P('¿Tuvo algún accidente?'), _si(t2.get('accidente')), P('¿De tránsito?'), _si(t2.get('transito')),
                   P('¿De trabajo?'), _si(t2.get('laboral'))]],
                 [3.8 * cm, 1.1 * cm, 3.4 * cm, 3.5 * cm, 2.4 * cm, 1.2 * cm]),
          Paragraph('3- Antecedentes traumáticos (fracturas, luxaciones o esguinces sufridos)', _E['h'])]
    tr = d.get('trauma', {})
    filas = [['ZONAS AFECTADAS', 'SI', 'NO', 'FECHA DE LA LESIÓN']]
    for z in ZONAS:
        v = tr.get(z, {})
        filas.append([Paragraph(z, _E['t']), 'X' if v.get('si') else '', '' if v.get('si') else 'X', v.get('fecha', '')])
    f += [_tabla(filas, [8 * cm, 1.4 * cm, 1.4 * cm, 4.6 * cm],
                 [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E5E7EB')), ('ALIGN', (1, 0), (-1, -1), 'CENTER')]),
          Spacer(1, 3), P(f"Breve relato del hecho, dónde sufrió la lesión: {_v(d.get('relato'), 60)}")]
    fam = d.get('familia', {})
    filas = [['ENFERMEDADES', *[p.upper() for p in PARIENTES]]]
    for e in FAMILIA:
        filas.append([e, *['X' if fam.get(e, {}).get(p) else '' for p in PARIENTES]])
    filas.append([Paragraph(f"Otras: <b>{_esc(d.get('familia_otras', ''))}</b>", _E['t']), '', '', '', ''])
    f += [KeepTogether([Paragraph('4- Antecedentes familiares: enfermedades padecidas por', _E['h']),
                        _tabla(filas, [6.4 * cm] + [2.25 * cm] * 4,
                               [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E5E7EB')),
                                ('ALIGN', (1, 0), (-1, -1), 'CENTER'), ('SPAN', (0, -1), (-1, -1))])]),
          Paragraph('5- Hábitos', _E['h'])]
    h = d.get('habitos', {})
    f += [_tabla([[P('Tabaco'), _si(h.get('tabaco')), P(f"Alcohol / otras sustancias psicoactivas: {_si_txt(h.get('alcohol'))} "
                                                         f"¿Cuál? {_v(h.get('alcohol_cual'), 15)}")],
                  [P('Actividad física'), _si(h.get('actividad')), P(f"¿Cuál? {_v(h.get('actividad_cual'), 30)}")],
                  [P('Medicamentos'), _si(h.get('medicamentos')), P(f"¿Cuál? {_v(h.get('medicamentos_cual'), 30)}")],
                  [P('Dieta habitual'), '', P(_v(h.get('dieta'), 40))],
                  [P('Otros hábitos'), '', P(_v(h.get('otros'), 40))]], [3.6 * cm, 1.2 * cm, 10.6 * cm]),
          Paragraph('6- Otros datos', _E['h']),
          P(f"• Antecedentes de internaciones en hospitales o clínicas, detalle motivos: {_v(d.get('internaciones'), 50)}"),
          P(f"• ¿Presenta alguna condición especial que pueda interferir con la función objeto de la convocatoria "
            f"para la cual será capacitado? Especifique: {_v(d.get('condicion_especial'), 50)}"),
          Spacer(1, 8),
          Paragraph('<i>Declaro bajo juramento haber comprendido lo explicado y acepto las condiciones propuestas, y me '
                    'comprometo a informar sobre toda condición psicofísica que pudiera surgir durante el cursado.</i>',
                    _E['j'])]
    ff = _f(d.get('fecha_firma')) or _f(d.get('fecha'))
    lugar = f"San Miguel de Tucumán, {ff.day} de {MESES[ff.month - 1]} del {ff.year}." if ff else \
        'San Miguel de Tucumán, ……… de ……………………… del ……….'
    f += [Spacer(1, 6), P(lugar), Spacer(1, 26),
          KeepTogether(_firma(['(Firma del Aspirante)', f"Aclaración: {_esc(d.get('apellidos_nombres', ''))}",
                               f"N° D.N.I.: {_esc(d.get('documento', ''))}"]))]
    tit = [('DECLARACIÓN JURADA DE SALUD', 'Helvetica-BoldOblique', 13),
           (f'Y DE CONDICIONES PSICOFÍSICAS VISIBLES Y NO VISIBLES - {anio}', 'Helvetica-BoldOblique', 11)]
    return _pdf(tit, f, False, anio, _codigo(d))


def _si_txt(v):
    return '<font color="#B91C1C"><b>SÍ</b></font>' if v else 'NO'


def _codigo(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:10].upper()


def pdf_ficha(d, anio):
    P = lambda t: Paragraph(t, _E['n'])  # noqa: E731
    f = [P(f"<b>FORMULARIO N°:</b> {_v(d.get('formulario'), 16)}"), Spacer(1, 4),
         P(f"<b>APELLIDOS:</b> {_v(d.get('apellidos'), 60)}"), P(f"<b>NOMBRES:</b> {_v(d.get('nombres'), 60)}"),
         P(f"<b>D.N.I.:</b> {_v(d.get('dni'))} &nbsp;&nbsp; <b>FECHA DE NACIMIENTO:</b> {_v(_dmy(d.get('fecha_nac')))}"),
         P(f"<b>DOMICILIO:</b> {_v(d.get('domicilio'), 70)}"), Spacer(1, 10),
         Paragraph('Por la presente doy mi consentimiento libre y voluntario para que se me realice una inspección '
                   'médica, y en el caso que se requiera, un registro fotográfico, previo a mi incorporación a este '
                   'Instituto.', _E['j']),
         Paragraph('Dejo constancia que me han explicado que la información que surja de la presente, es necesaria para '
                   'conocer si me encuentro en condiciones óptimas de salud, preservando mi integridad, pudiendo '
                   f'incorporarme para realizar todas las actividades previstas en el Curso Introductorio Ciclo Lectivo '
                   f'{anio}, destinado a los Aspirantes a Cadetes del Instituto de Enseñanza Superior de Policía '
                   '“Grl. José Francisco de San Martín”, la que será agregada a mi legajo personal.', _E['j']),
         Spacer(1, 6),
         Paragraph('<b><i>Declaro bajo juramento haber comprendido lo explicado y acepto las condiciones propuestas.</i></b>',
                   _E['n']),
         Spacer(1, 22),
         _firma(['(Firma del Aspirante)', f"Aclaración: {_esc((d.get('apellidos', '') + ' ' + d.get('nombres', '')).strip())}",
                 f"N° D.N.I.: {_esc(d.get('dni', ''))}"]),
         Spacer(1, 8), Paragraph('<para alignment="center">' + '- ' * 70 + '</para>', _E['t']), Spacer(1, 6),
         P(f"<b>FECHA DE EVALUACIÓN:</b> {_v(_dmy(d.get('fecha_eval')), 30)}"),
         P(f"<b>HORA:</b> {_v(d.get('hora'), 16)}"), Spacer(1, 10)]
    con = d.get('resultado') == 'Con novedad'
    caja = lambda marcado: Table([['X' if marcado else '']], colWidths=[2.2 * cm], rowHeights=[0.9 * cm], style=[  # noqa: E731
        ('BOX', (0, 0), (-1, -1), 1, colors.black), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 16), ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1F3A93'))])
    t = Table([[caja(con), '', caja(not con and d.get('resultado') == 'Sin novedad')],
               [Paragraph('CON NOVEDAD', _E['c']), '', Paragraph('SIN NOVEDAD', _E['c'])]],
              colWidths=[5 * cm, 5.4 * cm, 5 * cm])
    t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    f += [t, Spacer(1, 22),
          _firma(['FIRMA Y SELLO DEL PROFESIONAL', _esc(d.get('profesional', ''))]),
          Spacer(1, 6),
          Paragraph('<b>OBSERVACIONES:</b> En caso de que el aspirante tenga alguna novedad, el profesional médico lo '
                    'hará constar en el anexo “A” y “B”.', _E['t'])]

    # Anexo A
    hall = d.get('hallazgos', [])
    img = mapa_corporal(hall)
    b = io.BytesIO()
    img.save(b, format='PNG')
    b.seek(0)
    ancho = 13.2 * cm
    f += [PageBreak(), Paragraph('<para alignment="center"><b><u>ANEXO “A”</u></b></para>', _E['n']),
          Paragraph('<b><i><u>Inspección externa:</u></i></b>', _E['n']), Spacer(1, 4),
          RLImage(b, width=ancho, height=ancho * img.height / img.width)]
    if hall:
        filas = [['N°', 'Región', 'Tipo', 'Descripción']]
        for i, h in enumerate(hall, 1):
            filas.append([str(i), Paragraph(_esc(h.get('region', '')), _E['t']),
                          Paragraph(f'<font color="{TIPOS_HALLAZGO.get(h.get("tipo"), "#475569")}"><b>{_esc(h.get("tipo", ""))}</b></font>', _E['t']),
                          Paragraph(_esc(h.get('descripcion', '')), _E['t'])])
        f += [Spacer(1, 4), _tabla(filas, [0.9 * cm, 5 * cm, 2.6 * cm, 7 * cm],
                                   [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E5E7EB'))])]
    else:
        f.append(P('<i>Sin hallazgos en la inspección externa.</i>'))
    f += [Spacer(1, 4), P(f"<b>OBSERVACIONES:</b> {_v(d.get('obs_anexo_a'), 80)}")]

    # Anexo B
    f += [PageBreak(), Paragraph('<para alignment="center"><b><u>ANEXO “B”</u></b></para>', _E['n']), Spacer(1, 4),
          Paragraph('<b><i>Aparato Locomotor – Inspección externa:</i></b>', _E['n'])]
    loc = d.get('locomotor', {})
    filas = []
    for k, grupo, lado in LOCOMOTOR:
        filas.append([grupo, lado, Paragraph(_esc(loc.get(k, '')), _E['t'])])
    f.append(_tabla(filas, [3.6 * cm, 2.6 * cm, 9.2 * cm],
                    [('SPAN', (0, 0), (0, 1)), ('SPAN', (0, 2), (0, 3)), ('SPAN', (0, 4), (0, 5)),
                     ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('ROWHEIGHT', (0, 0), (-1, -1), 18)]))
    v = d.get('vision', {})
    f += [Spacer(1, 8),
          P(f"<b>¿Usa anteojos?</b> {_si_txt(v.get('anteojos'))} &nbsp;&nbsp; <b>¿Por qué motivo?</b> {_v(v.get('motivo'), 40)}")]
    if v.get('od') or v.get('oi'):
        f.append(P(f"<b>Agudeza visual</b> — OD: {_v(v.get('od'), 8)} &nbsp; OI: {_v(v.get('oi'), 8)}"))
    f += [P(f"<b>¿Usa prótesis dentales?</b> {_si_txt(d.get('protesis'))}"), Spacer(1, 6),
          P(f"<b>Genitourinario:</b> {_v(d.get('genitourinario'), 80)}"), Spacer(1, 4),
          P(f"<b>Cardio-Respiratorio:</b> {_v(d.get('cardio'), 80)}"), Spacer(1, 4),
          P(f"<b>Otras observaciones:</b> {_v(d.get('otras_obs'), 80)}"), Spacer(1, 30),
          _firma(['FIRMA Y SELLO DEL PROFESIONAL', _esc(d.get('profesional', ''))])]
    tit = [('“CURSO INTRODUCTORIO”', 'Helvetica-BoldOblique', 13),
           ('FICHA DE SALUD PARA LA INCORPORACIÓN DE', 'Times-Bold', 11),
           (f'ASPIRANTES A CADETES DE 1° AÑO - {anio}', 'Times-Bold', 11)]
    return _pdf(tit, f, True, anio, _codigo(d))


# --- Pantallas ---------------------------------------------------------------
def _encabezado_cadete(df_cad, anio, padron):
    lista = (df_cad['id_legajo'].astype(str) + ' - ' + df_cad['apellido_nombre']).tolist()
    sel = st.selectbox('Cadete / aspirante', lista, key='fi_cadete')
    id_leg = sel.split(' - ')[0]
    cad = df_cad[df_cad['id_legajo'].astype(str) == id_leg].iloc[0]
    px = padron.get(id_leg) or padron.get(str(cad.get('dni') or '')) or {}
    return id_leg, cad, px


def _descarga(pdf, nombre, clave):
    c1, c2 = st.columns([1, 2])
    c1.download_button('🖨️ Descargar / imprimir PDF', pdf, file_name=nombre, mime='application/pdf',
                       type='primary', key=clave, use_container_width=True)
    c2.caption('El PDF también quedó archivado en el legajo digital (Historia Clínica → Documentos).')


def _tab_ddjj(id_leg, cad, px, anio):
    prev = _cargar(id_leg, 'DDJJ', anio) or {}
    k = f'{id_leg}_{anio}'
    if prev:
        st.success(f"✔️ Ya tiene DDJJ {anio} registrada. Podés corregirla y volver a guardar, o reimprimirla.")
        if st.button('🖨️ Generar PDF de la DDJJ guardada', key=f'ddjj_re_{k}'):
            _descarga(pdf_ddjj(prev, anio), f'DDJJ_{anio}_{id_leg}.pdf', f'ddjj_dlre_{k}')
    nombre_def = (f"{px.get('APELLIDO', '')} {px.get('NOMBRES', '')}".strip() or cad['apellido_nombre'])
    g = prev.get

    with st.form(f'ddjj_{k}'):
        st.markdown('##### Datos personales')
        c = st.columns([1, 1, 2])
        fecha = c[0].date_input('Fecha', value=_f(g('fecha')) or sec.ahora_local().date(), format='DD/MM/YYYY')
        documento = c[1].text_input('Documento', value=g('documento') or str(cad.get('dni') or px.get('DNI') or ''))
        ape = c[2].text_input('Apellidos y nombres', value=g('apellidos_nombres') or nombre_def)
        c = st.columns(4)
        fnac = c[0].date_input('Fecha de nacimiento', value=_f(g('fecha_nac')) or _f(cad.get('fecha_nacimiento'))
                               or _f(px.get('FECHA DE NACIMIENTO')), format='DD/MM/YYYY',
                               min_value=date(1950, 1, 1), max_value=date.today())
        gen = c[1].selectbox('Género', GENEROS, index=GENEROS.index(g('genero') or cad.get('genero') or '')
                             if (g('genero') or cad.get('genero') or '') in GENEROS else 0)
        lnac = c[2].text_input('Lugar de nacimiento', value=g('lugar_nac') or '')
        nac = c[3].text_input('Nacionalidad', value=g('nacionalidad') or 'Argentina')
        c = st.columns(4)
        ec = c[0].selectbox('Estado civil', ESTADO_CIVIL, index=ESTADO_CIVIL.index(g('estado_civil'))
                            if g('estado_civil') in ESTADO_CIVIL else 0)
        hijos = c[1].text_input('Hijos', value=g('hijos') or '')
        grupo = c[2].selectbox('Grupo sanguíneo y factor', GRUPOS, index=GRUPOS.index(g('grupo')) if g('grupo') in GRUPOS else 0)
        os_ = c[3].text_input('Obra social', value=g('obra_social') or '')
        c = st.columns([2, 1])
        dom = c[0].text_input('Domicilio', value=g('domicilio') or '')
        loc = c[1].text_input('Localidad', value=g('localidad') or '')
        c = st.columns(3)
        tel = c[0].text_input('Teléfono fijo', value=g('tel_fijo') or '')
        cel = c[1].text_input('Celular', value=g('celular') or px.get('CELULAR', ''))
        mail = c[2].text_input('Correo electrónico', value=g('email') or px.get('EMAIL', ''))

        st.markdown('##### 1 · Signos o enfermedades  ·  tildá los que responde **SÍ**')
        marcados, detalle = set(g('sintomas') or []), dict(g('detalle') or {})
        nuevos, cols = [], st.columns(3)
        for col, items in zip(cols, SINTOMAS):
            for s in items:
                if col.checkbox(s, value=s in marcados, key=f'ddjj_s_{k}_{s}'):
                    nuevos.append(s)
        c = st.columns(3)
        det_new = {s: c[i].text_input(f'{s}: {DETALLE[s]}', value=detalle.get(s, ''), key=f'ddjj_d_{k}_{s}')
                   for i, s in enumerate(DETALLE)}

        st.markdown('##### 2 · Trabajo y accidentes')
        t2 = g('trabajo') or {}
        c = st.columns([1, 2, 1, 1, 1])
        otro = c[0].checkbox('¿Tiene otro trabajo?', value=bool(t2.get('otro')))
        tipo_t = c[1].text_input('¿Qué tipo de trabajo?', value=t2.get('tipo', ''))
        acc = c[2].checkbox('¿Tuvo algún accidente?', value=bool(t2.get('accidente')))
        trans = c[3].checkbox('¿De tránsito?', value=bool(t2.get('transito')))
        lab = c[4].checkbox('¿De trabajo?', value=bool(t2.get('laboral')))

        st.markdown('##### 3 · Antecedentes traumáticos (fracturas, luxaciones o esguinces)')
        tr = g('trauma') or {}
        df_tr = st.data_editor(
            pd.DataFrame({'Zona afectada': ZONAS, 'Sí': [bool(tr.get(z, {}).get('si')) for z in ZONAS],
                          'Fecha de la lesión': [tr.get(z, {}).get('fecha', '') for z in ZONAS]}),
            hide_index=True, use_container_width=True, disabled=['Zona afectada'], key=f'ddjj_tr_{k}')
        relato = st.text_area('Breve relato del hecho, dónde sufrió la lesión', value=g('relato') or '', height=68)

        st.markdown('##### 4 · Antecedentes familiares  ·  tildá quién la padece')
        fam = g('familia') or {}
        df_fam = st.data_editor(
            pd.DataFrame({'Enfermedad': FAMILIA, **{p: [bool(fam.get(e, {}).get(p)) for e in FAMILIA] for p in PARIENTES}}),
            hide_index=True, use_container_width=True, disabled=['Enfermedad'], key=f'ddjj_fam_{k}')
        fam_otras = st.text_input('Otras enfermedades familiares', value=g('familia_otras') or '')

        st.markdown('##### 5 · Hábitos')
        h = g('habitos') or {}
        c = st.columns([1, 1, 2])
        tab = c[0].checkbox('Tabaco', value=bool(h.get('tabaco')))
        alc = c[1].checkbox('Alcohol / sustancias', value=bool(h.get('alcohol')))
        alc_c = c[2].text_input('¿Cuál? (alcohol / sustancias)', value=h.get('alcohol_cual', ''))
        c = st.columns([1, 3])
        act = c[0].checkbox('Actividad física', value=bool(h.get('actividad')))
        act_c = c[1].text_input('¿Cuál? (actividad física)', value=h.get('actividad_cual', ''))
        c = st.columns([1, 3])
        med = c[0].checkbox('Medicamentos', value=bool(h.get('medicamentos')))
        med_c = c[1].text_input('¿Cuál? (medicamentos)', value=h.get('medicamentos_cual', ''))
        c = st.columns(2)
        dieta = c[0].text_input('Dieta habitual', value=h.get('dieta', ''))
        otros_h = c[1].text_input('Otros hábitos', value=h.get('otros', ''))

        st.markdown('##### 6 · Otros datos')
        intern = st.text_area('Antecedentes de internaciones en hospitales o clínicas (motivos)', value=g('internaciones') or '', height=68)
        cond = st.text_area('¿Presenta alguna condición especial que pueda interferir con la función para la cual será capacitado?',
                            value=g('condicion_especial') or '', height=68)
        ffirma = st.date_input('Fecha de firma (San Miguel de Tucumán)', value=_f(g('fecha_firma')) or fecha, format='DD/MM/YYYY')
        ok = st.form_submit_button('💾 Guardar DDJJ y generar PDF', type='primary', use_container_width=True)

    if ok and sec.exigir('examenes_periodicos'):
        d = {'fecha': str(fecha), 'documento': documento.strip(), 'apellidos_nombres': ape.strip(),
             'fecha_nac': str(fnac) if fnac else '', 'genero': gen, 'lugar_nac': lnac, 'nacionalidad': nac,
             'estado_civil': ec, 'hijos': hijos, 'domicilio': dom, 'localidad': loc, 'tel_fijo': tel, 'celular': cel,
             'email': mail, 'grupo': grupo, 'obra_social': os_, 'sintomas': nuevos,
             'detalle': {s: v for s, v in det_new.items() if v.strip()},
             'trabajo': {'otro': otro, 'tipo': tipo_t, 'accidente': acc, 'transito': trans, 'laboral': lab},
             'trauma': {r['Zona afectada']: {'si': bool(r['Sí']), 'fecha': str(r['Fecha de la lesión'] or '')}
                        for _, r in df_tr.iterrows()},
             'relato': relato, 'familia': {r['Enfermedad']: {p: bool(r[p]) for p in PARIENTES} for _, r in df_fam.iterrows()},
             'familia_otras': fam_otras,
             'habitos': {'tabaco': tab, 'alcohol': alc, 'alcohol_cual': alc_c, 'actividad': act, 'actividad_cual': act_c,
                         'medicamentos': med, 'medicamentos_cual': med_c, 'dieta': dieta, 'otros': otros_h},
             'internaciones': intern, 'condicion_especial': cond, 'fecha_firma': str(ffirma)}
        alertas = _alertas_ddjj(d)
        pdf = pdf_ddjj(d, anio)
        _guardar(id_leg, 'DDJJ', anio, d, 'Con alertas' if alertas else 'Sin alertas', len(alertas), pdf,
                 f'Ficha de Ingreso {anio} · Declaración Jurada de Salud')
        sec.registrar_auditoria('Fichas de Ingreso', 'DDJJ', f'DDJJ {anio} guardada ({len(alertas)} alertas)', id_leg)
        st.success(f'✅ DDJJ {anio} guardada y archivada en el legajo.')
        if alertas:
            st.warning('**Para evaluar en la ficha médica:** ' + ' · '.join(alertas))
        _descarga(pdf, f'DDJJ_{anio}_{id_leg}.pdf', f'ddjj_dl_{k}')


def _profesionales():
    try:
        conn = db.conectar(sec.DB_NAME)
        df = pd.read_sql_query('SELECT apellido_nombre, matricula FROM personal_gabinete ORDER BY apellido_nombre', conn)
        conn.close()
        return [f"{r['apellido_nombre']}" + (f" · {r['matricula']}" if r['matricula'] else '') for _, r in df.iterrows()]
    except Exception:
        return []


def _tab_ficha(id_leg, cad, px, anio):
    prev = _cargar(id_leg, 'FICHA', anio) or {}
    ddjj = _cargar(id_leg, 'DDJJ', anio) or {}
    k = f'{id_leg}_{anio}'
    g = prev.get
    if ddjj:
        al = _alertas_ddjj(ddjj)
        if al:
            st.warning('🩺 **La DDJJ declara:** ' + ' · '.join(al))
        else:
            st.info('🩺 La DDJJ no declara antecedentes ni síntomas.')
    else:
        st.caption('ℹ️ Este aspirante todavía no tiene DDJJ cargada: si la cargás primero, acá vas a ver sus antecedentes.')
    if prev:
        st.success(f"✔️ Ya tiene Ficha de Salud {anio} registrada ({prev.get('resultado', '')}). Podés corregirla o reimprimirla.")
        if st.button('🖨️ Generar PDF de la ficha guardada', key=f'fi_re_{k}'):
            _descarga(pdf_ficha(prev, anio), f'FichaSalud_{anio}_{id_leg}.pdf', f'fi_dlre_{k}')

    # Anexo A — mapa corporal interactivo (fuera del formulario para ver la vista previa en vivo)
    st.markdown('##### Anexo “A” · Inspección externa  ·  marcá cada hallazgo')
    base = pd.DataFrame(g('hallazgos') or [], columns=['region', 'tipo', 'descripcion'])
    c1, c2 = st.columns([1.25, 1])
    with c1:
        ed = st.data_editor(
            base.rename(columns={'region': 'Región', 'tipo': 'Tipo', 'descripcion': 'Descripción'}),
            num_rows='dynamic', use_container_width=True, hide_index=True, key=f'fi_hall_{k}',
            column_config={'Región': st.column_config.SelectboxColumn(options=list(REGIONES), required=True, width='medium'),
                           'Tipo': st.column_config.SelectboxColumn(options=list(TIPOS_HALLAZGO), required=True, width='small'),
                           'Descripción': st.column_config.TextColumn(width='medium')})
        st.caption('Agregá una fila por hallazgo (tatuaje, cicatriz, lunar, etc.). El número en el mapa es el N° de fila.')
        st.markdown(' '.join(f'<span style="color:{c};font-weight:700">● {t}</span>' for t, c in TIPOS_HALLAZGO.items()),
                    unsafe_allow_html=True)
    hallazgos = [{'region': r['Región'], 'tipo': r['Tipo'], 'descripcion': r['Descripción'] or ''}
                 for _, r in ed.iterrows() if r['Región'] in REGIONES]
    with c2:
        st.image(mapa_corporal(hallazgos, 520), use_container_width=True)

    profes = _profesionales()
    with st.form(f'ficha_{k}'):
        st.markdown('##### Datos del aspirante')
        c = st.columns([1, 2, 2])
        form_n = c[0].text_input('Formulario N°', value=g('formulario') or '')
        ape = c[1].text_input('Apellidos', value=g('apellidos') or px.get('APELLIDO', '') or cad['apellido_nombre'])
        nom = c[2].text_input('Nombres', value=g('nombres') or px.get('NOMBRES', ''))
        c = st.columns([1, 1, 2])
        dni = c[0].text_input('D.N.I.', value=g('dni') or ddjj.get('documento') or str(cad.get('dni') or px.get('DNI', '')))
        fnac = c[1].date_input('Fecha de nacimiento', value=_f(g('fecha_nac')) or _f(ddjj.get('fecha_nac'))
                               or _f(cad.get('fecha_nacimiento')), format='DD/MM/YYYY',
                               min_value=date(1950, 1, 1), max_value=date.today())
        dom = c[2].text_input('Domicilio', value=g('domicilio') or ' '.join(
            x for x in [ddjj.get('domicilio', ''), ddjj.get('localidad', '')] if x))
        consent = st.checkbox('El aspirante firmó el consentimiento para la inspección médica',
                              value=bool(g('consentimiento', True)))

        st.markdown('##### Evaluación')
        c = st.columns([1, 1, 1.3, 2])
        fev = c[0].date_input('Fecha de evaluación', value=_f(g('fecha_eval')) or sec.ahora_local().date(), format='DD/MM/YYYY')
        hv = g('hora')
        hora = c[1].time_input('Hora', value=datetime.strptime(hv, '%H:%M').time() if hv else time(8, 0), step=300)
        res = c[2].radio('Resultado', ['Sin novedad', 'Con novedad'], horizontal=True,
                         index=1 if (g('resultado') == 'Con novedad' or (not prev and hallazgos)) else 0)
        opciones = profes + ['Otro (escribir)']
        actual = g('profesional') or ''
        prof_sel = c[3].selectbox('Profesional que evalúa', opciones,
                                  index=opciones.index(actual) if actual in opciones else (len(opciones) - 1 if actual else 0))
        prof_txt = st.text_input('Profesional (si no está en la lista)', value=actual if actual not in opciones else '')
        obs_a = st.text_input('Observaciones del Anexo A', value=g('obs_anexo_a') or '')

        st.markdown('##### Anexo “B” · Aparato locomotor – inspección externa')
        loc = g('locomotor') or {}
        locv = {}
        c = st.columns(2)
        for i, (key, grupo, lado) in enumerate(LOCOMOTOR):
            locv[key] = c[i % 2].text_input(f'{grupo} · {lado}', value=loc.get(key, ''), placeholder='Sin particularidades')
        v = g('vision') or {}
        c = st.columns([1, 2, 1, 1, 1])
        ant = c[0].checkbox('¿Usa anteojos?', value=bool(v.get('anteojos')))
        mot = c[1].text_input('¿Por qué motivo?', value=v.get('motivo', ''))
        od = c[2].text_input('Agudeza OD', value=v.get('od', ''), placeholder='10/10')
        oi = c[3].text_input('Agudeza OI', value=v.get('oi', ''), placeholder='10/10')
        prot = c[4].checkbox('¿Prótesis dentales?', value=bool(g('protesis')))
        genito = st.text_input('Genitourinario', value=g('genitourinario') or '')
        cardio = st.text_input('Cardio-respiratorio', value=g('cardio') or '')
        otras = st.text_area('Otras observaciones', value=g('otras_obs') or '', height=68)
        ok = st.form_submit_button('💾 Guardar ficha y generar PDF', type='primary', use_container_width=True)

    if ok and sec.exigir('examenes_periodicos'):
        prof = prof_txt.strip() if prof_sel == 'Otro (escribir)' else prof_sel
        d = {'formulario': form_n, 'apellidos': ape.strip(), 'nombres': nom.strip(), 'dni': dni.strip(),
             'fecha_nac': str(fnac) if fnac else '', 'domicilio': dom, 'consentimiento': consent,
             'fecha_eval': str(fev), 'hora': hora.strftime('%H:%M'), 'resultado': res, 'profesional': prof,
             'hallazgos': hallazgos, 'obs_anexo_a': obs_a, 'locomotor': locv,
             'vision': {'anteojos': ant, 'motivo': mot, 'od': od, 'oi': oi}, 'protesis': prot,
             'genitourinario': genito, 'cardio': cardio, 'otras_obs': otras}
        if not consent:
            st.warning('⚠️ Se guardó sin consentimiento firmado: recordá obtenerlo antes de archivar.')
        pdf = pdf_ficha(d, anio)
        _guardar(id_leg, 'FICHA', anio, d, res, len(hallazgos), pdf, f'Ficha de Ingreso {anio} · Ficha de Salud / Inspección')
        sec.registrar_auditoria('Fichas de Ingreso', 'FICHA', f'Ficha de salud {anio}: {res}, {len(hallazgos)} hallazgos', id_leg)
        st.success(f'✅ Ficha de salud {anio} guardada ({res}) y archivada en el legajo.')
        _descarga(pdf, f'FichaSalud_{anio}_{id_leg}.pdf', f'fi_dl_{k}')


def _tab_seguimiento(df_cad, anio):
    res = _resumen(anio)
    dd = res[res['tipo'] == 'DDJJ'].set_index('id_legajo')
    fi = res[res['tipo'] == 'FICHA'].set_index('id_legajo')
    t = df_cad[['id_legajo', 'apellido_nombre', 'curso']].copy()
    t['id_legajo'] = t['id_legajo'].astype(str)
    t['DDJJ'] = t['id_legajo'].map(lambda x: '✅' if x in dd.index else '—')
    t['Alertas DDJJ'] = t['id_legajo'].map(lambda x: int(dd.loc[x, 'alertas']) if x in dd.index else 0)
    t['Ficha de salud'] = t['id_legajo'].map(lambda x: '✅' if x in fi.index else '—')
    t['Resultado'] = t['id_legajo'].map(lambda x: fi.loc[x, 'resultado'] if x in fi.index else '')
    n = max(len(t), 1)
    n_dd, n_fi = (t['DDJJ'] == '✅').sum(), (t['Ficha de salud'] == '✅').sum()
    n_cn = (t['Resultado'] == 'Con novedad').sum()
    k = st.columns(4)
    k[0].metric('Aspirantes', len(t))
    k[1].metric('DDJJ cargadas', f'{n_dd}', f'{n_dd / n:.0%}')
    k[2].metric('Fichas de salud', f'{n_fi}', f'{n_fi / n:.0%}')
    k[3].metric('Con novedad', int(n_cn))
    st.progress(min(1.0, (n_dd + n_fi) / (2 * n)), text=f'Campaña de ingreso {anio}: {(n_dd + n_fi) / (2 * n):.0%} completada')

    filtro = st.radio('Mostrar', ['Todos', 'Falta DDJJ', 'Falta ficha', 'Con novedad', 'DDJJ con alertas'],
                      horizontal=True, key='fi_filtro')
    v = {'Falta DDJJ': t[t['DDJJ'] == '—'], 'Falta ficha': t[t['Ficha de salud'] == '—'],
         'Con novedad': t[t['Resultado'] == 'Con novedad'], 'DDJJ con alertas': t[t['Alertas DDJJ'] > 0]}.get(filtro, t)
    st.dataframe(v.rename(columns={'id_legajo': 'Legajo', 'apellido_nombre': 'Aspirante', 'curso': 'Curso'}),
                 use_container_width=True, hide_index=True, height=380)
    buf = io.BytesIO()
    t.rename(columns={'id_legajo': 'Legajo', 'apellido_nombre': 'Aspirante', 'curso': 'Curso'}).to_excel(buf, index=False)
    st.download_button('⬇️ Descargar planilla de seguimiento (Excel)', buf.getvalue(),
                       f'seguimiento_ingreso_{anio}.xlsx', key='fi_xls')

    # Antecedentes más declarados en la cohorte
    if not dd.empty:
        conn = db.conectar(sec.DB_NAME)
        datos = pd.read_sql_query("SELECT datos FROM fichas_ingreso WHERE tipo = 'DDJJ' AND anio = ?", conn,
                                  params=(str(anio),))
        conn.close()
        cuenta = pd.Series([s for x in datos['datos'] for s in json.loads(x).get('sintomas', [])]).value_counts()
        if not cuenta.empty:
            st.markdown('##### Antecedentes más declarados en la cohorte')
            st.bar_chart(cuenta.head(12), horizontal=True, height=320)


def render(obtener_cadetes, excel_path):
    st.markdown('<div class="pro-header"><p class="pro-title">🗂️ Fichas de Ingreso</p>'
                '<p class="pro-subtitle">Declaración Jurada de Salud y Ficha de Salud / Inspección del comienzo de año: '
                'se cargan igual que en papel, se imprimen y quedan archivadas en el legajo.</p></div>',
                unsafe_allow_html=True)
    _asegurar()
    df_cad = obtener_cadetes()
    if df_cad.empty:
        st.warning('Primero cargá el padrón de cadetes (⚡ Carga Masiva → 👥 Padrón).')
        return
    hoy = sec.ahora_local().date()
    c1, c2 = st.columns([1, 4])
    anio = c1.selectbox('Ciclo lectivo', list(range(hoy.year + 1, hoy.year - 4, -1)), index=1, key='fi_anio')
    try:
        padron = _padron_excel(excel_path, os.path.getmtime(excel_path))
    except Exception:
        padron = {}
    t1, t2, t3 = st.tabs(['📝 Declaración Jurada de Salud', '🩺 Ficha de Salud / Inspección', f'📊 Seguimiento {anio}'])
    with t3:
        _tab_seguimiento(df_cad, anio)
    with c2:
        id_leg, cad, px = _encabezado_cadete(df_cad, anio, padron)
    with t1:
        _tab_ddjj(id_leg, cad, px, anio)
    with t2:
        _tab_ficha(id_leg, cad, px, anio)
