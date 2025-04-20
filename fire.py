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

# --- TABS ---
tab1, tab2 = st.tabs(["📋 Ver actividad", "➕ Crear nueva actividad"])

# ─────────────────────────────────────────────────────────────
# 📋 TAB 1: VER ACTIVIDAD
# ─────────────────────────────────────────────────────────────
with tab1:
    st.title("📋 Estado de Aprobación - Curso HTML Y CSS")

    pasos = [
        ("A_Diseño", "Diseño"),
        ("A_AutorizacionINAP", "Autorización INAP"),
        ("A_CargaSAI", "Carga SAI"),
        ("A_TramitacionExpediente", "Tramitación Expediente"),
        ("A_DictamenINAP", "Dictamen INAP"),
    ]

    doc_ref = db.collection("actividades").document("JU-HTML")
    doc_data = doc_ref.get().to_dict()

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
