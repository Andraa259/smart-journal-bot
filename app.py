import streamlit as st
from groq import Groq
from Levenshtein import ratio
import requests
import re
import math
import time

# 1. KONFIGURASI & STYLE
st.set_page_config(page_title="AI Humanizer Elite v3.1", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px !important; }
    .metric-card {
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    @media (max-width: 640px) { .stActionButton { width: 100%; } }
    </style>
    """, unsafe_allow_html=True)

# 2. ALGORITMA DETEKSI LOKAL (BURSTINESS)
def local_detector_logic(text):
    """
    Menghitung skor AI berdasarkan variasi statistik panjang kalimat.
    Rumus: Semakin rendah Standar Deviasi (sigma), semakin besar kemungkinan AI.
    """
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    
    if len(sentences) < 2:
        return 50.0 # Data tidak cukup
    
    lengths = [len(s.split()) for s in sentences]
    avg_length = sum(lengths) / len(lengths)
    
    # Kalkulasi Variance & Standar Deviasi
    # LaTeX: \sigma = \sqrt{\frac{\sum (x - \bar{x})^2}{n}}
    variance = sum((x - avg_length) ** 2 for x in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    
    # Pemetaan ke Skor AI: Manusia biasanya punya std_dev > 7
    ai_score = 100 - (std_dev * 10) 
    return max(5.0, min(99.0, ai_score))

# 3. KONEKSI API & CLOUD DETECTOR
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
HF_TOKEN = st.secrets["HF_API_KEY"]

def query_cloud_detector(text):
    """Memanggil DeBERTa-v3-Large di Hugging Face."""
    API_URL = "https://api-inference.huggingface.co/models/Suvash/deberta-v3-large-ai-detector"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=12)
        if response.status_code == 503: return "LOADING"
        if response.status_code == 200:
            result = response.json()
            for item in result[0]:
                if item['label'] == 'LABEL_0': # LABEL_0 = AI Generated
                    return item['score'] * 100
        return None
    except:
        return None

def get_ai_response(text, style, major, temp, feedback=""):
    """Llama 3.3 Reconstruction Engine."""
    system_prompt = f"""
    Anda pakar penulisan {major}. Rekonstruksi total teks ini ke gaya {style}.
    TUGAS UTAMA: Hancurkan pola statistik AI (Perplexity & Burstiness).
    1. Pakai kalimat yang panjang-pendeknya sangat bervariasi.
    2. Gunakan diksi cerdas, jangan klise/robotik.
    3. Ubah struktur gagasan, jangan hanya ganti sinonim.
    {feedback}
    """
    try:
        chat = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
            model="llama-3.3-70b-versatile",
            temperature=temp,
        )
        return chat.choices[0].message.content
    except:
        return text

# 4. UI COMPONENTS
def colored_card(label, value, is_ai=True):
    """Menampilkan card metrik dengan warna dinamis sesuai persentase."""
    if value == "LOADING":
        color, text_val = "#17a2b8", "LOADING..."
    elif value is None:
        color, text_val = "#6c757d", "OFFLINE"
    else:
        text_val = f"{value:.1f}%"
        if is_ai: # AI Score: Rendah = Hijau
            color = "#28a745" if value < 25 else "#ffc107; color:black;" if value < 50 else "#dc3545"
        else: # HIR Score: Tinggi = Hijau
            color = "#dc3545" if value < 30 else "#ffc107; color:black;" if value < 60 else "#28a745"
            
    st.markdown(f"""
        <div class="metric-card" style="background-color: {color};">
            <div style="font-size: 0.9em; opacity: 0.8;">{label}</div>
            <div style="font-size: 1.8em; font-weight: bold;">{text_val}</div>
        </div>
    """, unsafe_allow_html=True)

# 5. MAIN APP INTERFACE
st.title("🛡️ AI Humanizer Elite v3.1")
st.caption("Multidisciplinary IT-Psychology Tool | Surabaya 2026")

with st.sidebar:
    st.header("⚙️ Settings")
    major = st.text_input("Jurusan/Bidang:", "Psikologi & IT")
    style = st.selectbox("Style:", ["Kritis & Analitis", "Formal Akademik", "Naratif", "Santai"])
    temp = st.slider("Creativity", 0.6, 1.0, 0.85)
    st.divider()
    target_ai = st.slider("Target AI Score (%)", 5, 40, 20)

user_input = st.text_area("Tempel Teks AI di sini:", height=150)

if st.button("🚀 Start Deep Humanizing"):
    if user_input.strip():
        progress = st.progress(0)
        status = st.empty()
        
        current_text = user_input
        final_ai_score = 100
        
        # Feedback Loop Logic
        for i in range(2):
            status.text(f"Iterasi {i+1}: Rekonstruksi Kalimat...")
            progress.progress(30 if i==0 else 70)
            
            # Tambahkan feedback jika iterasi kedua
            fb = f"\nINFO: Teks sebelumnya terdeteksi {final_ai_score:.1f}% AI. Ganti struktur kalimatnya lebih radikal!" if i > 0 else ""
            
            humanized = get_ai_response(current_text, style, major, temp + (i*0.1), fb)
            
            # Cek Skor Cloud dulu
            score = query_cloud_detector(humanized)
            if score is None or score == "LOADING":
                # Fallback ke Algoritma Lokal
                score = local_detector_logic(humanized)
                
            final_ai_score = score
            current_text = humanized
            if isinstance(score, (int, float)) and score <= target_ai: break
        
        progress.progress(100)
        status.text("✅ Selesai!")
        
        st.session_state['master'] = current_text
        st.session_state['ai_score'] = final_ai_score
    else:
        st.error("Isi teks dulu, Andra!")

# 6. EDITOR & MONITORING
if 'master' in st.session_state:
    st.divider()
    
    # Master Editor
    final_edit = st.text_area("🛠️ Master Editor (Edit manual untuk naikkan HIR):", 
                              value=st.session_state['master'], height=280)
    
    if st.button("🔍 Re-Scan Skor"):
        with st.spinner("Memindai ulang..."):
            score = query_cloud_detector(final_edit)
            st.session_state['ai_score'] = score if score else local_detector_logic(final_edit)

    # Metrics Row
    c1, c2, c3 = st.columns(3)
    with c1:
        colored_card("DeBERTa AI Score", st.session_state['ai_score'])
    with c2:
        # HIR Calculation
        hir = min((1 - ratio(st.session_state['master'], final_edit)) * 400, 100.0)
        colored_card("Human-Input Ratio", hir, is_ai=False)
    with c3:
        char_count = len(final_edit)
        char_color = "#6c757d" if char_count <= 4096 else "#dc3545"
        st.markdown(f'<div class="metric-card" style="background-color:{char_color}">Char Count<br><b>{char_count} / 4096</b></div>', unsafe_allow_html=True)

    st.divider()
    
    # Telegram & Final Output
    st.code(final_edit, language=None)
    catatan = st.text_input("Label/Catatan Telegram:", placeholder="Contoh: Revisi Tugas Akhir")
    
    if st.button("✈️ Kirim ke Telegram"):
        if char_count <= 4096:
            token, cid = st.secrets["TELEGRAM_BOT_TOKEN"], st.secrets["TELEGRAM_CHAT_ID"]
            ai_val = f"{st.session_state['ai_score']:.1f}%" if isinstance(st.session_state['ai_score'], (int, float)) else "N/A"
            
            msg = (f"📩 **LAPORAN AI HUMANIZER**\n"
                   f"📌 **Judul:** {catatan if catatan else '-'}\n"
                   f"🤖 **AI Score:** {ai_val}\n"
                   f"📊 **HIR Score:** {hir:.1f}%\n\n"
                   f"📝 **Teks:**\n{final_edit}")
            
            try:
                res = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                                    data={"chat_id": cid, "text": msg, "parse_mode": "Markdown"})
                if res.status_code == 200: st.success("Terkirim!")
                else: st.error("Gagal kirim.")
            except: st.error("Error Koneksi Telegram.")
        else:
            st.error("Teks kepanjangan!")
