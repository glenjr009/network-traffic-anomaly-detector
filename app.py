import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import plotly.graph_objects as go

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------

st.set_page_config(
    page_title="3D SOC Anomaly Detector",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# 3D Background & Custom CSS
# -------------------------------------------------

st.markdown("""
<style>
/* Import Modern Font */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif;
    color: #E0E6ED;
}

/* 3D Dynamic Deep Background */
.stApp {
    background: radial-gradient(circle at 50% 20%, #101626 0%, #080B12 60%, #030407 100%);
    background-attachment: fixed;
}

/* Glassmorphic & 3D Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(16, 22, 38, 0.85) 0%, rgba(8, 11, 18, 0.95) 100%);
    border-right: 1px solid rgba(0, 229, 255, 0.2);
    box-shadow: 10px 0 30px rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(12px);
}

/* Title Font */
h1, h2, h3 {
    font-family: 'Orbitron', sans-serif !important;
    letter-spacing: 1.5px;
}

/* 3D Hero Title Banner */
.hero-3d-card {
    background: linear-gradient(135deg, rgba(20, 29, 47, 0.6) 0%, rgba(10, 14, 23, 0.8) 100%);
    border: 1px solid rgba(0, 229, 255, 0.3);
    border-radius: 16px;
    padding: 30px;
    margin-bottom: 25px;
    box-shadow:
        0 15px 35px rgba(0, 0, 0, 0.6),
        inset 0 1px 0 rgba(255, 255, 255, 0.1),
        0 0 20px rgba(0, 229, 255, 0.15);
    transform: perspective(1000px) rotateX(1deg);
    backdrop-filter: blur(10px);
}

/* 3D KPI Cards with Hover Lift */
.card-3d {
    background: linear-gradient(145deg, #131A29, #0B0F19);
    border-radius: 16px;
    padding: 20px 24px;
    position: relative;
    border: 1px solid rgba(0, 229, 255, 0.15);
    box-shadow:
        8px 8px 18px #05070C,
        -6px -6px 15px rgba(255, 255, 255, 0.03),
        inset 0 0 12px rgba(0, 229, 255, 0.05);
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.card-3d:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow:
        0 20px 30px rgba(0, 0, 0, 0.7),
        0 0 25px rgba(0, 229, 255, 0.3);
    border-color: #00E5FF;
}

.card-label {
    font-size: 0.85rem;
    color: #8A99AD;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 700;
}

.card-value {
    font-family: 'Orbitron', sans-serif;
    font-size: 2.1rem;
    font-weight: 900;
    margin-top: 8px;
    text-shadow: 0 0 12px rgba(0, 229, 255, 0.4);
}

/* Custom 3D File Upload Area */
div[data-testid="stFileUploader"] {
    background: linear-gradient(135deg, rgba(17, 24, 39, 0.7), rgba(9, 13, 22, 0.9));
    border: 2px dashed rgba(0, 229, 255, 0.3);
    border-radius: 16px;
    padding: 20px;
    box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5);
    transition: all 0.3s ease;
}

div[data-testid="stFileUploader"]:hover {
    border-color: #00E5FF;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
}

/* 3D Neumorphic Buttons */
.stButton>button {
    background: linear-gradient(135deg, #00E5FF 0%, #0072FF 100%);
    color: #000;
    font-family: 'Orbitron', sans-serif;
    font-weight: 700;
    border: none;
    border-radius: 12px;
    padding: 12px 28px;
    box-shadow: 0 6px 20px rgba(0, 229, 255, 0.4);
    transition: all 0.3s ease;
}

.stButton>button:hover {
    transform: translateY(-3px) scale(1.03);
    box-shadow: 0 10px 30px rgba(0, 229, 255, 0.7);
}

.stDownloadButton>button {
    background: linear-gradient(135deg, #00E676 0%, #00897B 100%);
    color: #fff;
    font-family: 'Orbitron', sans-serif;
    border-radius: 12px;
    box-shadow: 0 6px 20px rgba(0, 230, 118, 0.3);
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Interactive 3D Canvas Background Particle Mesh
# -------------------------------------------------

st.components.v1.html("""
<canvas id="bg3d" style="position:fixed; top:0; left:0; width:100vw; height:100vh; pointer-events:none; z-index:0; opacity:0.35;"></canvas>
<script>
const canvas = document.getElementById('bg3d');
const ctx = canvas.getContext('2d');
let w, h, particles = [];

function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

for(let i=0; i<60; i++){
    particles.push({
        x: Math.random()*w,
        y: Math.random()*h,
        z: Math.random()*w,
        size: Math.random()*2.5 + 1,
        vx: (Math.random()-0.5)*0.8,
        vy: (Math.random()-0.5)*0.8
    });
}

function animate(){
    ctx.clearRect(0, 0, w, h);

    particles.forEach((p, index) => {
        p.x += p.vx;
        p.y += p.vy;

        if(p.x < 0 || p.x > w) p.vx *= -1;
        if(p.y < 0 || p.y > h) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI*2);
        ctx.fillStyle = '#00E5FF';
        ctx.shadowBlur = 10;
        ctx.shadowColor = '#00E5FF';
        ctx.fill();

        for(let j=index+1; j<particles.length; j++){
            let p2 = particles[j];
            let dist = Math.hypot(p.x-p2.x, p.y-p2.y);
            if(dist < 140){
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.strokeStyle = `rgba(0, 229, 255, ${1 - dist/140})`;
                ctx.lineWidth = 0.5;
                ctx.stroke();
            }
        }
    });
    requestAnimationFrame(animate);
}
animate();
</script>
""", height=0)

# -------------------------------------------------
# Load Model
# -------------------------------------------------

@st.cache_resource
def load_resources():
    model = joblib.load("models/cicids_anomaly_model.pkl")
    label_encoder = joblib.load("models/cicids_label_encoder.pkl")
    return model, label_encoder

try:
    model, label_encoder = load_resources()
except Exception as e:
    st.error("Model files missing inside `models/` directory.")

# -------------------------------------------------
# Sidebar
# -------------------------------------------------

with st.sidebar:
    st.image("models/logo.png", width=170)
    st.title("🛡️ SOC 3D CORE")

    st.markdown("""
        <div style="background: rgba(0, 230, 118, 0.1); border: 1px solid #00E676; padding: 10px; border-radius: 12px; text-align: center; box-shadow: 0 0 15px rgba(0, 230, 118, 0.2);">
            <span style="color: #00E676; font-weight: 700; letter-spacing: 1px;">🟢 3D TELEMETRY ACTIVE</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔹 Modules")
    st.markdown("📂 **Data Ingestion**")
    st.markdown("⚡ **Real-time Inference**")
    st.markdown("📊 **3D Spatial Analytics**")
    st.markdown("📥 **Cyber Threat Report**")

    st.markdown("---")
    st.caption("Architecture: ML-IDS Pipeline v3.0")

# -------------------------------------------------
# Main Hero Section
# -------------------------------------------------

st.markdown("""
<div class="hero-3d-card">
    <h1 style="color: #00E5FF; margin:0; font-size: 2.3rem; text-shadow: 0 0 15px rgba(0,229,255,0.4);">
        🛡️ NETWORK TRAFFIC ANOMALY DETECTOR
    </h1>
    <p style="color: #8A99AD; margin-top: 8px; font-size: 1.1rem; font-weight: 500;">
        Next-Gen Spatial Intelligence & AI-Powered Intrusion Detection System
    </p>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Dataset Uploader
# -------------------------------------------------

uploaded_file = st.file_uploader(
    "Choose a PCAP / CSV Network File",
    type=["csv"],
    help="Upload preprocessed network flow CSV data."
)

# -------------------------------------------------
# Processing & Predictions
# -------------------------------------------------

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file, low_memory=False)

    # Cleaning
    df.columns = df.columns.str.strip()
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    if "Label" in df.columns:
        df = df.drop(columns=["Label"])

    # Feature Alignment
    expected_features = list(model.feature_names_in_)
    extra_cols = [c for c in df.columns if c not in expected_features]
    if extra_cols:
        df.drop(columns=extra_cols, inplace=True)

    missing_cols = [c for c in expected_features if c not in df.columns]
    for col in missing_cols:
        df[col] = 0

    df = df[expected_features]

    try:
        with st.spinner("⚡ Running Deep AI Inspection..."):
            predictions = model.predict(df)

        labels = label_encoder.inverse_transform(predictions)
        result = df.copy()
        result["Prediction"] = labels

        # Metrics
        benign = int((result["Prediction"] == "BENIGN").sum())
        attack = int(len(result) - benign)
        total = int(len(result))
        security_score = round((benign / total) * 100, 2)

        st.markdown("<br>", unsafe_allow_html=True)

        # -------------------------------------------------
        # Threat Level Badge
        # -------------------------------------------------

        if security_score >= 95:
            status_box = '<div style="background: rgba(0, 230, 118, 0.15); border: 1px solid #00E676; color: #00E676; padding: 12px 20px; border-radius: 12px; display: inline-block; font-weight: bold; box-shadow: 0 0 15px rgba(0, 230, 118, 0.3);">🟢 THREAT LEVEL: LOW (SYSTEM SAFE)</div>'
        elif security_score >= 80:
            status_box = '<div style="background: rgba(255, 171, 0, 0.15); border: 1px solid #FFAB00; color: #FFAB00; padding: 12px 20px; border-radius: 12px; display: inline-block; font-weight: bold; box-shadow: 0 0 15px rgba(255, 171, 0, 0.3);">🟠 THREAT LEVEL: MEDIUM (ELEVATED RISK)</div>'
        else:
            status_box = '<div style="background: rgba(255, 23, 68, 0.15); border: 1px solid #FF1744; color: #FF1744; padding: 12px 20px; border-radius: 12px; display: inline-block; font-weight: bold; box-shadow: 0 0 15px rgba(255, 23, 68, 0.3);">🔴 THREAT LEVEL: CRITICAL (ATTACK DETECTED)</div>'

        st.markdown(status_box, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # -------------------------------------------------
        # 3D Metric Cards
        # -------------------------------------------------

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(f"""
                <div class="card-3d">
                    <div class="card-label">Total Traffic Packets</div>
                    <div class="card-value" style="color: #00E5FF;">{total:,}</div>
                </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
                <div class="card-3d">
                    <div class="card-label">Safe Benign Flow</div>
                    <div class="card-value" style="color: #00E676;">{benign:,}</div>
                </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
                <div class="card-3d">
                    <div class="card-label">Threat Anomalies</div>
                    <div class="card-value" style="color: #FF1744;">{attack:,}</div>
                </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
                <div class="card-3d">
                    <div class="card-label">Overall Security Score</div>
                    <div class="card-value" style="color: #FFD600;">{security_score}%</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # -------------------------------------------------
        # 3D Charts & Tab Analytics
        # -------------------------------------------------

        tab1, tab2 = st.tabs(["📊 3D Visual Analytics", "📋 Telemetry Inspection Data"])

        with tab1:
            left, right = st.columns(2)

            with left:
                # 3D Styled Donut Chart
                pie = go.Figure(data=[go.Pie(
                    labels=["BENIGN", "ATTACK"],
                    values=[benign, attack],
                    hole=0.6,
                    marker=dict(colors=["#00E676", "#FF1744"], line=dict(color="#080B12", width=3)),
                    textinfo="percent+label",
                    hoverinfo="label+value+percent"
                )])

                pie.update_layout(
                    title="Traffic Ratio Breakdown",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E0E6ED", family="Rajdhani", size=14),
                    showlegend=True,
                    margin=dict(t=40, b=20, l=20, r=20)
                )
                st.plotly_chart(pie, use_container_width=True)

            with right:
                # 3D Depth Styled Bar Chart
                bar = go.Figure(data=[go.Bar(
                    x=["BENIGN", "ATTACK"],
                    y=[benign, attack],
                    marker=dict(
                        color=["#00E676", "#FF1744"],
                        line=dict(color="#000", width=1.5)
                    ),
                    text=[f"{benign:,}", f"{attack:,}"],
                    textposition="auto"
                )])

                bar.update_layout(
                    title="Volume Distribution",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E0E6ED", family="Rajdhani", size=14),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
                    margin=dict(t=40, b=20, l=20, r=20)
                )
                st.plotly_chart(bar, use_container_width=True)

        with tab2:
            st.markdown("### 📄 Processed Feature Array")
            st.dataframe(result, use_container_width=True, height=350)

            st.download_button(
                label="📥 Export 3D Telemetry Report (CSV)",
                data=result.to_csv(index=False),
                file_name="3d_threat_predictions.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error("Prediction analysis encountered an error.")
        st.code(str(e))

# -------------------------------------------------
# Footer
# -------------------------------------------------

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #5A6978; font-family: Orbitron; font-size: 0.8rem; letter-spacing: 1px;'>"
    "🛡️ SOC 3D DETECTOR | ENGINEERED BY STAVAN MOHIRE"
    "</div>",
    unsafe_allow_html=True
)
