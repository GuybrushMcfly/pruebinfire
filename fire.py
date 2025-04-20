import streamlit as st
import plotly.graph_objects as go
import firebase_admin
from firebase_admin import credentials, firestore

# --- INICIALIZACIÓN FIREBASE ---
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-cred.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Stepper desde Firebase", layout="wide")
st.title("📋 Estado de Aprobación - Curso HTML Y CSS")

# --- DEFINIR PASOS ---
pasos = [
    ("A_Diseño", "Diseño"),
    ("A_AutorizacionINAP", "Autorización INAP"),
    ("A_CargaSAI", "Carga SAI"),
    ("A_TramitacionExpediente", "Tramitación Expediente"),
    ("A_DictamenINAP", "Dictamen INAP"),
]

doc_ref = db.collection("actividades").document("JU-HTML")
doc_data = doc_ref.get().to_dict()

# --- VISUALIZAR BARRA DE PROGRESO ---
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

# --- FORMULARIO DE ACTUALIZACIÓN ---
with st.form("form_aprobacion"):
    temp_estado = {}
    for col, label in pasos:
        temp_estado[col] = st.checkbox(label, value=doc_data.get(col, False))
    submitted = st.form_submit_button("💾 Actualizar")

if submitted:
    # Validar orden lógico (no marcar un paso si anteriores están vacíos)
    for i in range(len(pasos)):
        col = pasos[i][0]
        if temp_estado[col] and not all(temp_estado[pasos[j][0]] for j in range(i)):
            st.error(f"❌ No se puede marcar '{pasos[i][1]}' sin completar los anteriores.")
            st.stop()
    try:
        doc_ref.update(temp_estado)
        st.success("✅ Datos actualizados correctamente")
        st.rerun()
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
