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
# 📋 TAB 1: VER ACTIVIDAD
# ─────────────────────────────────────────────────────────────
with tab1:
    st.title("📋 Estado de Aprobación")

    pasos = [
        ("A_Diseño", "Diseño"),
        ("A_AutorizacionINAP", "Autorización INAP"),
        ("A_CargaSAI", "Carga SAI"),
        ("A_TramitacionExpediente", "Tramitación Expediente"),
        ("A_DictamenINAP", "Dictamen INAP"),
    ]

    # Obtener lista de actividades
    actividades = db.collection("actividades").stream()
    actividades_dict = {}
    for doc in actividades:
        data = doc.to_dict()
        if "NombreActividad" in data:
            actividades_dict[data["NombreActividad"]] = doc.id

    if not actividades_dict:
        st.warning("⚠️ No hay actividades registradas.")
        st.stop()

    curso = st.selectbox("Seleccioná una actividad:", sorted(actividades_dict.keys()))
    id_act = actividades_dict[curso]
    doc_ref = db.collection("actividades").document(id_act)
    doc_data = doc_ref.get().to_dict()

    # Stepper visual
    bools = [doc_data.get(col, False) for col, _ in pasos]
    idx = len(bools) if all(bools) else next(i for i, v in enumerate(bools) if not v)
    fig = go.Figure(); x, y = list(range(len(pasos))), 1
    colors = {"ok": "#4DB6AC", "now": "#FF8A65", "no": "#D3D3D3"}
    icons = {"finalizado": "✓", "actual": "⏳", "pendiente": "⚪"}

    for i in range(len(pasos)-1):
        clr = colors["ok"] if i < idx else colors["no"]
        fig.add_trace(go.Scatter(x=[x[i], x[i+1]], y=[y, y], mode="lines",
                                 line=dict(color=clr, width=8), showlegend=False))

    for i, (col, label) in enumerate(pasos):
        estado = doc_data.get(col, False)
        if estado: clr, ic = colors["ok"], icons["finalizado"]
        elif i == idx: clr, ic = colors["now"], icons["actual"]
        else: clr, ic = colors["no"], icons["pendiente"]
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

    # Formulario para modificar
    with st.form("form_aprobacion"):
        usuario = st.text_input("Tu nombre (para registrar cambios)", value="Anónimo")
        temp_estado = {}
        for col, label in pasos:
            temp_estado[col] = st.checkbox(label, value=doc_data.get(col, False))
        submitted = st.form_submit_button("💾 Actualizar")

    if submitted:
        for i in range(len(pasos)):
            col = pasos[i][0]
            if temp_estado[col] and not all(temp_estado[pasos[j][0]] for j in range(i)):
                st.error(f"❌ No se puede marcar '{pasos[i][1]}' sin completar los anteriores.")
                st.stop()

        try:
            now = datetime.utcnow().isoformat()
            update_data = {}
            for col, _ in pasos:
                if temp_estado[col] != doc_data.get(col, False):
                    update_data[col] = temp_estado[col]
                    update_data[f"{col}_user"] = usuario
                    update_data[f"{col}_timestamp"] = now

            if update_data:
                doc_ref.update(update_data)
                st.success("✅ Datos actualizados correctamente")
                st.rerun()
            else:
                st.info("No hubo cambios para guardar.")
        except Exception as e:
            st.error(f"Error al actualizar: {e}")

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

    # Cargar lista de actividades
    actividades = db.collection("actividades").stream()
    actividades_dict = {}
    for doc in actividades:
        data = doc.to_dict()
        if "NombreActividad" in data:
            actividades_dict[data["NombreActividad"]] = doc.id

    if not actividades_dict:
        st.warning("⚠️ No hay actividades disponibles. Creá una actividad primero.")
        st.stop()

    # Inicializar claves si es la primera vez o se acaba de crear
    if st.session_state.get("reset_comision", True):
        st.session_state["id_comision"] = ""
        st.session_state["actividad_comision"] = list(actividades_dict.keys())[0]
        st.session_state["fecha_inicio_comision"] = None
        st.session_state["fecha_fin_comision"] = None
        st.session_state["vacantes_comision"] = 0
        st.session_state["aprobados_comision"] = 0
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

        id_act = actividades_dict[act_sel]
        año = fecha_ini.year
        fecha_ini_str = fecha_ini.strftime("%Y-%m-%d")
        fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")

        hoy = datetime.today().date()
        if hoy < fecha_ini:
            estado = "PENDIENTE"
        elif hoy > fecha_fin:
            estado = "FINALIZADA"
        else:
            estado = "CURSANDO"

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
                "EstadoComision": estado,
         #       "Vacantes": vacantes,
         #       "Aprobados": aprobados
            })

            pasos_campus = [
                "C_ArmadoAula", "C_Matriculacion", "C_AperturaCurso", "C_CierreCurso", "C_AsistenciaEvaluacion"
            ]
            pasos_dictado = [
                "D_Difusion", "D_AsignacionVacantes", "D_Cursada", "D_AsistenciaEvaluacion", "D_CreditosSAI"
            ]
            seguimiento_data = {"Id_Comision": id_com}
            for paso in pasos_campus + pasos_dictado:
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

    # 1. Cargar comisiones
    coms_raw = db.collection("comisiones").stream()
    comisiones = [doc.to_dict() for doc in coms_raw]
    if not comisiones:
        st.warning("No hay comisiones cargadas.")
        st.stop()

    # 2. Obtener lista de actividades
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

    # 3. Formulario de edición
    with st.form("form_editar_comision"):
        st.subheader(f"✏️ Editar comisión: {com_id_sel}")
        f_ini = st.date_input("Fecha de inicio", value=datetime.strptime(com_data["FechaInicio"], "%Y-%m-%d").date())
        f_fin = st.date_input("Fecha de finalización", value=datetime.strptime(com_data["FechaFin"], "%Y-%m-%d").date())
        vac = st.number_input("Vacantes", value=com_data.get("Vacantes", 0), min_value=0)
        apr = st.number_input("Aprobados", value=com_data.get("Aprobados", 0), min_value=0)
        guardar = st.form_submit_button("💾 Actualizar comisión")

    if guardar:
        hoy = datetime.today().date()
        if hoy < f_ini:
            estado = "PENDIENTE"
        elif hoy > f_fin:
            estado = "FINALIZADA"
        else:
            estado = "CURSANDO"

        try:
            db.collection("comisiones").document(com_id_sel).update({
                "FechaInicio": f_ini.strftime("%Y-%m-%d"),
                "FechaFin": f_fin.strftime("%Y-%m-%d"),
                "Vacantes": vac,
                "Aprobados": apr,
                "EstadoComision": estado
            })
            st.success("✅ Comisión actualizada correctamente")
       #     st.experimental_rerun()
        except Exception as e:
            st.error(f"❌ Error al actualizar: {e}")



