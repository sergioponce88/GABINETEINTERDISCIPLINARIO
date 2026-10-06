"""Análisis avanzado de datos sanitarios (pestaña extra del módulo 7).

Todo se calcula sobre la base SQLite con pandas; no requiere Spark.
Los resultados son indicadores de gestión y alertas para revisión
profesional: no constituyen diagnósticos.
"""
import io
import os
import re
import sqlite3
import unicodedata
import zipfile
from collections import Counter
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

import seguridad as sec

DIAS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

STOPWORDS = set(
    'para pero como esta este esto estos estas desde hasta entre sobre luego'
    ' porque cuando donde tiene tuvo tiene tambien muy mas menos sin con por los'
    ' las del una uno unos unas que fue son ser esta estan refiere refirio'
    ' presenta presento paciente cadete dolor aqueja'.split()
)


# ---------------------------------------------------------------------------
# Carga (cacheada: se invalida sola cuando cambia el archivo de la base)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=600)
def _cargar(db_name, stamp):
  conn = sqlite3.connect(db_name)
  tablas = {
      'cad': 'SELECT * FROM cadetes',
      'inter': 'SELECT * FROM primera_intervencion',
      'notas': 'SELECT * FROM notas_medicas',
      'exa': 'SELECT * FROM examenes_periodicos',
  }
  out = {k: pd.read_sql_query(q, conn) for k, q in tablas.items()}
  conn.close()
  return out


def _sin_acentos(texto):
  return ''.join(
      c for c in unicodedata.normalize('NFKD', str(texto)) if not unicodedata.combining(c)
  )


def _parse_pa(valor):
  m = re.search(r'(\d{1,3})\s*[/\\-]\s*(\d{1,3})', str(valor))
  if not m:
    return None, None
  s, d = int(m.group(1)), int(m.group(2))
  if s < 30:  # cargado en cmHg (ej. 12/8)
    s, d = s * 10, d * 10
  return (s, d) if 50 <= s <= 280 and 30 <= d <= 180 else (None, None)


def _parse_spo2(valor):
  m = re.search(r'(\d{2,3})', str(valor))
  if not m:
    return None
  v = int(m.group(1))
  return v if 50 <= v <= 100 else None


def _parse_temp(valor):
  try:
    v = float(str(valor).replace(',', '.').strip())
    return v if 30 <= v <= 45 else None
  except ValueError:
    return None


def _categoria_pa(s, d):
  if pd.isna(s):
    return 'Sin dato'
  if s < 90 or d < 60:
    return 'Baja (<90/60)'
  if s >= 140 or d >= 90:
    return 'Elevada nivel 2 (≥140/90)'
  if s >= 130 or d >= 80:
    return 'Elevada nivel 1 (130-139/80-89)'
  if s >= 120:
    return 'Levemente elevada (120-129/<80)'
  return 'Normal'


def _vacio(msg='Sin datos suficientes en el período seleccionado.'):
  st.info(msg)


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------
def render(db_name):
  try:
    stamp = os.stat(db_name).st_mtime_ns
  except OSError:
    stamp = 0
  datos = _cargar(db_name, stamp)
  cad, inter, notas, exa = (datos['cad'].copy(), datos['inter'].copy(),
                            datos['notas'].copy(), datos['exa'].copy())
  hoy = sec.ahora_local().date()

  st.markdown('#### 🔬 Análisis avanzado')
  st.caption('Indicadores calculados sobre los registros cargados. Los umbrales clínicos son'
             ' orientativos y requieren valoración profesional.')

  # --- Filtros -------------------------------------------------------------
  f1, f2 = st.columns([2, 3])
  with f1:
    rango = st.date_input('Período de análisis', value=(hoy - timedelta(days=90), hoy), key='an_rango')
  with f2:
    cursos = sorted(cad['curso'].dropna().unique().tolist())
    sel_cursos = st.multiselect('Curso', cursos, default=cursos, key='an_cursos')
  if isinstance(rango, (tuple, list)) and len(rango) == 2:
    ini, fin = rango
  else:
    ini = fin = rango[0] if isinstance(rango, (tuple, list)) else rango
  ini_ts, fin_ts = pd.Timestamp(ini), pd.Timestamp(fin) + pd.Timedelta(hours=23, minutes=59, seconds=59)
  dias_periodo = (pd.Timestamp(fin) - pd.Timestamp(ini)).days + 1

  cad['id_legajo'] = cad['id_legajo'].astype(str)
  cad_f = cad[cad['curso'].isin(sel_cursos)]
  n_cad = max(len(cad_f), 1)

  # --- Intervenciones (guardia) ----------------------------------------------
  if not inter.empty:
    inter['id_legajo'] = inter['id_legajo'].astype(str)
    inter['fecha'] = pd.to_datetime(inter['fecha_hora'], errors='coerce')
    inter = inter.merge(cad[['id_legajo', 'apellido_nombre', 'curso', 'genero']], on='id_legajo', how='left')
  int_f = inter[(inter['fecha'] >= ini_ts) & (inter['fecha'] <= fin_ts)
                & (inter['curso'].isin(sel_cursos))] if not inter.empty else inter
  # período anterior de igual duración (para comparar)
  prev_ini, prev_fin = ini_ts - pd.Timedelta(days=dias_periodo), ini_ts - pd.Timedelta(seconds=1)
  int_prev = inter[(inter['fecha'] >= prev_ini) & (inter['fecha'] <= prev_fin)
                   & (inter['curso'].isin(sel_cursos))] if not inter.empty else inter

  # --- Reposos ------------------------------------------------------------------
  if not notas.empty:
    notas['id_legajo'] = notas['id_legajo'].astype(str)
    notas['desde'] = pd.to_datetime(notas['fecha_desde'], errors='coerce')
    notas['hasta'] = pd.to_datetime(notas['fecha_hasta'], errors='coerce')
    notas = notas.merge(cad[['id_legajo', 'apellido_nombre', 'curso']], on='id_legajo', how='left')
    notas['dias_reposo'] = ((notas['hasta'] - notas['desde']).dt.days + 1).clip(lower=0)
    solape_ini = notas['desde'].clip(lower=pd.Timestamp(ini))
    solape_fin = notas['hasta'].clip(upper=pd.Timestamp(fin))
    notas['dias_en_periodo'] = ((solape_fin - solape_ini).dt.days + 1).clip(lower=0)
  rep_f = notas[(notas['dias_en_periodo'] > 0) & (notas['curso'].isin(sel_cursos))] if not notas.empty else notas

  # --- KPIs ---------------------------------------------------------------------
  n_int, n_prev = len(int_f), len(int_prev)
  unicos = int_f['id_legajo'].nunique() if n_int else 0
  dias_rep = int(rep_f['dias_en_periodo'].sum()) if len(rep_f) else 0
  mediana_rep = float(rep_f['dias_reposo'].median()) if len(rep_f) else 0.0
  ausentismo = 100 * dias_rep / (n_cad * dias_periodo) if dias_periodo else 0
  vencidas = 0
  if not notas.empty:
    pend = notas[(notas['estado_alta'] == 'Pendiente') & (notas['curso'].isin(sel_cursos))]
    vencidas = int((pend['hasta'] < pd.Timestamp(hoy)).sum())

  k = st.columns(6)
  k[0].metric('Atenciones de guardia', n_int, delta=(n_int - n_prev) if n_prev or n_int else None,
              help='Variación vs. el período anterior de igual duración.')
  k[1].metric('Cadetes atendidos', unicos, help=f'{100 * unicos / n_cad:.1f}% de {len(cad_f)} cadetes.')
  k[2].metric('Atenciones c/100 cadetes', f'{100 * n_int / n_cad:.1f}')
  k[3].metric('Días de reposo (período)', dias_rep)
  k[4].metric('Ausentismo por reposo', f'{ausentismo:.2f}%',
              help='Días de reposo ÷ (cadetes × días del período).')
  k[5].metric('Altas vencidas sin convalidar', vencidas)

  t1, t2, t3, t4, t5 = st.tabs([
      '📈 Demanda', '🫀 Signos vitales', '🛌 Reposos y altas', '🎯 Concentración', '🧹 Calidad de datos'])

  tablas_export = {}

  # === DEMANDA ===============================================================
  with t1:
    if n_int == 0:
      _vacio()
    else:
      semanal = (int_f.set_index('fecha').resample('W').size().rename('Atenciones').reset_index())
      semanal['Media móvil 4 sem.'] = semanal['Atenciones'].rolling(4, min_periods=1).mean().round(2)
      base = alt.Chart(semanal).encode(x=alt.X('fecha:T', title='Semana'))
      graf = (base.mark_bar(opacity=0.55).encode(y=alt.Y('Atenciones:Q', title=None))
              + base.mark_line(color='#F59E0B', point=True).encode(y='Media móvil 4 sem.:Q'))
      st.markdown('**Atenciones por semana y tendencia**')
      st.altair_chart(graf.properties(height=230), use_container_width=True)
      tablas_export['demanda_semanal'] = semanal

      st.markdown('**¿Cuándo se concentra la demanda?** (día de la semana × franja horaria)')
      calor = int_f.dropna(subset=['fecha']).copy()
      calor['Día'] = calor['fecha'].dt.weekday.map(dict(enumerate(DIAS_ES)))
      calor['h0'] = (calor['fecha'].dt.hour // 3) * 3
      calor['Franja'] = calor['h0'].map(lambda h: f'{h:02d}–{(h + 3) % 24:02d} h')
      mat = calor.groupby(['Día', 'Franja', 'h0']).size().rename('Atenciones').reset_index()
      hm = alt.Chart(mat).mark_rect().encode(
          x=alt.X('Franja:N', sort=alt.EncodingSortField('h0'), title=None),
          y=alt.Y('Día:N', sort=DIAS_ES, title=None),
          color=alt.Color('Atenciones:Q', scale=alt.Scale(scheme='blues')),
          tooltip=['Día', 'Franja', 'Atenciones']).properties(height=230)
      st.altair_chart(hm, use_container_width=True)
      tablas_export['demanda_dia_franja'] = mat.drop(columns='h0')

      st.markdown('**Motivos de consulta más frecuentes** (palabras clave del campo «síntomas»)')
      palabras = Counter()
      for texto in int_f['sintomas'].dropna():
        for w in re.findall(r'[a-z]{4,}', _sin_acentos(texto).lower()):
          if w not in STOPWORDS:
            palabras[w] += 1
      if palabras:
        df_kw = pd.DataFrame(palabras.most_common(15), columns=['Término', 'Menciones'])
        st.altair_chart(alt.Chart(df_kw).mark_bar().encode(
            y=alt.Y('Término:N', sort='-x', title=None), x=alt.X('Menciones:Q', title=None),
            tooltip=['Término', 'Menciones']).properties(height=300), use_container_width=True)
        tablas_export['motivos_palabras_clave'] = df_kw
      else:
        _vacio('No hay texto de síntomas para analizar.')

      st.markdown('**Derivaciones**')
      der = int_f['derivacion'].fillna('Sin dato').str.split(' - ').str[0].value_counts().rename_axis(
          'Derivación').reset_index(name='Casos')
      st.dataframe(der, use_container_width=True, hide_index=True)
      tablas_export['derivaciones'] = der

  # === SIGNOS VITALES ==========================================================
  with t2:
    if n_int == 0:
      _vacio()
    else:
      sv = int_f.copy()
      pa = sv['presion'].map(_parse_pa) if 'presion' in sv else pd.Series([(None, None)] * len(sv))
      sv['sis'] = pa.map(lambda t: t[0])
      sv['dia'] = pa.map(lambda t: t[1])
      sv['spo2'] = sv['saturacion'].map(_parse_spo2) if 'saturacion' in sv else None
      sv['temp'] = sv['temperatura'].map(_parse_temp) if 'temperatura' in sv else None
      for _c in ('sis', 'dia', 'spo2', 'temp'):
        sv[_c] = pd.to_numeric(sv[_c], errors='coerce')
      sv['Categoría PA'] = [_categoria_pa(s, d) for s, d in zip(sv['sis'], sv['dia'])]

      c1, c2 = st.columns(2)
      with c1:
        st.markdown('**Presión arterial (clasificación orientativa)**')
        dist = sv['Categoría PA'].value_counts().rename_axis('Categoría').reset_index(name='Casos')
        st.dataframe(dist, use_container_width=True, hide_index=True)
      with c2:
        st.markdown('**Cobertura de datos**')
        cob = pd.DataFrame({
            'Variable': ['Presión arterial', 'Saturación O₂', 'Temperatura'],
            'Registros válidos': [int(sv['sis'].notna().sum()), int(sv['spo2'].notna().sum()),
                                  int(sv['temp'].notna().sum()) if 'temp' in sv else 0],
            'Total': n_int})
        cob['%'] = (100 * cob['Registros válidos'] / cob['Total']).round(1)
        st.dataframe(cob, use_container_width=True, hide_index=True)

      umbral_spo2 = st.slider('Alertar saturación menor a (%)', 85, 99, 94, key='an_spo2')
      fuera = sv[(sv['Categoría PA'].isin(['Baja (<90/60)', 'Elevada nivel 2 (≥140/90)']))
                 | (sv['spo2'] < umbral_spo2) | (sv['temp'] >= 37.8)]
      st.markdown(f'**Registros fuera de rango para revisión clínica: {len(fuera)}**')
      if len(fuera):
        vista = fuera[['fecha_hora', 'id_legajo', 'apellido_nombre', 'curso', 'presion',
                       'saturacion', 'temperatura', 'Categoría PA']].rename(columns={
            'fecha_hora': 'Fecha/Hora', 'id_legajo': 'Legajo', 'apellido_nombre': 'Cadete',
            'curso': 'Curso', 'presion': 'PA', 'saturacion': 'SpO₂', 'temperatura': 'Temp.'})
        st.dataframe(vista, use_container_width=True, hide_index=True)
        tablas_export['signos_vitales_fuera_rango'] = vista

  # === REPOSOS Y ALTAS =========================================================
  with t3:
    if rep_f is None or rep_f.empty:
      _vacio()
    else:
      st.markdown('**Duración de reposos por tipo**')
      por_tipo = rep_f.groupby('tipo_reposo')['dias_reposo'].agg(
          Expedientes='count', Dias_totales='sum', Media='mean', Mediana='median',
          P90=lambda s: s.quantile(0.9)).round(1).reset_index().rename(
          columns={'tipo_reposo': 'Tipo', 'Dias_totales': 'Días totales'})
      st.dataframe(por_tipo, use_container_width=True, hide_index=True)
      tablas_export['reposos_por_tipo'] = por_tipo

      mensual = rep_f.assign(Mes=rep_f['desde'].dt.to_period('M').astype(str)).groupby(
          ['Mes', 'curso'])['dias_en_periodo'].sum().rename('Días').reset_index()
      st.markdown('**Días de reposo por mes y curso**')
      st.altair_chart(alt.Chart(mensual).mark_bar().encode(
          x=alt.X('Mes:N', title=None), y=alt.Y('Días:Q', title=None), color='curso:N',
          tooltip=['Mes', 'curso', 'Días']).properties(height=230), use_container_width=True)

      umbral = st.slider('Cadetes con reposo acumulado de al menos (días)', 5, 60, 15, key='an_dias')
      acum = rep_f.groupby(['id_legajo', 'apellido_nombre', 'curso'])['dias_en_periodo'].sum().reset_index(
          name='Días acumulados')
      acum = acum[acum['Días acumulados'] >= umbral].sort_values('Días acumulados', ascending=False)
      st.markdown(f'**{len(acum)} cadetes con ≥ {umbral} días de reposo en el período**')
      st.dataframe(acum, use_container_width=True, hide_index=True)
      tablas_export['reposo_acumulado_alto'] = acum

    if not notas.empty and 'fecha_alta_efectiva' in notas.columns:
      alta = notas[notas['estado_alta'] == 'Alta Convalidada'].copy()
      alta['alta'] = pd.to_datetime(alta['fecha_alta_efectiva'], errors='coerce')
      alta = alta.dropna(subset=['alta', 'hasta'])
      if len(alta):
        alta['Demora (días)'] = (alta['alta'] - alta['hasta']).dt.days
        st.markdown('**Demora de convalidación** (alta efectiva − fin de reposo)')
        m1, m2, m3 = st.columns(3)
        m1.metric('Altas con fecha registrada', len(alta))
        m2.metric('Demora promedio (días)', f'{alta["Demora (días)"].mean():.1f}')
        m3.metric('Convalidadas con retraso', int((alta['Demora (días)'] > 0).sum()))

  # === CONCENTRACIÓN ===========================================================
  with t4:
    if n_int == 0:
      _vacio()
    else:
      cnt = int_f.groupby(['id_legajo', 'apellido_nombre', 'curso']).size().rename('Atenciones').reset_index()
      cnt = cnt.sort_values('Atenciones', ascending=False).reset_index(drop=True)
      top_n = max(1, int(round(len(cad_f) * 0.10)))
      share = 100 * cnt['Atenciones'].head(top_n).sum() / cnt['Atenciones'].sum()
      st.markdown(f'**El 10% de la compañía ({top_n} cadetes) concentra el {share:.0f}% de las atenciones del período.**')
      st.dataframe(cnt.head(15), use_container_width=True, hide_index=True)
      tablas_export['concentracion_atenciones'] = cnt.head(50)

      reinc = inter[(inter['fecha'] >= pd.Timestamp(hoy) - pd.Timedelta(days=30))
                    & (inter['curso'].isin(sel_cursos))]
      reinc = reinc.groupby(['id_legajo', 'apellido_nombre', 'curso']).size().rename('Atenciones 30 días').reset_index()
      reinc = reinc[reinc['Atenciones 30 días'] >= 3].sort_values('Atenciones 30 días', ascending=False)
      st.markdown(f'**Reincidencia: {len(reinc)} cadetes con 3 o más atenciones en los últimos 30 días**')
      if len(reinc):
        st.dataframe(reinc, use_container_width=True, hide_index=True)
        tablas_export['reincidencia_30d'] = reinc

  # === CALIDAD DE DATOS ========================================================
  with t5:
    controles = []

    def _chk(nombre, df_mal, severidad):
      controles.append({'Control': nombre, 'Casos': len(df_mal), 'Severidad': severidad})
      if len(df_mal):
        with st.expander(f'{nombre} ({len(df_mal)})'):
          st.dataframe(df_mal, use_container_width=True, hide_index=True)

    dni = cad['dni'].astype(str).str.strip()
    _chk('Cadetes sin DNI', cad[dni.isin(['', 'nan', 'None'])][['id_legajo', 'apellido_nombre', 'curso']], 'Media')
    dup = cad[dni.duplicated(keep=False) & ~dni.isin(['', 'nan', 'None'])].sort_values('dni')
    _chk('DNI duplicados', dup[['id_legajo', 'apellido_nombre', 'dni']], 'Alta')
    if not notas.empty:
      _chk('Reposos sin fecha de fin válida', notas[notas['hasta'].isna()][['nro_expediente', 'id_legajo', 'apellido_nombre']], 'Alta')
      _chk('Reposos con fin anterior al inicio', notas[notas['hasta'] < notas['desde']][['nro_expediente', 'id_legajo', 'apellido_nombre']], 'Alta')
      d_exp = notas[notas['nro_expediente'].duplicated(keep=False)].sort_values('nro_expediente')
      _chk('Números de expediente repetidos', d_exp[['nro_expediente', 'id_legajo', 'apellido_nombre']], 'Media')
      _chk('Expedientes sin cadete en el padrón', notas[notas['apellido_nombre'].isna()][['nro_expediente', 'id_legajo']], 'Alta')
    if not inter.empty:
      _chk('Intervenciones sin cadete en el padrón', inter[inter['apellido_nombre'].isna()][['id', 'id_legajo', 'fecha_hora']], 'Alta')
      sin_pa = inter[inter['presion'].map(lambda v: _parse_pa(v)[0] is None)]
      _chk('Intervenciones sin presión arterial interpretable', sin_pa[['id', 'id_legajo', 'fecha_hora', 'presion']], 'Baja')
      _chk('Intervenciones con fecha ilegible', inter[inter['fecha'].isna()][['id', 'id_legajo', 'fecha_hora']], 'Media')
    resumen = pd.DataFrame(controles)
    if not resumen.empty:
      st.dataframe(resumen, use_container_width=True, hide_index=True)
      tablas_export['calidad_de_datos'] = resumen
      if resumen['Casos'].sum() == 0:
        st.success('Sin inconsistencias detectadas.')

  # --- Exportación del paquete de indicadores -----------------------------------
  if tablas_export:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
      for nombre, df in tablas_export.items():
        z.writestr(f'{nombre}.csv', df.to_csv(index=False).encode('utf-8-sig'))
    st.download_button(
        '⬇️ Descargar indicadores del período (ZIP de CSV)', buf.getvalue(),
        file_name=f'indicadores_{ini}_{fin}.zip', mime='application/zip', key='an_zip',
        on_click=sec.registrar_auditoria,
        args=('Informes', 'EXPORT', f'Descarga de indicadores analíticos {ini} a {fin} ({len(tablas_export)} tablas)'))
