import streamlit as st
from groq import Groq
from Levenshtein import ratio
import requests
import time

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="AI Humanizer Elite v3", layout="wide", page_icon="🛡️")

# CSS untuk Metrik Dinamis & UI
st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px !important; }
    .metric-card {
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 10px;
    }
    @media (max-width: 640px) { .stActionButton { width: 100%; } }
    </style>
    """, unsafe_allow_html=True)

# 2. INISIALISASI CLIENT & API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
HF_TOKEN = st.secrets["HF_API_KEY"]

def query_deberta(text):
    API_URL = "https://api-inference.huggingface.co/models/Duskfall77/deberta-v3-large-ai-detector"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=15)
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            for item in result[0]:
                if item['label'].upper() in ['AI', 'FAKE', 'LABEL_1']:
                    return item['score'] * 100
        return 0
    except:
        return None

def get_ai_response(text, style, major, temp, feedback_note=""):
    system_prompt = f"""
    Anda pakar parafrase {major}. Ubah teks ke gaya {style}.
    TUGAS: Rekonstruksi total teks agar lolos detektor AI DeBERTa-v3-Large.
    INSTRUKSI ANTI-AI:
    1. Acak struktur kalimat sepenuhnya. Gunakan Burstiness (variasi panjang kalimat).
    2. Pakai diksi unik (Perplexity tinggi) yang hanya digunakan pakar {major}.
    3. Hindari pengulangan kata dan transisi kaku.
    4. JANGAN menambah info baru, tetap ringkas.{feedback_note}
    """
    variations = []
    # Loop untuk 3 variasi
    for _ in range(3):
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
            model="llama-3.3-70b-versatile",
            temperature=temp,
        )
        variations.append(chat_completion.choices[0].message.content)
    return variations

def mix_ai_logic(selected_texts, major):
    combined = " --- ".join(selected_texts)
    prompt = f"Sintesiskan teks berikut menjadi satu paragraf bidang {major}. Pastikan alur natural, tidak redundan, dan hancurkan pola statistik AI. Tetap padat."
    chat_completion = client.chat.completions.create(
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": combined}],
        model="llama-3.3-70b-versatile",
        temperature=0.6,
    )
    return chat_completion.choices[0].message.content

# Fungsi UI untuk metrik berwarna
def colored_metric(label, value, is_ai_score=True):
    color = "#28a745" # Default Hijau
    
    if is_ai_score: # Logika untuk Detector AI (Rendah itu baik)
        if value > 50: color = "#dc3545" # Merah
        elif value > 20: color = "#ffc107; color: black;" # Kuning
    else: # Logika untuk HIR (Tinggi itu baik)
        if value < 30: color = "#dc3545" # Merah
        elif value < 60: color = "#ffc107; color: black;" # Kuning
    
    st.markdown(f"""
        <div class="metric-card" style="background-color: {color};">
            <div style="font-size: 0.9em; opacity: 0.9;">{label}</div>
            <div style="font-size: 1.8em; font-weight: bold;">{value:.1f}%</div>
        </div>
    """, unsafe_allow_html=True)

# 3. UI UTAMA
st.title("🛡️ AI Humanizer Elite v3")
st.caption("Auto-Optimization berdasarkan skor DeBERTa & Metrik HIR Dinamis.")

with st.sidebar:
    st.header("⚙️ Konfigurasi")
    major = st.text_input("Bidang Ilmu:", "Psikologi & IT")
    style = st.selectbox("Gaya Penulisan:", ["Kritis & Analitis", "Formal Akademik", "Naratif", "Ringkas"])
    temp = st.slider("Kreativitas (Temperature)", 0.6, 1.0, 0.85)
    st.divider()
    target_score = st.slider("Target Maksimal Skor AI (%)", 5, 40, 15)

user_input = st.text_area("Tempel Teks AI di sini:", height=150)

if st.button("🚀 Start Humanizing Process"):
    if user_input.strip():
        progress_bar = st.progress(0)
        status = st.empty()
        
        # PROSES AUTO-OPTIMISASI
        current_text = user_input
        final_score = 100
        best_variations = []
        
        for i in range(2): # Maksimal 2 iterasi optimasi otomatis
            status.text(f"🔄 Iterasi {i+1}: Rekonstruksi teks oleh Llama...")
            progress_bar.progress(25 if i==0 else 75)
            
            # Bot belajar dari skor sebelumnya
            feedback = f"\nPERINGATAN: Hasil sebelumnya terdeteksi {final_score:.1f}% AI. Tolong buat lebih manusiawi, acak struktur kalimatnya lebih berani!" if i > 0 else ""
            
            best_variations = get_ai_response(current_text, style, major, temp, feedback)
            candidate = best_variations[0]
            
            status.text(f"🔍 Iterasi {i+1}: Verifikasi dengan DeBERTa...")
            score = query_deberta(candidate)
            
            if score is not None:
                final_score = score
                if score <= target_score: # Berhenti jika sudah mencapai target
                    break
                current_text = candidate # Pakai hasil ini untuk dioptimalkan lagi di iterasi berikutnya
        
        progress_bar.progress(100)
        status.text("✅ Proses Optimasi Selesai!")
        
        st.session_state['results'] = best_variations
        st.session_state['ai_score'] = final_score
        st.session_state['master'] = best_variations[0]
    else:
        st.error("Teks belum diisi!")

# 4. TAHAP HASIL & EDITOR (DI MANA DETEKSI & HIR BEKERJA BERSAMA)
if 'results' in st.session_state:
    st.divider()
    
    st.subheader("📋 Pilih Variasi & Mix")
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

    # TOMBOL MIX
    if st.button("🪄 Mix & Rescan"):
        sel = [res[i] for i, s in enumerate([s1, s2, s3]) if s]
        if len(sel) >= 2:
            st.session_state['master'] = mix_ai_logic(sel, major)
            st.session_state['ai_score'] = query_deberta(st.session_state['master'])
        else: st.warning("Pilih minimal 2 variasi untuk di-mix!")

    st.divider()

    # MASTER EDITOR & METRIK BERWARNA
    st.subheader("🛠️ Master Editor")
    
    # Text area untuk edit manual
    final_text = st.text_area("Edit manual di sini untuk hasil maksimal:", 
                              value=st.session_state.get('master', ""), height=250)
    
    # Update deteksi manual jika user klik tombol (agar tidak boros API setiap ngetik)
    if st.button("🔍 Update Skor Deteksi"):
        with st.spinner("Memindai ulang..."):
            st.session_state['ai_score'] = query_deberta(final_text)

    # TAMPILAN METRIK DINAMIS (Warna menyesuaikan persen)
    col_met1, col_met2, col_met3 = st.columns(3)
    
    with col_met1:
        # Metrik Detector AI (Warna Otomatis)
        colored_metric("DeBERTa AI Score", st.session_state['ai_score'])
        
    with col_met2:
        # Metrik HIR (Warna Otomatis)
        hir_score = min((1 - ratio(st.session_state['master'], final_text)) * 300, 100.0)
        colored_metric("Human-Input Ratio", hir_score, is_ai_score=False)
        
    with col_met3:
        # Info Karakter
        char_count = len(final_text)
        status_color = "white" if char_count <= 4096 else "#dc3545"
        st.markdown(f"""
            <div class="metric-card" style="background-color: #6c757d; color: {status_color};">
                <div style="font-size: 0.9em; opacity: 0.9;">Karakter</div>
                <div style="font-size: 1.8em; font-weight: bold;">{char_count} / 4096</div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    # OUTPUT & TELEGRAM
    st.code(final_text, language=None)
    catatan = st.text_input("Judul/Catatan (untuk Telegram):", placeholder="Contoh: Tugas Psikologi Revisi")
    
    if st.button("✈️ Kirim ke Telegram"):
        if char_count <= 4096:
            token = st.secrets["TELEGRAM_BOT_TOKEN"]
            chat_id = st.secrets["TELEGRAM_CHAT_ID"]
            pesan = (f"📩 **LAPORAN HUMANIZER**\n"
                     f"📌 **Judul:** {catatan if catatan else '-'}\n"
                     f"🤖 **AI Score:** {st.session_state['ai_score']:.1f}%\n"
                     f"📊 **HIR Score:** {hir_score:.1f}%\n\n"
                     f"📝 **Teks:**\n{final_text}")
            
            res_tele = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                                     data={"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"})
            if res_tele.status_code == 200: st.success("Berhasil dikirim!")
            else: st.error("Gagal kirim.")
        else: st.error("Teks terlalu panjang!")
