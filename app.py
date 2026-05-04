import streamlit as st
from groq import Groq
from Levenshtein import ratio
import requests
import re
import math
import time

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="AI Humanizer: Elite Mixer", layout="wide", page_icon="🛡️")

# CSS UNTUK UI DINAMIS (Background Metrik berwarna)
st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px !important; }
    .metric-card {
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 10px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    @media (max-width: 640px) { .stActionButton { width: 100%; } }
    </style>
    """, unsafe_allow_html=True)

# 2. INISIALISASI CLIENT & API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
HF_TOKEN = st.secrets["HF_API_KEY"]

# --- ALGORITMA 1: LOCAL STATISTICAL DETECTOR (Burstiness) ---
def local_detector_logic(text):
    """Menghitung skor AI berdasarkan variasi panjang kalimat."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if len(sentences) < 2: return 50.0
    
    lengths = [len(s.split()) for s in sentences]
    avg_length = sum(lengths) / len(lengths)
    variance = sum((x - avg_length) ** 2 for x in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    
    # Manusia biasanya std_dev > 8. AI biasanya < 4.
    ai_score = 100 - (std_dev * 8.5)
    return max(5.0, min(98.0, ai_score))

# --- ALGORITMA 2: CLOUD AI DETECTOR (DeBERTa-v3) ---
def query_cloud_detector(text):
    """Memanggil model DeBERTa di Hugging Face."""
    API_URL = "https://api-inference.huggingface.co/models/Suvash/deberta-v3-large-ai-detector"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=12)
        if response.status_code == 503: return "LOADING"
        if response.status_code == 200:
            result = response.json()
            for item in result[0]:
                if item['label'] == 'LABEL_0': # LABEL_0 = Fake/AI
                    return item['score'] * 100
        return None
    except:
        return None

# --- CORE ENGINE (PROMPTS) ---
def get_ai_response(text, style, major, temp):
    system_prompt = f"""
    Anda adalah pakar penulisan kreatif di bidang {major}. 
    TUGAS: Lakukan rekonstruksi total teks berikut menjadi gaya {style}.
    ATURAN ANTI-DETEKSI AI:
    1. RESTRUKTURISASI RADIKAL: Ubah susunan gagasan. Mulailah kalimat dari titik tengah atau akhir.
    2. VARIABEL BURSTINESS: Campurkan kalimat pendek (3-5 kata) dengan kalimat kompleks.
    3. TINGKATKAN PERPLEXITY: Gunakan diksi Bahasa Indonesia yang kaya dan tidak pasaran.
    4. GAYA MANUSIA: Sisipkan nuansa opini atau penekanan unik.
    5. JANGAN menambah informasi palsu.
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

def mix_ai_logic(selected_texts, major):
    combined = " --- ".join(selected_texts)
    prompt = f"""
    Sintesiskan teks-teks berikut menjadi satu narasi tunggal yang sangat kohesif untuk bidang {major}.
    KRITERIA KUALITAS MANUSIA:
    1. Pastikan teks memiliki 'suara' yang konsisten tapi tidak monoton.
    2. Hancurkan pola repetitif AI.
    3. Gunakan konjungsi antar-kalimat yang natural.
    4. Pastikan teks akhir terasa padat dan tidak bertele-tele.
    """
    chat = client.chat.completions.create(
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": combined}],
        model="llama-3.3-70b-versatile",
        temperature=0.7,
    )
    return chat.choices[0].message.content

# --- UI UTILS ---
def colored_metric(label, value, is_ai=True):
    """Menampilkan card berwarna menyesuaikan persentase."""
    if value == "LOADING":
        color, val_text = "#17a2b8", "LOADING..."
    elif value is None:
        color, val_text = "#6c757d", "OFFLINE"
    else:
        val_text = f"{value:.1f}%"
        if is_ai: # AI Score: Rendah itu Hijau
            color = "#28a745" if value < 25 else "#ffc107; color:black;" if value < 50 else "#dc3545"
        else: # HIR Score: Tinggi itu Hijau
            color = "#dc3545" if value < 30 else "#ffc107; color:black;" if value < 60 else "#28a745"
            
    st.markdown(f"""
        <div class="metric-card" style="background-color: {color};">
            <div style="font-size: 0.9em; opacity: 0.8;">{label}</div>
            <div style="font-size: 1.8em; font-weight: bold;">{val_text}</div>
        </div>
    """, unsafe_allow_html=True)

def send_telegram(text, hir, ai_score, catatan):
    token = st.secrets["TELEGRAM_BOT_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    msg = (f"📩 **HASIL AI HUMANIZER**\n"
           f"📌 **JUDUL:** {catatan if catatan else '-'}\n"
           f"📊 **HIR:** {hir:.1f}%\n"
           f"🤖 **AI Score:** {ai_score if isinstance(ai_score, str) else f'{ai_score:.1f}%'}\n\n"
           f"📝 **TEKS:**\n{text}")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return requests.post(url, data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

# 3. UI UTAMA
st.title("🛡️ AI Humanizer: Elite Mixer Edition")

with st.sidebar:
    st.header("⚙️ Konfigurasi")
    major = st.text_input("Jurusan:", "Psikologi & IT")
    style = st.selectbox("Gaya:", ["Kritis & Tajam", "Formal Akademik", "Naratif", "Percakapan Santai"])
    temp = st.slider("Kreativitas", 0.5, 1.0, 0.8)
    st.divider()
    st.info("Sistem menggunakan Hybrid Detector (Cloud + Local Statistical Analysis)")

user_input = st.text_area("Tempel Teks AI Asli:", height=180)

if st.button("🚀 Buat 3 Variasi"):
    if user_input.strip():
        with st.spinner("Meracik variasi & Memindai skor..."):
            st.session_state['results'] = get_ai_response(user_input, style, major, temp)
            # Scan skor awal
            cloud_score = query_cloud_detector(st.session_state['results'][0])
            st.session_state['ai_score'] = cloud_score if cloud_score else local_detector_logic(st.session_state['results'][0])
    else:
        st.error("Isi teks dulu!")

# 4. TAHAP VARIASI & MIXING
if 'results' in st.session_state:
    st.subheader("📋 Hasil Variasi")
    res = st.session_state['results']
    
    c_v1, c_v2, c_v3 = st.columns(3)
    with c_v1:
        s1 = st.checkbox("Pilih Var 1", value=True)
        st.info(res[0])
    with c_v2:
        s2 = st.checkbox("Pilih Var 2")
        st.info(res[1])
    with c_v3:
        s3 = st.checkbox("Pilih Var 3")
        st.info(res[2])

    st.divider()
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🪄 Mix Pilihan"):
            selected = [res[i] for i, sel in enumerate([s1, s2, s3]) if sel]
            if len(selected) >= 2:
                with st.spinner("Menggabungkan..."):
                    st.session_state['master'] = mix_ai_logic(selected, major)
                    # Rescan skor
                    c_score = query_cloud_detector(st.session_state['master'])
                    st.session_state['ai_score'] = c_score if c_score else local_detector_logic(st.session_state['master'])
            else: st.warning("Pilih minimal 2!")
                
    with col_btn2:
        if st.button("🤖 Auto-Mix Semua"):
            with st.spinner("Mixing otomatis..."):
                st.session_state['master'] = mix_ai_logic(res, major)
                c_score = query_cloud_detector(st.session_state['master'])
                st.session_state['ai_score'] = c_score if c_score else local_detector_logic(st.session_state['master'])

    st.divider()

    # 5. MASTER EDITOR & METRIK
    st.subheader("🛠️ Master Editor")
    final_text = st.text_area("Sentuhan Akhir (HIR akan berubah otomatis):", 
                              value=st.session_state.get('master', ""), height=300)

    if st.button("🔍 Update Skor Deteksi"):
        with st.spinner("Memindai ulang..."):
            c_score = query_cloud_detector(final_text)
            st.session_state['ai_score'] = c_score if c_score else local_detector_logic(final_text)

    # BARIS METRIK BERWARNA
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        colored_metric("DeBERTa AI Score", st.session_state.get('ai_score'))
        
    with col_m2:
        hir = min((1 - ratio(st.session_state.get('master', final_text), final_text)) * 400, 100.0) if st.session_state.get('master') else 0
        colored_metric("Human-Input Ratio (HIR)", hir, is_ai=False)
        
    with col_m3:
        char_count = len(final_text)
        status_c = "#6c757d" if char_count <= 4096 else "#dc3545"
        st.markdown(f'<div class="metric-card" style="background-color:{status_c}">Karakter<br><b>{char_count} / 4096</b></div>', unsafe_allow_html=True)

    st.divider()

    # 6. FINALISASI
    st.subheader("📤 Output")
    st.code(final_text, language=None)
    
    catatan = st.text_input("Judul/Catatan (Telegram):", placeholder="Contoh: Revisi Bab 1")
    
    if st.button("✈️ Kirim ke Telegram"):
        if final_text.strip() and char_count <= 4096:
            with st.spinner("Mengirim..."):
                resp = send_telegram(final_text, hir, st.session_state['ai_score'], catatan)
                if resp.status_code == 200: st.success("Terkirim!")
                else: st.error("Gagal! Cek konfigurasi.")
        else: st.error("Cek teks atau panjang karakter!")
