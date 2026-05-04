import streamlit as st
from groq import Groq
from Levenshtein import ratio
import requests
import re
import math

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="AI Humanizer Elite v4.1", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px !important; }
    .metric-container { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; }
    @media (max-width: 640px) { .stActionButton { width: 100%; } }
    </style>
    """, unsafe_allow_html=True)

# 2. INISIALISASI CLIENT
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- ALGORITMA AI DETECTOR INTERNAL (STATISTIK LOKAL) ---
def internal_ai_detector(text):
    if not text or len(text.split()) < 5:
        return 0.0
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 2]
    if len(sentences) < 2:
        return 85.0
    
    lengths = [len(s.split()) for s in sentences]
    avg_length = sum(lengths) / len(lengths)
    variance = sum((x - avg_length) ** 2 for x in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    
    words = text.lower().split()
    unique_ratio = len(set(words)) / len(words)
    
    # Skor: Semakin kaku/seragam panjang kalimat, semakin tinggi skor AI
    burstiness_score = max(0, 100 - (std_dev * 10)) 
    complexity_score = max(0, 100 - (unique_ratio * 130))
    
    return min(max((burstiness_score * 0.7) + (complexity_score * 0.3), 5.0), 99.0)

# --- CORE LOGIC (FIX LENGTH) ---
def get_ai_response(text, style, major, temp, extra_inst=""):
    word_count = len(text.split())
    
    # Prompt memaksa panjang hasil agar sesuai dengan input
    system_prompt = f"""
    Anda pakar bahasa {major}. Ubah teks ke gaya {style}.
    ATURAN KETAT PANJANG TEKS:
    1. Hasil HARUS memiliki panjang sekitar {word_count} kata (toleransi +/- 10%).
    2. JANGAN menambah penjelasan tambahan atau basa-basi.
    3. Jika input adalah 1 paragraf pendek, hasil HARUS tetap 1 paragraf pendek.
    4. Fokus pada perubahan struktur kalimat dan diksi unik untuk mengelabui detektor AI.
    5. Tingkatkan Burstiness (acak panjang kalimat di dalam teks tersebut).
    {extra_inst}
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
st.title("🛡️ AI Humanizer: Compact Edition")
st.caption("Hasil variasi otomatis menyesuaikan panjang input asli.")

with st.sidebar:
    st.header("⚙️ Pengaturan")
    major = st.text_input("Jurusan:", "Psikologi & IT")
    style = st.selectbox("Gaya:", ["Kritis & Tajam", "Formal Akademik", "Naratif", "Ringkas"])
    temp = st.slider("Kreativitas", 0.5, 1.0, 0.85)

user_input = st.text_area("Tempel Teks AI Asli:", height=150)

if st.button("🚀 Buat 3 Variasi"):
    if user_input.strip():
        with st.spinner("Memproses variasi yang presisi..."):
            st.session_state['results'] = get_ai_response(user_input, style, major, temp)
    else:
        st.error("Input masih kosong!")

# 4. TAHAP VARIASI
if 'results' in st.session_state:
    st.subheader("📋 Variasi (Sesuai Panjang Input)")
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

    if st.button("🪄 Mix & Ringkas"):
        selected = [res[i] for i, sel in enumerate([s1, s2, s3]) if sel]
        if len(selected) >= 2:
            inst = "Gabungkan teks ini. JANGAN menambah panjang teks. Buat sepadat mungkin."
            st.session_state['master'] = get_ai_response(" --- ".join(selected), style, major, 0.7, inst)[0]
        else:
            st.warning("Pilih minimal 2!")

    st.divider()

    # 5. MASTER EDITOR & AI DETECTOR
    st.subheader("🛠️ Master Editor")
    final_text = st.text_area("Final Edit:", value=st.session_state.get('master', ""), height=200)

    ai_prob = internal_ai_detector(final_text)
    
    c1, c2 = st.columns(2)
    with c1:
        st.write("**AI Probability Score**")
        color = "red" if ai_prob > 60 else "orange" if ai_prob > 30 else "green"
        st.markdown(f"<h2 style='color:{color};'>{ai_prob:.1f}%</h2>", unsafe_allow_html=True)
        st.progress(ai_prob / 100)

    with c2:
        if 'master' in st.session_state:
            hir_score = min((1 - ratio(st.session_state['master'], final_text)) * 250, 100.0)
            st.write("**Human-Input Ratio (HIR)**")
            st.markdown(f"<h2>{hir_score:.1f}%</h2>", unsafe_allow_html=True)
            st.progress(hir_score / 100)

    if st.button("✨ Optimalisasi Skor AI"):
        with st.spinner("Menurunkan skor AI tanpa menambah kata..."):
            inst = "Hancurkan pola AI. Pakai kalimat acak. JANGAN menambah jumlah kata."
            st.session_state['master'] = get_ai_response(final_text, style, major, 0.95, inst)[0]
            st.rerun()

    st.divider()

    # 6. OUTPUT & TELEGRAM
    st.code(final_text, language=None)
    catatan = st.text_input("Judul untuk Telegram:")
    
    if st.button("✈️ Kirim ke Telegram"):
        if final_text.strip() and len(final_text) <= 4096:
            token, cid = st.secrets["TELEGRAM_BOT_TOKEN"], st.secrets["TELEGRAM_CHAT_ID"]
            stats = f"🤖 AI: {ai_prob:.1f}% | 📊 HIR: {hir_score:.1f}%"
            payload = {"chat_id": cid, "text": f"📩 **FINAL RESULT**\n📌 {catatan}\n{stats}\n\n{final_text}", "parse_mode": "Markdown"}
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=payload)
            st.success("Terkirim!")
