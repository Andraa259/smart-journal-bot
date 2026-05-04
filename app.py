import streamlit as st
from groq import Groq
from Levenshtein import ratio
import requests
import re
import math

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="AI Humanizer Elite v4", layout="wide", page_icon="🛡️")

# CSS Kustom
st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px !important; }
    .metric-container { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; }
    @media (max-width: 640px) { .stActionButton { width: 100%; } }
    </style>
    """, unsafe_allow_html=True)

# 2. INISIALISASI CLIENT
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- ALGORITMA AI DETECTOR INTERNAL ---
def internal_ai_detector(text):
    if not text or len(text.split()) < 10:
        return 0.0
    
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    
    if len(sentences) < 2:
        return 85.0 # AI biasanya sangat pendek dan kaku
    
    # 1. Burstiness (Variasi panjang kalimat)
    lengths = [len(s.split()) for s in sentences]
    avg_length = sum(lengths) / len(lengths)
    variance = sum((x - avg_length) ** 2 for x in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    
    # 2. Perplexity Sederhana (Variasi Kata Unik)
    words = text.lower().split()
    unique_ratio = len(set(words)) / len(words)
    
    # Kalkulasi Skor (0-100)
    # AI cenderung punya std_dev rendah (seragam) dan unique_ratio menengah
    burstiness_score = max(0, 100 - (std_dev * 8)) 
    complexity_score = max(0, 100 - (unique_ratio * 120))
    
    final_score = (burstiness_score * 0.7) + (complexity_score * 0.3)
    return min(max(final_score, 5.0), 99.0)

# --- CORE LOGIC ---
def get_ai_response(text, style, major, temp, instruction=""):
    system_prompt = f"""
    Anda pakar penulisan {major}. Ubah teks ke gaya {style}.
    ATURAN ANTI-AI:
    1. Hancurkan pola statistik dengan mengacak panjang kalimat (Burstiness).
    2. Gunakan diksi manusiawi, hindari kata robotik seperti 'signifikan', 'implementasi'.
    3. Masukkan nuansa opini/analisis tajam.
    {instruction}
    """
    variations = []
    for _ in range(3):
        chat = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
            model="llama-3.3-70b-versatile",
            temperature=temp,
        )
        variations.append(chat.choices[0].message.content)
    return variations

# 3. UI UTAMA
st.title("🛡️ AI Humanizer: Elite Edition")

with st.sidebar:
    st.header("⚙️ Konfigurasi")
    major = st.text_input("Jurusan:", "Psikologi & IT")
    style = st.selectbox("Gaya:", ["Formal Akademik", "Kritis & Tajam", "Naratif", "Percakapan Santai"])
    temp = st.slider("Kreativitas", 0.5, 1.0, 0.85)

user_input = st.text_area("Tempel Teks AI Asli:", height=150)

if st.button("🚀 Buat 3 Variasi"):
    if user_input.strip():
        with st.spinner("Menganalisis dan meracik..."):
            st.session_state['results'] = get_ai_response(user_input, style, major, temp)
    else:
        st.error("Isi teks dulu!")

# 4. TAHAP VARIASI & MIXING
if 'results' in st.session_state:
    st.subheader("📋 Hasil Variasi")
    res = st.session_state['results']
    
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        s1 = st.checkbox("Pilih Var 1", value=True)
        st.info(res[0])
    with col_v2:
        s2 = st.checkbox("Pilih Var 2")
        st.info(res[1])
    with col_v3:
        s3 = st.checkbox("Pilih Var 3")
        st.info(res[2])

    st.divider()
    
    if st.button("🪄 Mix Pilihan"):
        selected = [res[i] for i, sel in enumerate([s1, s2, s3]) if sel]
        if len(selected) >= 2:
            st.session_state['master'] = get_ai_response(" --- ".join(selected), style, major, 0.7, "Gabungkan teks ini menjadi satu paragraf padat dan eliminasi redundansi.")[0]
        else:
            st.warning("Pilih minimal 2 variasi!")

    st.divider()

    # 5. MASTER EDITOR & DETECTOR
    st.subheader("🛠️ Master Editor")
    final_text = st.text_area("Edit manual di sini:", value=st.session_state.get('master', ""), height=250)

    # --- INTERNAL DETECTOR UI ---
    ai_prob = internal_ai_detector(final_text)
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.write("📊 **AI Detection Score**")
        color = "red" if ai_prob > 60 else "orange" if ai_prob > 30 else "green"
        st.markdown(f"<h2 style='color:{color};'>{ai_prob:.1f}%</h2>", unsafe_allow_html=True)
        st.progress(ai_prob / 100)
        st.caption("Semakin tinggi %, semakin terdeteksi seperti AI.")

    with col_m2:
        if 'master' in st.session_state:
            hir_score = min((1 - ratio(st.session_state['master'], final_text)) * 250, 100.0)
            st.write("👤 **Human-Input Ratio (HIR)**")
            st.markdown(f"<h2>{hir_score:.1f}%</h2>", unsafe_allow_html=True)
            st.progress(hir_score / 100)
    
    # Tombol Optimalisasi (Auto-Drop AI Score)
    if st.button("✨ Optimalisasi (Turunkan Skor AI)"):
        with st.spinner("Menghancurkan pola AI..."):
            opt_instruction = "RE-WRITE teks ini secara drastis. Gunakan struktur kalimat yang acak (pendek-panjang), gunakan kosa kata tidak umum, dan pastikan tidak ada pengulangan kata di awal kalimat."
            st.session_state['master'] = get_ai_response(final_text, style, major, 0.95, opt_instruction)[0]
            st.rerun()

    st.divider()

    # 6. SENDING
    st.code(final_text, language=None)
    catatan_user = st.text_input("Catatan untuk Telegram:")
    
    if st.button("✈️ Kirim ke Telegram"):
        if final_text.strip() and len(final_text) <= 4096:
            token, cid = st.secrets["TELEGRAM_BOT_TOKEN"], st.secrets["TELEGRAM_CHAT_ID"]
            header = f"📌 **JUDUL:** {catatan_user if catatan_user else '-'}\n"
            stats = f"🤖 **AI Score:** {ai_prob:.1f}% | 📊 **HIR:** {hir_score:.1f}%\n"
            payload = {"chat_id": cid, "text": f"📩 **HUMANIZER RESULT**\n\n{header}{stats}\n📝 **TEKS:**\n{final_text}", "parse_mode": "Markdown"}
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=payload)
            st.success("Terkirim!")
