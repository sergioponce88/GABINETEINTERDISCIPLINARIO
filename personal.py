"""Personal del Gabinete: alta, modificación y baja del staff médico."""
import html

import pandas as pd
import streamlit as st

import db
import seguridad as sec

ESPECIALIDADES = ['Medicina General / Clínica', 'Traumatología', 'Psicología', 'Psiquiatría', 'Enfermería',
                  'Kinesiología', 'Nutrición', 'Odontología', 'Cardiología', 'Trabajo Social', 'Otra']
COLS = {'id_legajo_personal': 'Legajo', 'apellido_nombre': 'Apellido y nombre', 'dni': 'DNI',
        'matricula': 'Matrícula', 'especialidad': 'Especialidad', 'telefono': 'Teléfono'}


def _cargar():
    conn = db.conectar(sec.DB_NAME)
    df = pd.read_sql_query('SELECT * FROM personal_gabinete ORDER BY apellido_nombre', conn)
    conn.close()
    return df


def _campos(prefijo, r=None):
    """Campos del formulario; devuelve un dict con los valores."""
    r = r if r is not None else {}
    c1, c2 = st.columns([1, 2])
    v = {'id_legajo_personal': c1.text_input('N° de legajo *', value=r.get('id_legajo_personal') or '', key=f'{prefijo}_leg'),
         'apellido_nombre': c2.text_input('Apellido y nombre *', value=r.get('apellido_nombre') or '',
                                          placeholder='Ej: GÓMEZ, Juan Carlos', key=f'{prefijo}_nom')}
    c3, c4, c5 = st.columns(3)
    v['dni'] = c3.text_input('DNI', value=r.get('dni') or '', key=f'{prefijo}_dni')
    v['matricula'] = c4.text_input('Matrícula', value=r.get('matricula') or '', placeholder='Ej: MP-4521', key=f'{prefijo}_mat')
    v['telefono'] = c5.text_input('Teléfono', value=r.get('telefono') or '', key=f'{prefijo}_tel')
    actual = r.get('especialidad') or ESPECIALIDADES[0]
    idx = ESPECIALIDADES.index(actual) if actual in ESPECIALIDADES else ESPECIALIDADES.index('Otra')
    c6, c7 = st.columns(2)
    esp = c6.selectbox('Especialidad', ESPECIALIDADES, index=idx, key=f'{prefijo}_esp')
    otra = c7.text_input('Si es "Otra", ¿cuál?', value='' if actual in ESPECIALIDADES else actual, key=f'{prefijo}_otra')
    v['especialidad'] = otra.strip() if esp == 'Otra' and otra.strip() else esp
    return {k: str(x).strip() for k, x in v.items()}


def _validar(v):
    if not v['id_legajo_personal'] or not v['apellido_nombre']:
        st.error('Completá N° de legajo y apellido y nombre.')
        return False
    if v['dni'] and not v['dni'].replace('.', '').isdigit():
        st.error('El DNI debe tener solo números.')
        return False
    return True


def render():
    st.markdown('<div class="pro-header"><p class="pro-title">🧑‍⚕️ Personal del Gabinete</p>'
                '<p class="pro-subtitle">Staff médico y profesionales que intervienen en los legajos.</p></div>',
                unsafe_allow_html=True)
    if msg := st.session_state.pop('pers_ok', None):
        st.success(msg)
    df = _cargar()
    puede = sec.tiene_permiso('gestionar_personal')

    k = st.columns(3)
    k[0].metric('Profesionales', len(df))
    k[1].metric('Especialidades', df['especialidad'].replace('', pd.NA).nunique() if not df.empty else 0)
    k[2].metric('Con matrícula', int((df['matricula'].fillna('') != '').sum()) if not df.empty else 0)

    busca = st.text_input('🔍 Buscar por nombre, legajo, DNI o especialidad', key='pers_busca')
    vista = df
    if busca and not df.empty:
        m = df.astype(str).apply(lambda col: col.str.contains(busca, case=False, na=False)).any(axis=1)
        vista = df[m]
    if df.empty:
        st.info('Todavía no hay personal cargado. Usá **➕ Agregar** para cargar el primero.')
    else:
        st.dataframe(vista[list(COLS)].rename(columns=COLS), use_container_width=True, hide_index=True)

    if not puede:
        st.caption('🔒 Solo el Administrador puede agregar, modificar o eliminar personal.')
        return

    t_add, t_ed, t_del = st.tabs(['➕ Agregar', '✏️ Modificar', '🗑️ Eliminar'])

    with t_add:
        with st.form('pers_add', clear_on_submit=True):
            v = _campos('add')
            ok = st.form_submit_button('💾 Guardar profesional', type='primary')
        if ok and _validar(v) and sec.exigir('gestionar_personal'):
            if v['id_legajo_personal'] in set(df['id_legajo_personal'].astype(str)):
                st.error(f"Ya existe un profesional con el legajo {v['id_legajo_personal']}.")
            else:
                with db.transaccion(sec.DB_NAME) as cur:
                    cur.execute('INSERT INTO personal_gabinete (id_legajo_personal, apellido_nombre, dni, matricula,'
                                ' especialidad, telefono) VALUES (?, ?, ?, ?, ?, ?)',
                                tuple(v[c] for c in COLS))
                sec.registrar_auditoria('Personal', 'INSERT', f"Alta de {v['apellido_nombre']}", v['id_legajo_personal'])
                st.session_state['pers_ok'] = f"✅ {v['apellido_nombre']} agregado al gabinete."
                st.rerun()

    if df.empty:
        for t in (t_ed, t_del):
            t.caption('No hay personal para modificar o eliminar.')
        return
    opciones = {str(r['id_legajo_personal']): f"{r['apellido_nombre']} · Leg. {r['id_legajo_personal']}"
                + (f" · {r['especialidad']}" if r['especialidad'] else '') for _, r in df.iterrows()}

    with t_ed:
        sel = st.selectbox('Profesional', list(opciones), format_func=opciones.get, key='pers_sel_ed')
        r = df[df['id_legajo_personal'].astype(str) == sel].iloc[0].to_dict()
        with st.form(f'pers_ed_{sel}'):
            v = _campos(f'ed_{sel}', r)
            ok = st.form_submit_button('💾 Guardar cambios', type='primary')
        if ok and _validar(v) and sec.exigir('gestionar_personal'):
            otros = set(df['id_legajo_personal'].astype(str)) - {sel}
            if v['id_legajo_personal'] in otros:
                st.error(f"El legajo {v['id_legajo_personal']} ya pertenece a otro profesional.")
            else:
                with db.transaccion(sec.DB_NAME) as cur:
                    cur.execute('UPDATE personal_gabinete SET id_legajo_personal = ?, apellido_nombre = ?, dni = ?,'
                                ' matricula = ?, especialidad = ?, telefono = ? WHERE id_legajo_personal = ?',
                                (*[v[c] for c in COLS], sel))
                sec.registrar_auditoria('Personal', 'UPDATE', f"Modificación de {v['apellido_nombre']}", sel)
                st.session_state['pers_ok'] = f"✅ Datos de {v['apellido_nombre']} actualizados."
                st.rerun()

    with t_del:
        sel_d = st.selectbox('Profesional', list(opciones), format_func=opciones.get, key='pers_sel_del')
        st.warning(f'Se eliminará a **{html.escape(opciones[sel_d])}** del listado de personal. '
                   'Las notas y altas que ya firmó no se modifican.')
        conf = st.checkbox('Confirmo la eliminación', key=f'pers_conf_{sel_d}')
        if st.button('🗑️ Eliminar', disabled=not conf, key=f'pers_del_{sel_d}') and sec.exigir('gestionar_personal'):
            with db.transaccion(sec.DB_NAME) as cur:
                cur.execute('DELETE FROM personal_gabinete WHERE id_legajo_personal = ?', (sel_d,))
            sec.registrar_auditoria('Personal', 'DELETE', f'Baja de {opciones[sel_d]}', sel_d)
            st.session_state['pers_ok'] = f'🗑️ {opciones[sel_d].split(" · ")[0]} eliminado.'
            st.rerun()
