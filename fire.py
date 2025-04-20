import json
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

# --- INICIALIZACIÓN FIREBASE ---
creds_dict = json.loads(st.secrets["GOOGLE_FIREBASE_CREDS"])
cred = credentials.Certificate(creds_dict)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Actividades", layout="wide")

# --- TABS PRINCIPALES ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Ver actividad",
    "➕ Crear nueva actividad",
    "➕ Crear comisión",
    "🛠️ Editar comisiones"
])

# ─────────────────────────────────────────────────────────────
# 📋 TAB 1: VER ACTIVIDAD + SEGUIMIENTO
# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# 📋 TAB 1: VER ACTIVIDAD + SEGUIMIENTO
# ─────────────────────────────────────────────────────────────
with tab1:
    st.title("📋 Estado de Aprobación y Seguimiento")

    # Pasos de actividad
    pasos_act = [
        ("A_Diseño", "Diseño"),
        ("A_AutorizacionINAP", "Autorización INAP"),
        ("A_CargaSAI", "Carga SAI"),
        ("A_TramitacionExpediente", "Tramitación Expediente"),
        ("A_DictamenINAP", "Dictamen INAP"),
    ]

    pasos_campus = [
        ("C_ArmadoAula", "Armado Aula"),
        ("C_Matriculacion", "Matriculación"),
        ("C_AperturaCurso", "Apertura"),
        ("C_CierreCurso", "Cierre"),
        ("C_AsistenciaEvaluacion", "Evaluación")
    ]

    pasos_dictado = [
        ("D_Difusion", "Difusión"),
        ("D_AsignacionVacantes", "Vacantes"),
        ("D_Cursada", "Cursada"),
        ("D_AsistenciaEvaluacion", "Evaluación"),
        ("D_CreditosSAI", "Créditos")
    ]

    colores = {"ok": "#4DB6AC", "now": "#FF8A65", "no": "#D3D3D3"}
    iconos = {"finalizado": "✓", "actual": "⏳", "pendiente": "⚪"}

    def mostrar_stepper(pasos, datos, editable=False, doc_ref=None):
        temp_estado = {}
        for col, _ in pasos:
            temp_estado[col] = datos.get(col, False)

        bools = [temp_estado[col] for col, _ in pasos]
        idx = len(bools) if all(bools) else next((i for i, v in enumerate(bools) if not v), 0)

        fig = go.Figure(); x, y = list(range(len(pasos))), 1

        for i in range(len(pasos)-1):
            clr = colores["ok"] if i < idx else colores["no"]
            fig.add_trace(go.Scatter(x=[x[i], x[i+1]], y=[y, y], mode="lines",
                                     line=dict(color=clr, width=8), showlegend=False))

        for i, (col, label) in enumerate(pasos):
            estado = temp_estado[col]
            if estado: clr, ic = colores["ok"], iconos["finalizado"]
            elif i == idx: clr, ic = colores["now"], iconos["actual"]
            else: clr, ic = colores["no"], iconos["pendiente"]
            fig.add_trace(go.Scatter(x=[x[i]], y=[y], mode="markers+text",
                                     marker=dict(size=45, color=clr),
                                     text=[ic], textposition="middle center",
                                     textfont=dict(color="white", size=18),
                                     hovertext=[label], hoverinfo="text", showlegend=False))
            fig.add_trace(go.Scatter(x=[x[i]], y=[y-0.2], mode="text",
                                     text=[label], textposition="bottom center",
                                     textfont=dict(color="white", size=16), showlegend=False))

        fig.update_layout(xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                          yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.3, 1.2]),
                          height=160, margin=dict(l=20, r=20, t=30, b=0))
        st.plotly_chart(fig, config={"displayModeBar": False})

        if editable:
            with st.expander("🛠️ Editar estado"):
                cambios = {}
                for col, label in pasos:
                    cambios[col] = st.checkbox(label, value=temp_estado[col], key=f"edit_{col}")
                if st.button("💾 Actualizar estado"):
                    for i in range(len(pasos)):
                        col = pasos[i][0]
                        if cambios[col]:
                            anteriores = [cambios[pasos[j][0]] for j in range(i)]
                            if not all(anteriores):
                                st.error(f"❌ No se puede marcar '{pasos[i][1]}' sin completar pasos anteriores.")
                                st.stop()
                    try:
                        now = datetime.utcnow().isoformat()
                        update_data = {}
                        for col in cambios:
                            if cambios[col] != datos.get(col, False):
                                update_data[col] = cambios[col]
                                update_data[f"{col}_user"] = st.session_state.get("name", "Anónimo")
                                update_data[f"{col}_timestamp"] = now
                        if update_data:
                            doc_ref.update(update_data)
                            st.success("✅ Datos actualizados correctamente")
                            st.rerun()
                        else:
                            st.info("No hubo cambios para guardar.")
                    except Exception as e:
                        st.error(f"Error al actualizar: {e}")

    # Cargar actividades
    actividades = db.collection("actividades").stream()
    actividades_dict = {}
    for doc in actividades:
        data = doc.to_dict()
        if "NombreActividad" in data:
            actividades_dict[data["NombreActividad"]] = doc.id

    if not actividades_dict:
        st.warning("⚠️ No hay actividades registradas.")
        st.stop()

    actividad_sel = st.selectbox("Seleccioná una actividad:", sorted(actividades_dict.keys()))
    id_act = actividades_dict[actividad_sel]
    doc_ref = db.collection("actividades").document(id_act)
    datos_act = doc_ref.get().to_dict()

    st.markdown("### 🔹 Actividad")
    mostrar_stepper(pasos_act, datos_act, editable=True, doc_ref=doc_ref)

    # Comisiones de esa actividad
    comisiones = db.collection("comisiones").where("Id_Actividad", "==", id_act).stream()
    comisiones_dict = {doc.id: doc.to_dict() for doc in comisiones}

    if not comisiones_dict:
        st.warning("🔸 Esta actividad no tiene comisiones registradas aún.")
        st.stop()

    com_id = st.selectbox("Seleccioná una comisión:", sorted(comisiones_dict.keys()))

    # Datos de seguimiento
    seguimiento_ref = db.collection("seguimiento").document(com_id)
    seguimiento_doc = seguimiento_ref.get()
    if not seguimiento_doc.exists:
        st.warning("⚠️ No hay datos de seguimiento para esta comisión.")
        st.stop()

    datos_seg = seguimiento_doc.to_dict()

    st.markdown("### 🔹 Campus Virtual")
    mostrar_stepper(pasos_campus, datos_seg, editable=True, doc_ref=seguimiento_ref)

    st.markdown("### 🔹 Dictado")
    mostrar_stepper(pasos_dictado, datos_seg, editable=True, doc_ref=seguimiento_ref)



# ─────────────────────────────────────────────────────────────
# ➕ TAB 2: CREAR NUEVA ACTIVIDAD
# ─────────────────────────────────────────────────────────────
with tab2:
    st.title("➕ Crear nueva actividad")

    with st.form("crear_actividad"):
        nuevo_id = st.text_input("ID de la actividad (ej. JU-NUEVA)")
        nombre = st.text_input("Nombre de la actividad")
        area = st.text_input("Área temática", value="")
        enviar = st.form_submit_button("🚀 Crear actividad")

    if enviar:
        if not nuevo_id or not nombre:
            st.warning("🟡 Completá todos los campos obligatorios.")
        else:
            doc_ref = db.collection("actividades").document(nuevo_id)
            if doc_ref.get().exists:
                st.error("❌ Ya existe una actividad con ese ID.")
            else:
                doc_ref.set({
                    "NombreActividad": nombre,
                    "Area": area,
                    "A_Diseño": False,
                    "A_AutorizacionINAP": False,
                    "A_CargaSAI": False,
                    "A_TramitacionExpediente": False,
                    "A_DictamenINAP": False,
                })
                st.success(f"✅ Actividad '{nombre}' creada con ID '{nuevo_id}'")

# ─────────────────────────────────────────────────────────────
# ➕ TAB 3: CREAR NUEVA COMISIÓN
# ─────────────────────────────────────────────────────────────
with tab3:
    st.title("➕ Crear nueva comisión")

    actividades = db.collection("actividades").stream()
    actividades_dict = {}
    for doc in actividades:
        data = doc.to_dict()
        if "NombreActividad" in data:
            actividades_dict[data["NombreActividad"]] = doc.id

    if not actividades_dict:
        st.warning("⚠️ No hay actividades disponibles. Creá una actividad primero.")
        st.stop()

    if st.session_state.get("reset_comision", True):
        st.session_state["id_comision"] = ""
        st.session_state["actividad_comision"] = list(actividades_dict.keys())[0]
        st.session_state["fecha_inicio_comision"] = None
        st.session_state["fecha_fin_comision"] = None
        st.session_state["reset_comision"] = False

    with st.form("form_crear_comision"):
        id_com = st.text_input("ID de la comisión (ej. JU-HTML-01)", key="id_comision")
        act_sel = st.selectbox("Actividad asociada:", sorted(actividades_dict.keys()), key="actividad_comision")
        fecha_ini = st.date_input("Fecha de inicio", key="fecha_inicio_comision")
        fecha_fin = st.date_input("Fecha de finalización", key="fecha_fin_comision")
        crear = st.form_submit_button("🚀 Crear comisión")

    if crear:
        if not id_com:
            st.warning("🟡 Ingresá un ID para la comisión.")
            st.stop()

        if fecha_ini > fecha_fin:
            st.error("❌ La fecha de inicio no puede ser posterior a la fecha de finalización.")
            st.stop()

        id_act = actividades_dict[act_sel]
        año = fecha_ini.year

        hoy = datetime.today().date()
        estado = "PENDIENTE" if hoy < fecha_ini else "FINALIZADA" if hoy > fecha_fin else "CURSANDO"

        fecha_ini_str = fecha_ini.strftime("%d/%m/%Y")
        fecha_fin_str = fecha_fin.strftime("%d/%m/%Y")

        com_ref = db.collection("comisiones").document(id_com)
        seg_ref = db.collection("seguimiento").document(id_com)

        if com_ref.get().exists:
            st.error("❌ Ya existe una comisión con ese ID.")
            st.stop()

        try:
            com_ref.set({
                "Id_Comision": id_com,
                "Id_Actividad": id_act,
                "AñoComision": año,
                "FechaInicio": fecha_ini_str,
                "FechaFin": fecha_fin_str,
                "EstadoComision": estado
            })

            pasos = ["C_ArmadoAula", "C_Matriculacion", "C_AperturaCurso", "C_CierreCurso", "C_AsistenciaEvaluacion",
                     "D_Difusion", "D_AsignacionVacantes", "D_Cursada", "D_AsistenciaEvaluacion", "D_CreditosSAI"]
            seguimiento_data = {"Id_Comision": id_com}
            for paso in pasos:
                seguimiento_data[paso] = False
                seguimiento_data[f"{paso}_user"] = ""
                seguimiento_data[f"{paso}_timestamp"] = ""

            seg_ref.set(seguimiento_data)

            st.success(f"✅ Comisión '{id_com}' creada correctamente.")
            st.session_state["reset_comision"] = True

        except Exception as e:
            st.error(f"❌ Error al crear la comisión: {e}")

# ─────────────────────────────────────────────────────────────
# 🛠️ TAB 4: EDITAR COMISIONES EXISTENTES
# ─────────────────────────────────────────────────────────────
with tab4:
    st.title("🛠️ Editar comisiones existentes")

    coms_raw = db.collection("comisiones").stream()
    comisiones = [doc.to_dict() for doc in coms_raw]
    if not comisiones:
        st.warning("No hay comisiones cargadas.")
        st.stop()

    actividades = db.collection("actividades").stream()
    actividades_dict = {doc.id: doc.to_dict().get("NombreActividad", doc.id) for doc in actividades}
    id_to_nombre = {v: k for k, v in actividades_dict.items()}

    nombre_sel = st.selectbox("🔍 Filtrar por actividad:", sorted(actividades_dict.values()))
    id_actividad = id_to_nombre[nombre_sel]
    coms_filtradas = [c for c in comisiones if c["Id_Actividad"] == id_actividad]

    if not coms_filtradas:
        st.warning("No hay comisiones para esta actividad.")
        st.stop()

    com_ids = [c["Id_Comision"] for c in coms_filtradas]
    com_id_sel = st.selectbox("🔍 Seleccioná una comisión:", com_ids)
    com_data = next(c for c in coms_filtradas if c["Id_Comision"] == com_id_sel)

    with st.form("form_editar_comision"):
        st.subheader(f"✏️ Editar comisión: {com_id_sel}")
        f_ini = datetime.strptime(com_data["FechaInicio"], "%d/%m/%Y").date()
        f_fin = datetime.strptime(com_data["FechaFin"], "%d/%m/%Y").date()
        f_ini = st.date_input("Fecha de inicio", value=f_ini)
        f_fin = st.date_input("Fecha de finalización", value=f_fin)
        vac = st.number_input("Vacantes", value=com_data.get("Vacantes", 0), min_value=0)
        apr = st.number_input("Aprobados", value=com_data.get("Aprobados", 0), min_value=0)
        guardar = st.form_submit_button("💾 Actualizar comisión")

    if guardar:
        hoy = datetime.today().date()
        estado = "PENDIENTE" if hoy < f_ini else "FINALIZADA" if hoy > f_fin else "CURSANDO"
        try:
            db.collection("comisiones").document(com_id_sel).update({
                "FechaInicio": f_ini.strftime("%d/%m/%Y"),
                "FechaFin": f_fin.strftime("%d/%m/%Y"),
                "Vacantes": vac,
                "Aprobados": apr,
                "EstadoComision": estado
            })
            st.success("✅ Comisión actualizada correctamente")
        except Exception as e:
            st.error(f"❌ Error al actualizar: {e}")



