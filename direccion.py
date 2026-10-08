"""Herramientas de administración para la Dirección.

* Panel de Dirección: situación de fuerza, reposos vigentes, pendientes.
* Parte Sanitario Diario (PDF) para elevar a la superioridad.
* Respaldo del sistema (solo administradores).

Principio de mínimo dato clínico: estos tableros muestran estado y fechas de
reposo, nunca diagnósticos, síntomas ni resultados de estudios.
"""
import hashlib
import io
import os
import sqlite3
import tempfile
import zipfile
from datetime import timedelta
from xml.sax.saxutils import escape

import pandas as pd
import streamlit as st

import seguridad as sec

DIAS_ALERTA_VENCIMIENTO = 3


# ---------------------------------------------------------------------------
# Cálculo de situación (sirve a la pantalla y al PDF)
# ---------------------------------------------------------------------------
def _leer(db_name):
  conn = sqlite3.connect(db_name)
  try:
    cad = pd.read_sql_query('SELECT id_legajo, apellido_nombre, curso FROM cadetes', conn)
    notas = pd.read_sql_query('SELECT * FROM notas_medicas', conn)
    inter = pd.read_sql_query(
        'SELECT id_legajo, fecha_hora, derivacion FROM primera_intervencion', conn)
    exa = pd.read_sql_query('SELECT id_legajo, anio FROM examenes_periodicos', conn)
  finally:
    conn.close()
  return cad, notas, inter, exa


def calcular_situacion(db_name, fecha):
  """Foto de la situación sanitaria de la compañía a una fecha dada."""
  cad, notas, inter, exa = _leer(db_name)
  f = pd.Timestamp(fecha).normalize()
  cad['id_legajo'] = cad['id_legajo'].astype(str)
  cols_rep = ['Legajo', 'Cadete', 'Curso', 'Tipo', 'Desde', 'Hasta', 'Días restantes']

  if notas.empty:
    vig = venc = pd.DataFrame()
  else:
    notas['id_legajo'] = notas['id_legajo'].astype(str)
    notas = notas.merge(cad, on='id_legajo', how='left')
    notas['desde'] = pd.to_datetime(notas['fecha_desde'], errors='coerce').dt.normalize()
    notas['hasta'] = pd.to_datetime(notas['fecha_hasta'], errors='coerce').dt.normalize()
    if 'fecha_alta_efectiva' in notas:
      alta_ef = pd.to_datetime(notas['fecha_alta_efectiva'], errors='coerce').dt.normalize()
    else:
      alta_ef = pd.Series(pd.NaT, index=notas.index)
    cerrada = (notas['estado_alta'] == 'Alta Convalidada') & (alta_ef.isna() | (alta_ef <= f))
    dentro = (notas['desde'].isna() | (notas['desde'] <= f)) & (notas['hasta'] >= f)
    vig = notas[dentro & ~cerrada].copy()
    vig['dias_restantes'] = (vig['hasta'] - f).dt.days
    venc = notas[(notas['estado_alta'] == 'Pendiente') & (notas['hasta'] < f)].copy()
    venc['dias_atraso'] = (f - venc['hasta']).dt.days

  def _fmt(df, extra):
    if df.empty:
      return pd.DataFrame(columns=cols_rep if extra == 'restantes' else cols_rep[:-1] + ['Días de atraso'])
    out = pd.DataFrame({
        'Legajo': df['id_legajo'], 'Cadete': df['apellido_nombre'].fillna('(sin padrón)'),
        'Curso': df['curso'].fillna('-'), 'Tipo': df['tipo_reposo'].fillna('-'),
        'Desde': df['desde'].dt.strftime('%d/%m/%Y'), 'Hasta': df['hasta'].dt.strftime('%d/%m/%Y'),
    })
    if extra == 'restantes':
      out['Días restantes'] = df['dias_restantes'].astype(int)
      return out.sort_values('Días restantes')
    out['Días de atraso'] = df['dias_atraso'].astype(int)
    return out.sort_values('Días de atraso', ascending=False)

  vigentes = _fmt(vig, 'restantes')
  vencidas = _fmt(venc, 'atraso')
  por_vencer = vigentes[vigentes['Días restantes'] <= DIAS_ALERTA_VENCIMIENTO] if len(vigentes) else vigentes

  en_reposo_ids = set(vigentes['Legajo']) if len(vigentes) else set()
  efectivos = len(cad)
  en_reposo = len(en_reposo_ids & set(cad['id_legajo']))

  # Novedades de guardia
  if inter.empty:
    del_dia = pd.DataFrame(columns=['Hora', 'Legajo', 'Cadete', 'Curso', 'Derivación'])
    sem = 0
    atenciones_curso = pd.Series(dtype=int)
  else:
    inter['id_legajo'] = inter['id_legajo'].astype(str)
    inter['fecha'] = pd.to_datetime(inter['fecha_hora'], errors='coerce')
    inter = inter.merge(cad, on='id_legajo', how='left')
    dia = inter[inter['fecha'].dt.normalize() == f]
    del_dia = pd.DataFrame({
        'Hora': dia['fecha'].dt.strftime('%H:%M'), 'Legajo': dia['id_legajo'],
        'Cadete': dia['apellido_nombre'].fillna('(sin padrón)'), 'Curso': dia['curso'].fillna('-'),
        'Derivación': dia['derivacion'].fillna('-').astype(str).str.split(' - ').str[0],
    }).sort_values('Hora')
    ult7 = inter[(inter['fecha'].dt.normalize() > f - pd.Timedelta(days=7)) & (inter['fecha'].dt.normalize() <= f)]
    sem = len(ult7)
    atenciones_curso = ult7.groupby('curso').size()

  # Situación por curso
  por_curso = cad.groupby('curso').size().rename('Efectivos').to_frame()
  rep_curso = pd.Series(dtype=int)
  if len(vigentes):
    rep_curso = vigentes.drop_duplicates('Legajo').groupby('Curso').size()
  por_curso['En reposo'] = rep_curso.reindex(por_curso.index).fillna(0).astype(int)
  por_curso['Disponibles'] = por_curso['Efectivos'] - por_curso['En reposo']
  por_curso['Disponibilidad'] = (100 * por_curso['Disponibles'] / por_curso['Efectivos'].clip(lower=1)).round(1)
  por_curso['Atenciones 7 días'] = atenciones_curso.reindex(por_curso.index).fillna(0).astype(int)
  por_curso = por_curso.reset_index().rename(columns={'curso': 'Curso'})

  # Sin examen periódico del año
  anio = str(f.year)
  con_examen = set(exa[exa['anio'].astype(str) == anio]['id_legajo'].astype(str)) if not exa.empty else set()
  sin_examen = cad[~cad['id_legajo'].isin(con_examen)][['id_legajo', 'apellido_nombre', 'curso']].rename(
      columns={'id_legajo': 'Legajo', 'apellido_nombre': 'Cadete', 'curso': 'Curso'})

  return {
      'fecha': f, 'efectivos': efectivos, 'en_reposo': en_reposo,
      'disponibles': efectivos - en_reposo,
      'disponibilidad': round(100 * (efectivos - en_reposo) / efectivos, 1) if efectivos else 0.0,
      'vigentes': vigentes, 'por_vencer': por_vencer, 'vencidas': vencidas,
      'guardia_dia': del_dia, 'guardia_7d': sem, 'por_curso': por_curso, 'sin_examen': sin_examen,
      'anio_examen': anio,
  }


# ---------------------------------------------------------------------------
# Parte sanitario diario (PDF)
# ---------------------------------------------------------------------------
def generar_parte_pdf(sit, emitido_por):
  from reportlab.lib import colors
  from reportlab.lib.pagesizes import A4
  from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
  from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

  buf = io.BytesIO()
  doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=44,
                          title='Parte Sanitario Diario', author=emitido_por)
  ss = getSampleStyleSheet()
  base = ParagraphStyle('b', parent=ss['Normal'], fontName='Helvetica', fontSize=8, leading=10)
  cab = ParagraphStyle('c', parent=base, fontName='Helvetica-Bold', textColor=colors.white)
  tit = ParagraphStyle('t', parent=ss['Title'], fontSize=16, leading=19, spaceAfter=2)
  sub = ParagraphStyle('s', parent=base, alignment=1, textColor=colors.HexColor('#475569'), fontSize=9)
  h2 = ParagraphStyle('h2', parent=ss['Heading3'], fontName='Helvetica-Bold', fontSize=10.5,
                      textColor=colors.HexColor('#1E3A8A'), spaceBefore=10, spaceAfter=4)
  azul, zebra, borde = colors.HexColor('#1E3A8A'), colors.HexColor('#F1F5F9'), colors.HexColor('#CBD5E1')

  def P(t, est=base):
    return Paragraph(escape(str(t)), est)

  def tabla(df, anchos, vacio):
    if df is None or len(df) == 0:
      return Paragraph(f'<i>{escape(vacio)}</i>', base)
    filas = [[P(c, cab) for c in df.columns]] + [[P(v) for v in r] for r in df.itertuples(index=False)]
    t = Table(filas, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), azul), ('GRID', (0, 0), (-1, -1), 0.25, borde),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, zebra]), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t

  f = sit['fecha']
  el = [
      Paragraph('PARTE SANITARIO DIARIO', tit),
      Paragraph('Dirección de Gabinete Interdisciplinario · Dirección General de Institutos e Instrucción'
                ' · Policía de Tucumán', sub),
      Paragraph(f'Fecha del parte: <b>{f:%d/%m/%Y}</b> · Emitido por: {escape(emitido_por)} · '
                f'Hora de emisión: {sec.ahora_local():%d/%m/%Y %H:%M}', sub),
      Spacer(1, 8)]

  resumen = Table([
      [P('Efectivos', cab), P('En reposo', cab), P('Disponibles', cab), P('Disponibilidad', cab),
       P('Altas vencidas s/ convalidar', cab), P(f'Guardia del día', cab)],
      [P(sit['efectivos']), P(sit['en_reposo']), P(sit['disponibles']), P(f"{sit['disponibilidad']:.1f}%"),
       P(len(sit['vencidas'])), P(len(sit['guardia_dia']))]],
      colWidths=[80, 80, 80, 90, 120, 73])
  resumen.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), azul), ('GRID', (0, 0), (-1, -1), 0.25, borde),
      ('FONTSIZE', (0, 1), (-1, 1), 12), ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
  el += [resumen, Paragraph('Situación por curso', h2),
         tabla(sit['por_curso'].assign(Disponibilidad=sit['por_curso']['Disponibilidad'].map('{:.1f}%'.format)),
               [118, 70, 70, 80, 90, 95], 'Sin cursos cargados.'),
         Paragraph(f'Novedades de guardia del día ({len(sit["guardia_dia"])})', h2),
         tabla(sit['guardia_dia'], [40, 55, 180, 78, 170], 'Sin novedades de guardia en la fecha.'),
         Paragraph(f'Reposos vigentes ({len(sit["vigentes"])})', h2),
         tabla(sit['vigentes'], [46, 145, 55, 98, 58, 58, 63], 'Sin reposos vigentes.'),
         Paragraph(f'Reposos que vencen en los próximos {DIAS_ALERTA_VENCIMIENTO} días ({len(sit["por_vencer"])})', h2),
         tabla(sit['por_vencer'], [46, 145, 55, 98, 58, 58, 63], 'Sin vencimientos próximos.'),
         Paragraph(f'Altas médicas vencidas sin convalidar ({len(sit["vencidas"])})', h2),
         tabla(sit['vencidas'], [46, 145, 55, 98, 58, 58, 63], 'Sin altas pendientes de convalidación.'),
         Spacer(1, 30),
         Paragraph('_______________________________<br/>Firma y sello del responsable', sub)]

  def pie(canvas, d):
    canvas.saveState()
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(colors.HexColor('#64748B'))
    canvas.drawString(36, 24, 'Documento reservado. No contiene diagnósticos ni datos clínicos.')
    canvas.drawRightString(A4[0] - 36, 24, f'Página {d.page}')
    canvas.restoreState()

  doc.build(el, onFirstPage=pie, onLaterPages=pie)
  return buf.getvalue()


# ---------------------------------------------------------------------------
# Pantalla: Panel de Dirección
# ---------------------------------------------------------------------------
def _auditar_export(detalle):
  sec.registrar_auditoria('Panel de Dirección', 'EXPORT', detalle)


def pagina_panel(db_name, kpi_card, fecha_larga_es):
  if not sec.exigir('panel_direccion'):
    return
  hoy = sec.ahora_local().date()
  sit = calcular_situacion(db_name, hoy)

  st.markdown(
      '<div class="pro-header"><p class="pro-title">🏛️ Panel de Dirección</p>'
      f'<p class="pro-subtitle">Situación sanitaria de la compañía · {fecha_larga_es(hoy)}</p></div>',
      unsafe_allow_html=True)

  c = st.columns(3)
  c[0].markdown(kpi_card('👥', sit['efectivos'], 'Efectivos', '#38BDF8', 'Cadetes en padrón'), unsafe_allow_html=True)
  c[1].markdown(kpi_card('🛌', sit['en_reposo'], 'En reposo hoy', '#F59E0B',
                         f'{len(sit["por_vencer"])} vencen en {DIAS_ALERTA_VENCIMIENTO} días'), unsafe_allow_html=True)
  col_disp = '#10B981' if sit['disponibilidad'] >= 90 else '#F59E0B' if sit['disponibilidad'] >= 80 else '#EF4444'
  c[2].markdown(kpi_card('✅', f'{sit["disponibilidad"]:.1f}%', 'Disponibilidad', col_disp,
                         f'{sit["disponibles"]} aptos para actividad'), unsafe_allow_html=True)
  st.markdown('<div style="height:0.8rem"></div>', unsafe_allow_html=True)
  c = st.columns(3)
  c[0].markdown(kpi_card('⏰', len(sit['vencidas']), 'Altas vencidas', '#EF4444', 'Pendientes de convalidar'), unsafe_allow_html=True)
  c[1].markdown(kpi_card('🩺', len(sit['guardia_dia']), 'Guardia hoy', '#38BDF8', f'{sit["guardia_7d"]} en los últimos 7 días'), unsafe_allow_html=True)
  c[2].markdown(kpi_card('🧪', len(sit['sin_examen']), f'Sin examen {sit["anio_examen"]}', '#A78BFA', 'Examen periódico anual'), unsafe_allow_html=True)
  st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

  t1, t2, t3, t4 = st.tabs(['🎓 Situación por curso', '🛌 Reposos vigentes', '📌 Pendientes de gestión', '📄 Parte diario'])

  with t1:
    pc = sit['por_curso']
    if pc.empty:
      st.info('Aún no hay cadetes cargados.')
    else:
      st.dataframe(
          pc, use_container_width=True, hide_index=True,
          column_config={'Disponibilidad': st.column_config.ProgressColumn(
              'Disponibilidad', format='%.0f%%', min_value=0, max_value=100)})
      st.bar_chart(pc.set_index('Curso')[['Disponibles', 'En reposo']], color=['#10B981', '#F59E0B'], height=260)

  with t2:
    v = sit['vigentes']
    if v.empty:
      st.success('No hay reposos vigentes en este momento.')
    else:
      cursos = sorted(v['Curso'].unique())
      sel = st.multiselect('Filtrar por curso', cursos, default=cursos, key='dir_cursos')
      vv = v[v['Curso'].isin(sel)]
      st.caption(f'{len(vv)} reposos · ordenados por días restantes (los más próximos a vencer, primero).')
      st.dataframe(vv, use_container_width=True, hide_index=True)
      st.download_button('⬇️ Descargar reposos vigentes (CSV)', vv.to_csv(index=False).encode('utf-8-sig'),
                         file_name=f'reposos_vigentes_{hoy}.csv', mime='text/csv', key='dir_dl_vig',
                         on_click=_auditar_export, args=(f'CSV de reposos vigentes ({len(vv)} filas)',))

  with t3:
    st.markdown('**⏰ Altas vencidas sin convalidar**')
    if sit['vencidas'].empty:
      st.success('Todas las altas están al día.')
    else:
      st.warning(f'{len(sit["vencidas"])} reposos ya vencieron y siguen sin alta convalidada. Gestionar en «3. Control de Alta».')
      st.dataframe(sit['vencidas'], use_container_width=True, hide_index=True)
    st.markdown(f'**⏳ Vencen en los próximos {DIAS_ALERTA_VENCIMIENTO} días**')
    if sit['por_vencer'].empty:
      st.info('Sin vencimientos próximos.')
    else:
      st.dataframe(sit['por_vencer'], use_container_width=True, hide_index=True)
    st.markdown(f'**🧪 Cadetes sin examen periódico {sit["anio_examen"]}**')
    se = sit['sin_examen']
    if se.empty:
      st.success('Todos los cadetes tienen su examen periódico del año.')
    else:
      with st.expander(f'Ver listado ({len(se)})'):
        st.dataframe(se, use_container_width=True, hide_index=True)

  with t4:
    st.caption('Genere el parte para elevar a la superioridad. Solo incluye estado y fechas de reposo; no contiene diagnósticos.')
    fecha = st.date_input('Fecha del parte', value=hoy, max_value=hoy, key='dir_fecha_parte')
    sit_p = calcular_situacion(db_name, fecha)
    m = st.columns(4)
    m[0].metric('Efectivos', sit_p['efectivos'])
    m[1].metric('En reposo', sit_p['en_reposo'])
    m[2].metric('Disponibilidad', f'{sit_p["disponibilidad"]:.1f}%')
    m[3].metric('Guardia del día', len(sit_p['guardia_dia']))
    yo = st.session_state.get('auth_user') or {}
    quien = f'{yo.get("nombre") or yo.get("nombre_completo") or ""} ({yo.get("username", "")})'
    pdf = generar_parte_pdf(sit_p, quien)
    st.download_button('⬇️ Descargar Parte Sanitario (PDF)', pdf, file_name=f'parte_sanitario_{fecha}.pdf',
                       mime='application/pdf', key='dir_dl_parte',
                       on_click=_auditar_export, args=(f'Parte sanitario diario {fecha}',))
    if fecha != hoy:
      st.caption('Para fechas pasadas el parte se reconstruye con el estado actual de los registros.')


# ---------------------------------------------------------------------------
# Pantalla: Respaldo del sistema
# ---------------------------------------------------------------------------
def _snapshot_db(db_name):
  """Copia consistente de la base (API de backup de SQLite) como bytes."""
  fd, tmp = tempfile.mkstemp(suffix='.db')
  os.close(fd)
  try:
    src = sqlite3.connect(db_name)
    dst = sqlite3.connect(tmp)
    src.backup(dst)
    dst.close()
    src.close()
    with open(tmp, 'rb') as fh:
      return fh.read()
  finally:
    os.remove(tmp)


def generar_respaldo(db_name, upload_dir, incluir_docs):
  datos_db = _snapshot_db(db_name)
  buf = io.BytesIO()
  n_docs = 0
  with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr(os.path.basename(db_name), datos_db)
    if incluir_docs and os.path.isdir(upload_dir):
      for raiz, _, archivos in os.walk(upload_dir):
        for a in archivos:
          ruta = os.path.join(raiz, a)
          z.write(ruta, os.path.join('documentos', os.path.relpath(ruta, upload_dir)))
          n_docs += 1
    yo = (st.session_state.get('auth_user') or {}).get('username', '')
    z.writestr('LEEME.txt', (
        'Respaldo del Sistema de Gabinete Interdisciplinario\n'
        f'Generado: {sec.ahora_local():%d/%m/%Y %H:%M} por {yo}\n'
        f'SHA-256 de la base: {hashlib.sha256(datos_db).hexdigest()}\n'
        f'Documentos PDF incluidos: {n_docs}\n\n'
        'Para restaurar: detener la app, reemplazar el archivo .db y la carpeta de documentos.\n'
        'Contiene información sanitaria confidencial: guárdelo cifrado y fuera del repositorio.\n'))
  return buf.getvalue(), n_docs


def pagina_respaldo(db_name, upload_dir):
  if not sec.exigir('respaldo'):
    return
  st.markdown(
      '<div class="pro-header"><p class="pro-title">💾 Respaldo del Sistema</p>'
      '<p class="pro-subtitle">Copia de seguridad de la base de datos y de los documentos adjuntos.</p></div>',
      unsafe_allow_html=True)
  st.warning(
      'Si el sistema está alojado en Streamlit Community Cloud, el disco es temporal: los datos pueden perderse'
      ' al reiniciar la app. Descargue respaldos periódicos y guárdelos fuera del repositorio.')

  conn = sqlite3.connect(db_name)
  try:
    ult = conn.execute(
        "SELECT fecha_hora, usuario FROM auditoria_logs WHERE modulo = 'Respaldo' AND accion = 'EXPORT'"
        ' ORDER BY id DESC LIMIT 1').fetchone()
    tablas = ['cadetes', 'notas_medicas', 'primera_intervencion', 'legajo_documentos',
              'examenes_periodicos', 'usuarios', 'auditoria_logs']
    conteos = {}
    for t in tablas:
      try:
        conteos[t] = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
      except sqlite3.Error:
        conteos[t] = 0
  finally:
    conn.close()

  tam_db = os.path.getsize(db_name) / 1024 if os.path.exists(db_name) else 0
  n_pdf = sum(len(f) for _, _, f in os.walk(upload_dir)) if os.path.isdir(upload_dir) else 0
  k = st.columns(3)
  k[0].metric('Tamaño de la base', f'{tam_db:,.0f} KB')
  k[1].metric('Documentos PDF', n_pdf)
  k[2].metric('Último respaldo', ult[0][:16] if ult else 'Nunca')
  st.dataframe(pd.DataFrame({'Tabla': list(conteos), 'Registros': list(conteos.values())}),
               use_container_width=True, hide_index=True)

  incluir = st.checkbox('Incluir documentos PDF adjuntos (puede ser pesado)', value=True, key='resp_docs')
  if st.button('🔧 Generar respaldo', key='resp_gen'):
    with st.spinner('Generando respaldo...'):
      datos, n_docs = generar_respaldo(db_name, upload_dir, incluir)
    st.session_state['respaldo_zip'] = (datos, n_docs, sec.ahora_local().strftime('%Y%m%d_%H%M'))
  if st.session_state.get('respaldo_zip'):
    datos, n_docs, sello = st.session_state['respaldo_zip']
    st.success(f'Respaldo listo: {len(datos) / 1024:,.0f} KB · {n_docs} documentos incluidos.')
    st.download_button('⬇️ Descargar respaldo (ZIP)', datos, file_name=f'respaldo_gabinete_{sello}.zip',
                       mime='application/zip', key='resp_dl',
                       on_click=sec.registrar_auditoria,
                       args=('Respaldo', 'EXPORT', f'Descarga de respaldo del sistema ({n_docs} documentos)'))
