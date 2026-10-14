"""Carga masiva: todas las notas médicas / ART de un cadete en una sola grilla,
importación por Excel para varios cadetes y restauración del padrón."""
import io

import pandas as pd
import streamlit as st

import db
import expediente_historico
import seguridad as sec

TIPOS = ['ART', 'Reposo Domiciliario', 'Reposo Académico', 'Internación']
ESTADOS = ['Pendiente', 'Alta Convalidada', 'Prórroga Otorgada']
COLS = {  # columna de la grilla → columna de notas_medicas
    'Expediente': 'nro_expediente', 'Médico / Matrícula': 'medico', 'Diagnóstico': 'diagnostico',
    'Tipo': 'tipo_reposo', 'Desde': 'fecha_desde', 'Hasta': 'fecha_hasta',
    'Medicamentos': 'medicamentos', 'Indicaciones': 'certificados_indicaciones',
    'Estudios': 'analisis_estudios', 'Estado': 'estado_alta', 'Fecha Alta': 'fecha_alta_efectiva',
}
OBLIG = ['Expediente', 'Médico / Matrícula', 'Diagnóstico', 'Desde', 'Hasta']
SQL_INS = (f"INSERT INTO notas_medicas (id_legajo, {', '.join(COLS.values())}) "
           f"VALUES (?, {', '.join('?' * len(COLS))})")


def _grilla_vacia(n=6):
    return pd.DataFrame({
        'Expediente': [''] * n, 'Médico / Matrícula': [''] * n, 'Diagnóstico': [''] * n,
        'Tipo': ['ART'] * n, 'Desde': pd.to_datetime([None] * n), 'Hasta': pd.to_datetime([None] * n),
        'Medicamentos': [''] * n, 'Indicaciones': [''] * n, 'Estudios': [''] * n,
        'Estado': ['Pendiente'] * n, 'Fecha Alta': pd.to_datetime([None] * n),
    })


def _fecha(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)) or str(v).strip() == '':
        return None
    if hasattr(v, 'isoformat'):
        return (v.date() if hasattr(v, 'date') and callable(v.date) else v).isoformat()
    s = str(v).strip()[:10]
    iso = len(s) == 10 and s[4] == '-'  # 2026-09-01 (ISO) vs 01/09/2026 (AR)
    d = pd.to_datetime(s, errors='coerce', dayfirst=not iso, format='%Y-%m-%d' if iso else None)
    return None if pd.isna(d) else d.date().isoformat()


def _validar(df, existentes):
    """Devuelve (filas_ok, errores) descartando filas totalmente vacías."""
    df = df.copy()
    df = df[~df[OBLIG].apply(lambda r: all(pd.isna(x) or str(x).strip() == '' for x in r), axis=1)]
    ok, errores, vistos = [], [], set()
    for i, r in df.reset_index(drop=True).iterrows():
        n = i + 1
        faltan = [c for c in OBLIG if pd.isna(r[c]) or str(r[c]).strip() == '']
        if faltan:
            errores.append(f'Fila {n}: falta {", ".join(faltan)}'); continue
        d, h = _fecha(r['Desde']), _fecha(r['Hasta'])
        if not d or not h:
            errores.append(f'Fila {n}: fecha inválida'); continue
        if h < d:
            errores.append(f'Fila {n}: "Hasta" es anterior a "Desde"'); continue
        exp = str(r['Expediente']).strip()
        if exp in existentes or exp in vistos:
            errores.append(f'Fila {n}: expediente {exp} ya cargado (se omite)'); continue
        vistos.add(exp)
        fila = {k: ('' if pd.isna(r.get(k)) else str(r.get(k)).strip()) for k in COLS}
        fila.update({'Expediente': exp, 'Desde': d, 'Hasta': h, 'Fecha Alta': _fecha(r.get('Fecha Alta')),
                     'Tipo': fila['Tipo'] or 'ART', 'Estado': fila['Estado'] or 'Pendiente'})
        ok.append(fila)
    return ok, errores


def _expedientes(id_legajo=None):
    conn = db.conectar(sec.DB_NAME)
    q, p = 'SELECT id_legajo, nro_expediente FROM notas_medicas', None
    if id_legajo:
        q, p = q + ' WHERE id_legajo = ?', (id_legajo,)
    df = pd.read_sql_query(q, conn, params=p)
    conn.close()
    return df


def _guardar(filas_por_legajo):
    total = 0
    with db.transaccion(sec.DB_NAME) as cur:
        for id_leg, filas in filas_por_legajo.items():
            cur.executemany(SQL_INS, [(id_leg, *[f[k] for k in COLS]) for f in filas])
            total += len(filas)
    return total


# ---------------------------------------------------------------------------
def _tab_por_cadete(df_cad):
    lista = (df_cad['id_legajo'].astype(str) + ' - ' + df_cad['apellido_nombre']).tolist()
    sel = st.selectbox('Cadete', lista, key='cm_cadete')
    id_leg = sel.split(' - ')[0]
    previas = _expedientes(id_leg)
    st.caption(f'{len(previas)} nota(s) ya registradas para este cadete. '
               'Agregá una fila por certificado; las filas vacías se ignoran.')

    clave = f'cm_grid_{id_leg}'
    if clave not in st.session_state:
        st.session_state[clave] = _grilla_vacia()
    editado = st.data_editor(
        st.session_state[clave], key=f'{clave}_ed', num_rows='dynamic',
        use_container_width=True, hide_index=True,
        column_config={
            'Expediente': st.column_config.TextColumn(required=True, width='small'),
            'Médico / Matrícula': st.column_config.TextColumn(required=True),
            'Diagnóstico': st.column_config.TextColumn(required=True, width='large'),
            'Tipo': st.column_config.SelectboxColumn(options=TIPOS, default='ART', width='small'),
            'Desde': st.column_config.DateColumn(format='DD/MM/YYYY', required=True),
            'Hasta': st.column_config.DateColumn(format='DD/MM/YYYY', required=True),
            'Estado': st.column_config.SelectboxColumn(options=ESTADOS, default='Pendiente'),
            'Fecha Alta': st.column_config.DateColumn(format='DD/MM/YYYY'),
        },
    )
    ok, errores = _validar(editado, set(previas['nro_expediente'].astype(str)))
    c1, c2 = st.columns([1, 3])
    c1.metric('Listas para guardar', len(ok))
    if errores:
        with c2.expander(f'⚠️ {len(errores)} observación(es)', expanded=True):
            st.markdown('\n'.join(f'- {e}' for e in errores))
    if st.button(f'💾 Guardar {len(ok)} nota(s) de una vez', type='primary',
                 disabled=not ok, key='cm_guardar') and sec.exigir('notas_medicas'):
        n = _guardar({id_leg: ok})
        sec.registrar_auditoria('Notas Médicas', 'INSERT_MASIVO', f'{n} notas cargadas en bloque', id_leg)
        for k in (clave, f'{clave}_ed'):
            st.session_state.pop(k, None)
        st.success(f'✅ {n} nota(s) guardadas para el legajo {id_leg}.')
        st.rerun()


def _plantilla():
    df = pd.DataFrame(columns=['Legajo', *COLS])
    df.loc[0] = ['20505', 'ART-2026-001', 'Dr. Pérez / MP-1234', 'Esguince tobillo', 'ART',
                 '01/09/2026', '15/09/2026', '', '', '', 'Pendiente', '']
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name='Notas')
    return buf.getvalue()


def _tab_excel(df_cad):
    st.download_button('⬇️ Descargar plantilla Excel', _plantilla(),
                       'plantilla_notas_medicas.xlsx', key='cm_tpl')
    arch = st.file_uploader('Subir planilla completada (.xlsx)', type=['xlsx'], key='cm_xlsx')
    if not arch:
        return
    df = pd.read_excel(arch, dtype=str).fillna('')
    falt = [c for c in ['Legajo', *OBLIG] if c not in df.columns]
    if falt:
        st.error(f'Faltan columnas: {", ".join(falt)}'); return
    for c in COLS:
        df[c] = df.get(c, '')
    validos = set(df_cad['id_legajo'].astype(str))
    previas = _expedientes()
    plan, errores = {}, []
    for leg, grupo in df.groupby(df['Legajo'].str.strip()):
        if leg not in validos:
            errores.append(f'Legajo {leg}: no existe en el padrón ({len(grupo)} fila/s omitidas)'); continue
        ya = set(previas.loc[previas['id_legajo'].astype(str) == leg, 'nro_expediente'].astype(str))
        ok, err = _validar(grupo, ya)
        errores += [f'Legajo {leg} · {e}' for e in err]
        if ok:
            plan[leg] = ok
    n = sum(map(len, plan.values()))
    k = st.columns(3)
    k[0].metric('Cadetes', len(plan)); k[1].metric('Notas válidas', n); k[2].metric('Observaciones', len(errores))
    if errores:
        with st.expander('Ver observaciones'):
            st.markdown('\n'.join(f'- {e}' for e in errores))
    if st.button(f'💾 Importar {n} nota(s)', type='primary', disabled=not n,
                 key='cm_imp') and sec.exigir('notas_medicas'):
        total = _guardar(plan)
        sec.registrar_auditoria('Notas Médicas', 'IMPORT_EXCEL', f'{total} notas / {len(plan)} cadetes')
        st.success(f'✅ {total} notas importadas.')


def _tab_padron(excel_path):
    st.caption('Restaura/actualiza la tabla de cadetes desde el listado oficial (no borra notas).')
    arch = st.file_uploader('Listado de cadetes (.xlsx)', type=['xlsx'], key='cm_padron')
    fuente = arch or excel_path
    try:
        df = pd.read_excel(fuente, dtype=str)
    except Exception:
        st.info('Subí el listado de cadetes.'); return
    df.columns = [str(c).strip().upper() for c in df.columns]
    col_leg = st.radio('Columna usada como N° de legajo', ['CARGO', 'DNI'], horizontal=True, key='cm_col')
    filas = [(
        str(r[col_leg]).strip(), f"{str(r['APELLIDO']).strip()} {str(r['NOMBRES']).strip()}",
        str(r.get('CURSO', '')).strip(), str(r.get('DNI', '')).strip(),
        _fecha(r.get('FECHA DE NACIMIENTO')),
    ) for _, r in df.dropna(subset=['APELLIDO']).iterrows()]
    prev = pd.DataFrame(filas, columns=['Legajo', 'Apellido y nombre', 'Curso', 'DNI', 'Nacimiento'])
    dup = prev[prev['Legajo'].duplicated(keep=False)]
    if not dup.empty:
        st.error(f'⛔ {col_leg} repetido en el listado: corregí el Excel antes de sincronizar '
                 '(si no, el segundo cadete pisa al primero).')
        st.dataframe(dup, use_container_width=True, hide_index=True)
    st.dataframe(prev, use_container_width=True, hide_index=True, height=260)
    if st.button(f'🔄 Sincronizar {len(filas)} cadetes', type='primary', disabled=not dup.empty,
                 key='cm_sync') and sec.exigir('sincronizar_excel'):
        with db.transaccion(sec.DB_NAME) as cur:
            cur.executemany(
                'INSERT INTO cadetes (id_legajo, apellido_nombre, curso, dni, fecha_nacimiento) VALUES (?, ?, ?, ?, ?) '
                'ON CONFLICT (id_legajo) DO UPDATE SET apellido_nombre = excluded.apellido_nombre, '
                'curso = excluded.curso, dni = excluded.dni, fecha_nacimiento = excluded.fecha_nacimiento',
                filas)
        sec.registrar_auditoria('Legajos', 'SYNC_EXCEL', f'{len(filas)} cadetes sincronizados')
        st.success('✅ Padrón actualizado.')


def render(obtener_cadetes, excel_path):
    st.markdown('<div class="pro-header"><p class="pro-title">⚡ Carga Masiva de Notas Médicas / ART</p>'
                '<p class="pro-subtitle">Formularios, prórrogas y altas ya ocurridos, con sus PDF, en una sola carga.</p>'
                '</div>', unsafe_allow_html=True)
    df_cad = obtener_cadetes()
    t0, t1, t2, t3 = st.tabs(['📚 Expediente por formularios', '🧑 Grilla rápida', '📄 Importar Excel',
                              '👥 Padrón de cadetes'])
    with t3:
        _tab_padron(excel_path)
    if df_cad.empty:
        for t in (t0, t1, t2):
            t.warning('Primero cargá el padrón de cadetes (pestaña 👥).')
        return
    with t0:
        expediente_historico.render_tab(df_cad)
    with t1:
        _tab_por_cadete(df_cad)
    with t2:
        _tab_excel(df_cad)
