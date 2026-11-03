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

# -------------------------------------------------
# Load CICIDS Model
# -------------------------------------------------

from src.prediction import load_cicids_artifacts, CICIDS_FEATURE_NAMES

@st.cache_resource
def load_resources():
    model, label_encoder = load_cicids_artifacts()

    # Validate the model's 78-feature schema
    model_features = list(getattr(model, "feature_names_in_", []))

    if model_features != list(CICIDS_FEATURE_NAMES):
        raise ValueError("Model feature schema does not match CICIDS schema.")

    # Validate model output labels
    encoder_classes = set(map(str, label_encoder.classes_))

    if encoder_classes != {"ATTACK", "BENIGN"}:
        raise ValueError("Unexpected model label classes.")

    return model, label_encoder


try:
    model, label_encoder = load_resources()
except Exception:
    st.error(
        "The CICIDS model could not be loaded or validated. "
        "Please check that the model and label encoder files are available."
    )
    st.stop()
