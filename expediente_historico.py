"""Carga rápida de expedientes históricos: formulario inicial → prórrogas → alta,
cada movimiento con sus PDF (formulario, certificado, estudios). Todo se arma en un
lote en memoria y se guarda de una sola vez (transacción atómica)."""
from datetime import timedelta
import html

import pandas as pd
import streamlit as st

import db
import seguridad as sec

TIPOS_REPOSO = ['ART', 'Reposo Domiciliario', 'Reposo Académico', 'Internación']
MOV = {'inicial': '📝 Formulario inicial', 'prorroga': '➕ Prórroga / más días', 'alta': '✅ Alta'}


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
def asegurar_columnas():
    """Columnas que la app vieja agregaba con ALTER al vuelo + PDF dentro de la base."""
    for t, c, tipo in [('notas_medicas', 'examen_pendiente', 'TEXT'),
                       ('notas_medicas', 'expediente_vinculado', 'TEXT'),
                       ('legajo_documentos', 'contenido', 'BYTEA')]:
        conn = db.conectar(sec.DB_NAME)
        try:
            conn.execute(f'ALTER TABLE {t} ADD COLUMN {c} {tipo}')
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()


def _notas_db(id_leg):
    conn = db.conectar(sec.DB_NAME)
    df = pd.read_sql_query(
        'SELECT id, nro_expediente, tipo_reposo, fecha_desde, fecha_hasta, estado_alta, medico, diagnostico'
        ' FROM notas_medicas WHERE id_legajo = ? ORDER BY fecha_desde, id', conn, params=(id_leg,))
    conn.close()
    return df


def _dias(d, h):
    return (h - d).days + 1 if d and h else 0


def _lote(id_leg):
    k = f'hist_{id_leg}'
    if k not in st.session_state:
        st.session_state[k] = []  # lista de episodios
    return st.session_state[k]


def _episodio_abierto(lote):
    return lote[-1] if lote and not lote[-1]['cerrado'] else None


def _ultimo_hasta(ep):
    movs = [m for m in ep['movs'] if m['tipo'] != 'alta']
    if movs:
        return movs[-1]['hasta']
    return ep['base']['hasta'] if ep['base'] else None


# ---------------------------------------------------------------------------
# Guardado atómico
# ---------------------------------------------------------------------------
def _guardar_lote(id_leg, lote):
    asegurar_columnas()
    n_notas = n_docs = 0
    with db.transaccion(sec.DB_NAME) as cur:
        for ep in lote:
            prev_id = ep['base']['id'] if ep['base'] else None
            prev_exp = ep['base']['exp'] if ep['base'] else None
            for m in ep['movs']:
                if m['tipo'] in ('inicial', 'prorroga'):
                    if prev_id:
                        cur.execute("UPDATE notas_medicas SET estado_alta = 'Prórroga Otorgada' WHERE id = ?", (prev_id,))
                    diag = m['diag'] if m['tipo'] == 'inicial' else f"Prórroga de exp. {prev_exp}. Motivo: {m['diag']}"
                    cur.execute(
                        'INSERT INTO notas_medicas (id_legajo, nro_expediente, medico, diagnostico, tipo_reposo,'
                        ' fecha_desde, fecha_hasta, medicamentos, certificados_indicaciones, analisis_estudios,'
                        " estado_alta, expediente_vinculado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente', ?)"
                        ' RETURNING id',
                        (id_leg, m['exp'], m['medico'], diag, m['tipo_reposo'], m['desde'].isoformat(),
                         m['hasta'].isoformat(), m['medicamentos'], m['indicaciones'], m['estudios'],
                         f'Vinculado a {prev_exp}' if m['tipo'] == 'prorroga' else None))
                    prev_id, prev_exp = cur.fetchone()[0], m['exp']
                    n_notas += 1
                else:  # alta
                    obs = f"Exp. Alta: {m['exp']} | {m['obs']}"
                    if m['examen']:
                        obs += f" | ⚠️ Examen Complementario PENDIENTE: {m['examen']}"
                    cur.execute(
                        "UPDATE notas_medicas SET estado_alta = 'Alta Convalidada', fecha_alta_efectiva = ?,"
                        ' medico_alta = ?, observaciones_alta = ?, examen_pendiente = ? WHERE id = ?',
                        (m['fecha'].isoformat(), m['medico'], obs, m['examen'] or None, prev_id))
                for nombre, datos in m['pdfs']:
                    cur.execute(
                        'INSERT INTO legajo_documentos (id_legajo, titulo_documento, tipo_documento, fecha_subida,'
                        ' archivo_nombre, observaciones, contenido) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (id_leg, f"Expediente {m['exp']} · {MOV[m['tipo']][2:]} · {nombre}",
                         'PDF Alta' if m['tipo'] == 'alta' else 'PDF Histórico', m['fecha'].isoformat(),
                         sec.nombre_seguro(nombre), 'Carga histórica', datos))
                    n_docs += 1
    return n_notas, n_docs


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def _form_movimiento(id_leg, lote, df_db):
    ep = _episodio_abierto(lote)
    pendientes = df_db[df_db['estado_alta'] == 'Pendiente']
    tipo = st.radio('Tipo de formulario', list(MOV), format_func=MOV.get, horizontal=True, key=f'hist_tipo_{id_leg}')

    base = None
    if tipo != 'inicial' and ep is None:
        if pendientes.empty:
            st.info('Primero cargá el **formulario inicial** del expediente (no hay expedientes abiertos).')
            return
        op = (pendientes['id'].astype(str) + ' · Exp. ' + pendientes['nro_expediente'].astype(str)
              + ' · hasta ' + pendientes['fecha_hasta'].astype(str)).tolist()
        sel = st.selectbox('Continuar expediente ya registrado', op, key=f'hist_base_{id_leg}')
        r = pendientes[pendientes['id'].astype(str) == sel.split(' · ')[0]].iloc[0]
        base = {'id': int(r['id']), 'exp': str(r['nro_expediente']), 'tipo_reposo': r['tipo_reposo'],
                'hasta': pd.to_datetime(r['fecha_hasta'], errors='coerce').date() if r['fecha_hasta'] else None,
                'diag': r['diagnostico']}
    if tipo == 'inicial' and ep is not None:
        st.caption('ℹ️ Hay un episodio abierto sin alta: un nuevo formulario inicial abre otro episodio aparte.')

    ref = ep or ({'base': base, 'movs': []} if base else None)
    ult_hasta = _ultimo_hasta(ref) if ref else None
    ini = (ref['movs'][0] if ref and ref['movs'] else (ref['base'] if ref else None)) or {}
    hoy = sec.ahora_local().date()
    n_form = st.session_state.setdefault(f'hist_n_{id_leg}', 0)  # clave nueva = formulario limpio

    with st.form(f'hist_form_{id_leg}_{tipo}_{n_form}'):
        c1, c2 = st.columns([1, 1.4])
        exp = c1.text_input('N° de expediente / formulario *', placeholder='Ej: EXP-2026-0123')
        medico = c2.text_input('Médico que convalida / Matrícula *', placeholder='Ej: Dr. Gómez · MP-4521')
        fecha = None

        datos = {}
        if tipo == 'alta':
            fecha = st.date_input('Fecha efectiva de alta *', format='DD/MM/YYYY',
                                  value=(ult_hasta + timedelta(days=1)) if ult_hasta else hoy)
            datos['obs'] = st.text_area('Observaciones de alta / aptitud', height=80,
                                        placeholder='Recuperado, apto para retomar actividades.')
            e1, e2 = st.columns([1, 3])
            pide = e1.checkbox('Pide examen complementario')
            datos['examen'] = e2.text_input('Detalle del examen', placeholder='Ej: Placa de tórax de control')
        else:
            datos['diag'] = st.text_input('Diagnóstico *', value=ini.get('diag', '') if tipo == 'prorroga' else '')
            d1, d2, d3, d4 = st.columns([1.3, 1, 1, .7])
            tr_def = ini.get('tipo_reposo') if ini.get('tipo_reposo') in TIPOS_REPOSO else 'ART'
            datos['tipo_reposo'] = d1.selectbox('Tipo de reposo', TIPOS_REPOSO, index=TIPOS_REPOSO.index(tr_def))
            desde_def = ult_hasta + timedelta(days=1) if (ult_hasta and tipo == 'prorroga') else hoy
            datos['desde'] = d2.date_input('Reposo desde *', value=desde_def, format='DD/MM/YYYY')
            datos['n_dias'] = d4.number_input('Días', min_value=1, max_value=365, value=7, step=1)
            datos['hasta'] = d3.date_input('Reposo hasta', value=None, format='DD/MM/YYYY',
                                           help='Vacío = se calcula con "Días".')
            with st.expander('Medicación, indicaciones y estudios (opcional)'):
                datos['medicamentos'] = st.text_input('Medicamentos')
                datos['indicaciones'] = st.text_area('Indicaciones / certificado', height=70)
                datos['estudios'] = st.text_area('Estudios complementarios', height=70)

        pdfs = st.file_uploader('📎 Formulario, certificado y estudios (PDF · podés seleccionar varios)',
                                type=['pdf'], accept_multiple_files=True)
        enviar = st.form_submit_button('➕ Agregar al expediente', type='primary', use_container_width=True)

    if not enviar:
        return
    exp, medico = exp.strip(), medico.strip()
    usados = set(df_db['nro_expediente'].astype(str)) | {m['exp'] for e in lote for m in e['movs'] if m['tipo'] != 'alta'}
    errores = []
    if not exp or not medico:
        errores.append('Completá N° de expediente y médico.')
    if tipo != 'alta':
        if not datos['diag'].strip():
            errores.append('Completá el diagnóstico.')
        if not datos['hasta']:
            datos['hasta'] = datos['desde'] + timedelta(days=int(datos['n_dias']) - 1)
        if datos['hasta'] < datos['desde']:
            errores.append('"Hasta" es anterior a "Desde".')
        if exp in usados:
            errores.append(f'El expediente {exp} ya está cargado.')
        if tipo == 'prorroga' and ult_hasta and datos['desde'] <= ult_hasta:
            st.session_state['hist_aviso'] = (f'⚠️ La prórroga {exp} empieza antes de que termine el reposo anterior'
                                              f' ({ult_hasta:%d/%m/%Y}). Revisá las fechas.')
    elif tipo == 'alta' and datos.get('examen') and not pide:
        datos['examen'] = ''
    archivos = []
    for f in pdfs or []:
        if sec.validar_pdf(f) is None:
            errores.append(f'PDF no válido o demasiado grande: {f.name}')
        else:
            archivos.append((f.name, bytes(f.getbuffer())))
    if errores:
        for e in errores:
            st.error(e)
        return

    mov = {'tipo': tipo, 'exp': exp, 'medico': medico, 'fecha': fecha or datos['desde'], 'pdfs': archivos,
           'diag': datos.get('diag', '').strip(), 'tipo_reposo': datos.get('tipo_reposo'),
           'desde': datos.get('desde'), 'hasta': datos.get('hasta'),
           'medicamentos': datos.get('medicamentos', ''), 'indicaciones': datos.get('indicaciones', ''),
           'estudios': datos.get('estudios', ''), 'obs': datos.get('obs', ''), 'examen': datos.get('examen', '')}
    if tipo == 'inicial' or (ep is None):
        lote.append({'base': None if tipo == 'inicial' else base, 'movs': [mov], 'cerrado': tipo == 'alta'})
    else:
        ep['movs'].append(mov)
        ep['cerrado'] = tipo == 'alta'
    st.session_state[f'hist_n_{id_leg}'] = n_form + 1
    st.rerun()


def _vista_lote(id_leg, lote):
    if not lote:
        st.markdown('<div class="panel" style="text-align:center;opacity:.75">El expediente está vacío. '
                    'Agregá el primer formulario arriba.</div>', unsafe_allow_html=True)
        return
    dias = sum(_dias(m['desde'], m['hasta']) for e in lote for m in e['movs'] if m['tipo'] != 'alta')
    n_mov = sum(len(e['movs']) for e in lote)
    n_pdf = sum(len(m['pdfs']) for e in lote for m in e['movs'])
    k = st.columns(4)
    k[0].metric('Formularios', n_mov)
    k[1].metric('Días de reposo', dias)
    k[2].metric('PDF anexados', n_pdf)
    k[3].metric('Estado', 'Con alta' if lote[-1]['cerrado'] else 'Abierto')

    for i, ep in enumerate(lote, 1):
        st.markdown(f'##### Episodio {i}' + (f" · continúa Exp. {html.escape(ep['base']['exp'])}" if ep['base'] else ''))
        filas = []
        for m in ep['movs']:
            if m['tipo'] == 'alta':
                det = f"Alta el {m['fecha']:%d/%m/%Y}" + (f" · 🔬 {m['examen']}" if m['examen'] else '')
            else:
                det = f"{m['desde']:%d/%m/%Y} → {m['hasta']:%d/%m/%Y} ({_dias(m['desde'], m['hasta'])} días) · {m['tipo_reposo']}"
            filas.append({'Formulario': MOV[m['tipo']], 'Expediente': m['exp'], 'Detalle': det,
                          'Médico': m['medico'], 'PDF': '📎 ' + str(len(m['pdfs'])) if m['pdfs'] else '—'})
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    b1, b2, b3 = st.columns([1, 1, 2])
    if b1.button('↩️ Quitar último', key=f'hist_undo_{id_leg}', use_container_width=True):
        ep = lote[-1]
        ep['movs'].pop()
        ep['cerrado'] = False
        if not ep['movs']:
            lote.pop()
        st.rerun()
    if b2.button('🗑️ Vaciar', key=f'hist_clear_{id_leg}', use_container_width=True):
        lote.clear()
        st.rerun()
    if b3.button(f'💾 Guardar todo ({n_mov} formularios · {n_pdf} PDF)', type='primary',
                 key=f'hist_save_{id_leg}', use_container_width=True) and sec.exigir('notas_medicas'):
        try:
            n_notas, n_docs = _guardar_lote(id_leg, lote)
        except Exception as e:
            st.error(f'No se guardó nada (se revirtió todo): {e}')
            return
        sec.registrar_auditoria('Notas Médicas', 'CARGA_HISTORICA',
                                f'{n_mov} formularios / {n_notas} notas / {n_docs} PDF', id_leg)
        lote.clear()
        st.session_state['hist_ok'] = f'✅ Expediente guardado: {n_mov} formularios y {n_docs} PDF.'
        st.rerun()


def render_tab(df_cad):
    if msg := st.session_state.pop('hist_ok', None):
        st.success(msg)
    if msg := st.session_state.pop('hist_aviso', None):
        st.warning(msg)
    lista = (df_cad['id_legajo'].astype(str) + ' - ' + df_cad['apellido_nombre']).tolist()
    sel = st.selectbox('Cadete', lista, key='hist_cadete')
    id_leg = sel.split(' - ')[0]
    df_db = _notas_db(id_leg)
    lote = _lote(id_leg)

    if not df_db.empty:
        with st.expander(f'📂 Ya registrado en el sistema ({len(df_db)} nota/s) — para no duplicar'):
            v = df_db[['nro_expediente', 'tipo_reposo', 'fecha_desde', 'fecha_hasta', 'estado_alta', 'medico']]
            st.dataframe(v.rename(columns={'nro_expediente': 'Expediente', 'tipo_reposo': 'Tipo', 'fecha_desde': 'Desde',
                                           'fecha_hasta': 'Hasta', 'estado_alta': 'Estado', 'medico': 'Médico'}),
                         use_container_width=True, hide_index=True)

    st.markdown('#### 1 · Cargá cada formulario en orden')
    _form_movimiento(id_leg, lote, df_db)
    st.markdown('#### 2 · Revisá y guardá todo junto')
    _vista_lote(id_leg, lote)
