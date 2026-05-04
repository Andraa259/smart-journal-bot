import streamlit as st
from groq import Groq
from Levenshtein import ratio
import requests
import re
import math

# 1. KONFIGURASI & UI STYLE
st.set_page_config(page_title="AI Humanizer Elite v3.2", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px !important; border-radius: 10px; }
    .metric-card {
        padding: 15px; border-radius: 12px; color: white;
        text-align: center; margin-bottom: 10px; font-weight: bold;
    }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. ALGORITMA STATISTIK LOKAL (ANTI-OFFLINE)
def local_statistical_check(text):
    """Mendeteksi sidik jari AI lewat variasi panjang kalimat (Burstiness)."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    
    if len(sentences) < 2:
        return 85.0 # Terlalu pendek, asumsikan pola AI standar
    
    # Hitung jumlah kata tiap kalimat
    lengths = [len(s.split()) for s in sentences]
    avg_len = sum(lengths) / len(lengths)
    
    # Hitung Standar Deviasi (Seberapa 'acak' panjang kalimatnya)
    variance = sum((x - avg_len) ** 2 for x in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    
    # Mapping: Manusia biasanya punya std_dev > 5. AI biasanya < 3.
    # Rumus: Semakin kecil std_dev, semakin mendekati 100% AI.
    score = 100 - (std_dev * 8.5) 
    return max(10.0, min(99.0, score))

# 3. KONEKSI API & DETEKTOR
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
HF_TOKEN = st.secrets["HF_API_KEY"]

def query_detector(text):
    """Cek Cloud dulu, kalau gagal pindah ke Lokal."""
    API_URL = "https://api-inference.huggingface.co/models/Suvash/deberta-v3-large-ai-detector"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        resp = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=8)
        if resp.status_code == 200:
            result = resp.json()
            for item in result[0]:
                if item['label'] == 'LABEL_0': return item['score'] * 100
        elif resp.status_code == 503: return "LOADING"
    except:
        pass
    
    # JALUR ALTERNATIF (LOGIKA MANUAL)
    return local_statistical_check(text)

def get_ai_response(text, style, major, temp, feedback=""):
    """Llama 3.3 melakukan rekonstruksi teks."""
    prompt = f"""Anda pakar {major}. Rekonstruksi teks ini ke gaya {style}.
    MISI: Hancurkan pola statistik AI dengan variasi panjang kalimat ekstrem dan diksi non-klise. 
    Jangan bertele-tele, pertahankan makna asli.{feedback}"""
    try:
        chat = client.chat.completions.create(
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            model="llama-3.3-70b-versatile", temperature=temp,
        )
        return chat.choices[0].message.content
    except: return text

# 4. DASHBOARD UTAMA
st.title("🛡️ AI Humanizer Elite v3.2")
st.caption("Andra's Workspace | IT & Psychology Multidisciplinary Tools")

with st.sidebar:
    st.header("⚙️ Settings")
    major = st.text_input("Jurusan:", "Psikologi & IT")
    style = st.selectbox("Gaya:", ["Kritis & Analitis", "Formal Akademik", "Naratif"])
    temp = st.slider("Kreativitas", 0.6, 1.0, 0.85)
    target = st.slider("Target Skor AI (%)", 5, 40, 20)

user_input = st.text_area("Input Teks AI:", height=150, placeholder="Tempel tulisan ChatGPT di sini...")

if st.button("🚀 Eksekusi Humanizing"):
    if user_input.strip():
        curr_text = user_input
        f_score = 100
        
        with st.spinner("Mencuci teks & menghancurkan pola AI..."):
            for i in range(2): # 2 Iterasi Optimasi
                fb = f"\nINFO: Teks sebelumnya masih {f_score:.1f}% AI. Ubah ritmenya!" if i > 0 else ""
                res = get_ai_response(curr_text, style, major, temp + (i*0.1), fb)
                score = query_detector(res)
                
                if isinstance(score, (int, float)):
                    f_score = score
                    if score <= target: break
                curr_text = res
                
        st.session_state['master'] = curr_text
        st.session_state['ai_score'] = f_score
    else: st.error("Teks kosong!")

# 5. EDITOR & METRIK VISUAL
if 'master' in st.session_state:
    st.divider()
    m_edit = st.text_area("🛠️ Master Editor (Edit untuk naikkan HIR):", 
                          value=st.session_state['master'], height=250)
    
    if st.button("🔍 Re-Scan Skor"):
        st.session_state['ai_score'] = query_detector(m_edit)

    # BARIS METRIK DENGAN WARNA DINAMIS
    c1, c2, c3 = st.columns(3)
    
    def get_color(val, is_ai=True):
        if val == "LOADING": return "#17a2b8"
        if is_ai: # Semakin rendah semakin hijau
            return "#28a745" if val < 25 else "#ffc107" if val < 55 else "#dc3545"
        return "#28a745" if val > 60 else "#ffc107" if val > 35 else "#dc3545"

    with c1:
        s = st.session_state['ai_score']
        color = get_color(s)
        disp = f"{s:.1f}%" if isinstance(s, (int, float)) else "LOADING"
        st.markdown(f'<div class="metric-card" style="background-color:{color}">AI DETECTOR<br><span style="font-size:1.5em">{disp}</span></div>', unsafe_allow_html=True)
    
    with c2:
        hir = min((1 - ratio(st.session_state['master'], m_edit)) * 400, 100.0)
        color = get_color(hir, False)
        st.markdown(f'<div class="metric-card" style="background-color:{color}">HIR SCORE<br><span style="font-size:1.5em">{hir:.1f}%</span></div>', unsafe_allow_html=True)
        
    with c3:
        char = len(m_edit)
        color = "#6c757d" if char <= 4096 else "#dc3545"
        st.markdown(f'<div class="metric-card" style="background-color:{color}">KARAKTER<br><span style="font-size:1.5em">{char} / 4096</span></div>', unsafe_allow_html=True)

    # 6. FINALISASI
    st.divider()
    st.code(m_edit, language=None)
    catatan = st.text_input("Label Telegram:", placeholder="Contoh: Tugas Akhir v1")
    
    if st.button("✈️ Kirim ke Telegram"):
        t, cid = st.secrets["TELEGRAM_BOT_TOKEN"], st.secrets["TELEGRAM_CHAT_ID"]
        s_rep = f"{st.session_state['ai_score']:.1f}%" if isinstance(st.session_state['ai_score'], (int, float)) else "N/A"
        msg = f"📩 **REPORT AI HUMANIZER**\n📌 {catatan}\n🤖 AI: {s_rep}\n📊 HIR: {hir:.1f}%\n\n{m_edit}"
        requests.post(f"https://api.telegram.org/bot{t}/sendMessage", data={"chat_id": cid, "text": msg, "parse_mode": "Markdown"})
        st.success("Terkirim!")
