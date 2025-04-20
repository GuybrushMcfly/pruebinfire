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

# ─────────────────────────────────────────────────────────
# 📋 TAB 1: VER ACTIVIDAD + SEGUIMIENTO
# ─────────────────────────────────────────────────────────
with tab1:
    st.title("📋 Estado de Aprobación y Seguimiento")

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

    def mostrar_stepper(pasos, datos, editable=False, doc_ref=None, suffix=""):
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
            exp_key = f"exp_{suffix}"
            if exp_key not in st.session_state:
                st.session_state[exp_key] = False

            if st.button(f"🛠️ Editar {suffix.capitalize()}", key=f"btn_toggle_{suffix}"):
                st.session_state[exp_key] = not st.session_state[exp_key]

            if st.session_state[exp_key]:
                with st.expander("Editar estado", expanded=True):
                    cambios = {}
                    for col, label in pasos:
                        cambios[col] = st.checkbox(label, value=temp_estado[col], key=f"edit_{suffix}_{col}")
                    if st.button("💾 Actualizar estado", key=f"btn_update_{suffix}"):
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
                                st.session_state[exp_key] = False
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

    actividades_nombres = sorted(actividades_dict.keys())
    actividad_sel = st.selectbox(
    "🔍 Buscar y seleccionar actividad:",
    [""] + actividades_nombres,
    index=0,
    key="actividad_search"
)
    

    if actividad_sel:
        id_act = actividades_dict[actividad_sel]
        doc_ref = db.collection("actividades").document(id_act)
        datos_act = doc_ref.get().to_dict()

        st.markdown("### 🔹 Actividad")
        mostrar_stepper(pasos_act, datos_act, editable=True, doc_ref=doc_ref, suffix="act")

        comisiones = db.collection("comisiones").where("Id_Actividad", "==", id_act).stream()
        comisiones_dict = {doc.id: doc.to_dict() for doc in comisiones}

        if not comisiones_dict:
            st.warning("🔸 Esta actividad no tiene comisiones registradas aún.")
            st.stop()

        com_id = st.selectbox("Seleccioná una comisión:", sorted(comisiones_dict.keys()))

        seguimiento_ref = db.collection("seguimiento").document(com_id)
        seguimiento_doc = seguimiento_ref.get()
        if not seguimiento_doc.exists:
            st.warning("⚠️ No hay datos de seguimiento para esta comisión.")
            st.stop()

        datos_seg = seguimiento_doc.to_dict()

        st.markdown("### 🔹 Campus Virtual")
        mostrar_stepper(pasos_campus, datos_seg, editable=True, doc_ref=seguimiento_ref, suffix="campus")

        st.markdown("### 🔹 Dictado")
        mostrar_stepper(pasos_dictado, datos_seg, editable=True, doc_ref=seguimiento_ref, suffix="dictado")



# ─────────────────────────────────────────────────────────────
# ➕ TAB 2: CREAR NUEVA ACTIVIDAD
# ─────────────────────────────────────────────────────────────
with tab2:
    st.title("➕ Crear nueva actividad")
    with st.form("crear_actividad"):
        nuevo_id = st.text_input("ID de la actividad (ej. JU-NUEVA)")
        nombre = st.text_input("Nombre de la actividad")
        area = st.text_input("Área temática",value="")
        enviar = st.form_submit_button("🚀 Crear actividad")
    if enviar:
        if not nuevo_id or not nombre:
            st.warning("🟡 Completá campos obligatorios.")
        else:
            ref = db.collection("actividades").document(nuevo_id)
            if ref.get().exists:
                st.error("❌ ID ya existe.")
            else:
                ref.set({"NombreActividad":nombre,"Area":area,
                         "A_Diseño":False,"A_AutorizacionINAP":False,
                         "A_CargaSAI":False,"A_TramitacionExpediente":False,
                         "A_DictamenINAP":False})
                st.success(f"✅ Actividad '{nombre}' con ID '{nuevo_id}' creada.")

# ─────────────────────────────────────────────────────────────
# ➕ TAB 3: CREAR NUEVA COMISIÓN
# ─────────────────────────────────────────────────────────────
with tab3:
    st.title("➕ Crear nueva comisión")
    activs = db.collection("actividades").stream()
    act_dict = {d.to_dict().get("NombreActividad"):d.id for d in activs if d.to_dict().get("NombreActividad")}
    if not act_dict:
        st.warning("⚠️ Crea una actividad primero.")
        st.stop()
    # Selector de actividad (dropdown)
    act_sel = st.selectbox("Actividad asociada:",sorted(act_dict.keys()))
    if act_sel:
        if st.session_state.get("reset_comision",True):
            st.session_state.update({"id_comision":"","fecha_inicio_comision":None,"fecha_fin_comision":None,"reset_comision":False})
        with st.form("form_crear_comision"):
            id_com = st.text_input("ID de la comisión (ej. JU-HTML-01)",key="id_comision")
            fecha_ini = st.date_input("Fecha de inicio",key="fecha_inicio_comision")
            fecha_fin = st.date_input("Fecha de finalización",key="fecha_fin_comision")
            crear = st.form_submit_button("🚀 Crear comisión")
        if crear:
            if not id_com:
                st.warning("🟡 ID requerido.")
                st.stop()
            if fecha_ini>fecha_fin:
                st.error("�?❌ Fecha inicio posterior a fin.")
                st.stop()
            año=fecha_ini.year; hoy=datetime.today().date()
            estado = "PENDIENTE" if hoy<fecha_ini else "FINALIZADA" if hoy>fecha_fin else "CURSANDO"
            com_ref=db.collection("comisiones").document(id_com)
            seg_ref=db.collection("seguimiento").document(id_com)
            if com_ref.get().exists:
                st.error("❌ Comisión existe.")
                st.stop()
            try:
                com_ref.set({"Id_Comision":id_com,"Id_Actividad":act_dict[act_sel],
                             "AñoComision":año,"FechaInicio":fecha_ini.strftime("%d/%m/%Y"),
                             "FechaFin":fecha_fin.strftime("%d/%m/%Y"),"EstadoComision":estado})
                pasos=["C_ArmadoAula","C_Matriculacion","C_AperturaCurso","C_CierreCurso","C_AsistenciaEvaluacion",
                       "D_Difusion","D_AsignacionVacantes","D_Cursada","D_AsistenciaEvaluacion","D_CreditosSAI"]
                seg_data={"Id_Comision":id_com}
                for p in pasos: seg_data[p]=False; seg_data[f"{p}_user"]=""; seg_data[f"{p}_timestamp"]=""
                seg_ref.set(seg_data)
                st.success(f"✅ Comisión '{id_com}' creada.")
                st.session_state["reset_comision"]=True
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ─────────────────────────────────────────────────────────────
# 🛠️ TAB 4: EDITAR COMISIONES EXISTENTES
# ─────────────────────────────────────────────────────────────
with tab4:
    st.title("🛠️ Editar comisiones existentes")
    coms=db.collection("comisiones").stream()
    com_list=[c.to_dict() for c in coms]
    if not com_list:
        st.warning("Sin comisiones."); st.stop()
    activs=db.collection("actividades").stream()
    act_dict={d.id:d.to_dict().get("NombreActividad",d.id) for d in activs}
    # Selector de actividad
    actividad = st.selectbox("Filtrar actividad:", sorted(act_dict.values()))
    id_act = next(k for k,v in act_dict.items() if v == actividad)
    filt=[c for c in com_list if c["Id_Actividad"]==id_act]
    if not filt:
        st.warning("Sin comisiones."); st.stop()
    sel = st.selectbox("Selecciona comisión:",[c["Id_Comision"] for c in filt])
    data = next(c for c in filt if c["Id_Comision"]==sel)
    with st.form("form_editar_comision"):
        st.subheader(f"✏️ Editar comisión: {sel}")
        f_ini = datetime.strptime(data["FechaInicio"], "%d/%m/%Y").date()
        f_fin = datetime.strptime(data["FechaFin"], "%d/%m/%Y").date()
        f_ini=st.date_input("Fecha de inicio", value=f_ini)
        f_fin=st.date_input("Fecha de finalización", value=f_fin)
        vac = st.number_input("Vacantes", value=data.get("Vacantes",0), min_value=0)
        apr = st.number_input("Aprobados", value=data.get("Aprobados",0), min_value=0)
        guardar = st.form_submit_button("💾 Actualizar comisión")
    if guardar:
        hoy = datetime.today().date()
        estado="PENDIENTE" if hoy<f_ini else "FINALIZADA" if hoy>f_fin else "CURSANDO"
        try:
            db.collection("comisiones").document(sel).update({"FechaInicio":f_ini.strftime("%d/%m/%Y"),
                                                               "FechaFin":f_fin.strftime("%d/%m/%Y"),
                                                               "Vacantes":vac, "Aprobados":apr,
                                                               "EstadoComision":estado})
            st.success("✅ Comisión actualizada.")
        except Exception as e:
            st.error(f"❌ Error al actualizar: {e}")
