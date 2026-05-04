import streamlit as st
from groq import Groq
from Levenshtein import ratio
import requests
import time

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="AI Humanizer Elite v3", layout="wide", page_icon="🛡️")

# CSS untuk UI Mobile, Metrik Dinamis, dan Area Teks
st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px !important; }
    .metric-card {
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 10px;
        font-family: sans-serif;
    }
    .stInfo { background-color: #f8f9fa; border-left: 5px solid #007bff; }
    @media (max-width: 640px) { .stActionButton { width: 100%; } }
    </style>
    """, unsafe_allow_html=True)

# 2. INISIALISASI CLIENT & API
# Pastikan secrets sudah diatur di Dashboard Streamlit
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
HF_TOKEN = st.secrets["HF_API_KEY"]

def query_deberta(text):
    """Memanggil model DeBERTa-v3-Large via Hugging Face Inference API."""
    API_URL = "https://api-inference.huggingface.co/models/Duskfall77/deberta-v3-large-ai-detector"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        # Timeout ditambahkan untuk menangani cold start
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=20)
        result = response.json()
        
        # Jika model sedang loading (Cold Start)
        if isinstance(result, dict) and "estimated_time" in result:
            st.warning(f"Model sedang loading... Siap dalam {result['estimated_time']:.0f} detik.")
            return None
            
        if isinstance(result, list) and len(result) > 0:
            for item in result[0]:
                if item['label'].upper() in ['AI', 'FAKE', 'LABEL_1']:
                    return item['score'] * 100
        return 0
    except Exception as e:
        return None

def get_ai_response(text, style, major, temp, feedback_note=""):
    """Memanggil Llama 3.3 via Groq dengan instruksi anti-deteksi."""
    system_prompt = f"""
    Anda pakar penulisan kreatif dan akademis di bidang {major}.
    TUGAS: Lakukan rekonstruksi total teks agar lolos detektor AI (DeBERTa/Copyleaks).
    
    ATURAN ANTI-DETEKSI:
    1. RESTRUKTURISASI RADIKAL: Jangan hanya ganti sinonim. Ubah alur gagasan kalimat.
    2. VARIABEL BURSTINESS: Campurkan kalimat pendek dengan kalimat kompleks berstruktur unik.
    3. TINGKATKAN PERPLEXITY: Gunakan diksi Bahasa Indonesia yang cerdas, idiomatis, dan tidak pasaran.
    4. GAYA MANUSIA: Hindari transisi kaku seperti 'Selain itu' atau 'Secara signifikan'.
    5. PERTAHANKAN MAKNA: Jangan menambah informasi palsu, tetap padat dan efisien.
    {feedback_note}
    """
    
    variations = []
    for _ in range(3):
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
                model="llama-3.3-70b-versatile",
                temperature=temp,
            )
            variations.append(chat_completion.choices[0].message.content)
        except Exception as e:
            variations.append(f"Error calling Groq: {str(e)}")
    return variations

def mix_ai_logic(selected_texts, major):
    """Menggabungkan beberapa variasi menjadi satu teks utuh."""
    combined = " --- ".join(selected_texts)
    prompt = f"Sintesiskan teks berikut menjadi satu paragraf bidang {major}. Pastikan alur sangat natural, hancurkan pola statistik AI, dan pastikan tidak redundan."
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": combined}],
            model="llama-3.3-70b-versatile",
            temperature=0.6,
        )
        return chat_completion.choices[0].message.content
    except:
        return selected_texts[0]

def colored_metric(label, value, is_ai_score=True):
    """Menampilkan metrik dengan latar belakang warna dinamis."""
    if value is None:
        color = "#6c757d" # Abu-abu jika offline
        display_text = "OFFLINE"
    else:
        display_text = f"{value:.1f}%"
        if is_ai_score:
            if value > 50: color = "#dc3545" # Merah (Bahaya)
            elif value > 20: color = "#ffc107; color: black;" # Kuning (Waspada)
            else: color = "#28a745" # Hijau (Aman)
        else:
            if value < 30: color = "#dc3545" # Merah (Perubahan Sedikit)
            elif value < 60: color = "#ffc107; color: black;" # Kuning (Menengah)
            else: color = "#28a745" # Hijau (Perubahan Banyak)
    
    st.markdown(f"""
        <div class="metric-card" style="background-color: {color};">
            <div style="font-size: 0.85em; opacity: 0.9;">{label}</div>
            <div style="font-size: 1.7em; font-weight: bold;">{display_text}</div>
        </div>
    """, unsafe_allow_html=True)

# 3. UI UTAMA
st.title("🛡️ AI Humanizer Elite v3")
st.caption(f"Andra's Professional Workspace | Surabaya, 2026")

with st.sidebar:
    st.header("⚙️ Konfigurasi")
    major = st.text_input("Bidang Ilmu:", "Psikologi & IT")
    style = st.selectbox("Gaya Penulisan:", ["Kritis & Tajam", "Formal Akademik", "Naratif", "Ringkas & Padat"])
    temp = st.slider("Kreativitas (Temperature)", 0.5, 1.0, 0.85)
    st.divider()
    target_score = st.slider("Target Maksimal Skor AI (%)", 5, 40, 20)
    st.info("Sistem akan melakukan iterasi otomatis jika skor masih di atas target.")

user_input = st.text_area("Tempel Teks AI di sini (ChatGPT/Claude/Lainnya):", height=180)

if st.button("🚀 Start Deep Humanizing"):
    if user_input.strip():
        progress_bar = st.progress(0)
        status = st.empty()
        
        current_text = user_input
        final_score = 100
        best_variations = []
        current_temp = temp
        
        # FEEDBACK LOOP (Iterasi Otomatis)
        for i in range(2):
            status.text(f"🔄 Iterasi {i+1}: Rekonstruksi oleh Llama 3.3...")
            progress_bar.progress(25 if i==0 else 75)
            
            # Berikan feedback ke AI jika skor masih tinggi
            fb_note = ""
            if i > 0 and (final_score is not None and final_score > 40):
                current_temp = min(current_temp + 0.1, 1.0)
                fb_note = f"\nCATATAN: Hasil sebelumnya masih terdeteksi {final_score:.1f}% AI. Tolong hancurkan pola kalimatnya lebih ekstrem lagi!"
            
            best_variations = get_ai_response(current_text, style, major, current_temp, fb_note)
            candidate = best_variations[0]
            
            status.text(f"🔍 Iterasi {i+1}: Verifikasi dengan DeBERTa-v3-Large...")
            score = query_deberta(candidate)
            
            if score is not None:
                final_score = score
                if score <= target_score:
                    break
                current_text = candidate
            else:
                final_score = None
                break
                
        progress_bar.progress(100)
        status.text("✅ Optimasi Selesai!")
        
        st.session_state['results'] = best_variations
        st.session_state['ai_score'] = final_score
        st.session_state['master'] = best_variations[0]
    else:
        st.error("Teks aslinya diisi dulu, Ndra!")

# 4. TAHAP HASIL & EDITOR
if 'results' in st.session_state:
    st.divider()
    
    st.subheader("📋 Pilihan Variasi")
    res = st.session_state['results']
    col_v1, col_v2, col_v3 = st.columns(3)
    
    with col_v1:
        s1 = st.checkbox("Gunakan Var 1", value=True)
        st.info(res[0])
    with col_v2:
        s2 = st.checkbox("Gunakan Var 2")
        st.info(res[1])
    with col_v3:
        s3 = st.checkbox("Gunakan Var 3")
        st.info(res[2])

    if st.button("🪄 Mix & Rescan"):
        sel = [res[i] for i, s in enumerate([s1, s2, s3]) if s]
        if len(sel) >= 2:
            st.session_state['master'] = mix_ai_logic(sel, major)
            st.session_state['ai_score'] = query_deberta(st.session_state['master'])
        else:
            st.warning("Pilih minimal 2 variasi untuk di-mix!")

    st.divider()

    # 5. MASTER EDITOR & METRIK
    st.subheader("🛠️ Master Editor")
    final_text = st.text_area("Edit manual hasil di sini (HIR Score akan berubah):", 
                              value=st.session_state.get('master', ""), height=280)
    
    if st.button("🔍 Update Skor Deteksi"):
        with st.spinner("Memindai ulang teks Master..."):
            st.session_state['ai_score'] = query_deberta(final_text)

    # BARIS METRIK
    col_met1, col_met2, col_met3 = st.columns(3)
    
    with col_met1:
        colored_metric("DeBERTa AI Score", st.session_state.get('ai_score'))
        
    with col_met2:
        # Kalkulasi HIR Score
        m_text = st.session_state.get('master', "")
        hir = min((1 - ratio(m_text, final_text)) * 350, 100.0) if m_text else 0
        colored_metric("Human-Input Ratio", hir, is_ai_score=False)
        
    with col_met3:
        char_count = len(final_text)
        char_color = "#6c757d" if char_count <= 4096 else "#dc3545"
        st.markdown(f"""
            <div class="metric-card" style="background-color: {char_color};">
                <div style="font-size: 0.85em; opacity: 0.9;">Karakter</div>
                <div style="font-size: 1.7em; font-weight: bold;">{char_count} / 4096</div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    # OUTPUT AKHIR & TELEGRAM
    st.subheader("📤 Finalisasi & Kirim")
    st.code(final_text, language=None)
    
    catatan = st.text_input("Judul/Keterangan Pesan (Telegram):", placeholder="Misal: Bab 1 Pendahuluan - Fix")
    
    if st.button("✈️ Kirim ke Telegram"):
        if final_text.strip():
            if len(final_text) <= 4096:
                token = st.secrets["TELEGRAM_BOT_TOKEN"]
                chat_id = st.secrets["TELEGRAM_CHAT_ID"]
                ai_rep = f"{st.session_state['ai_score']:.1f}%" if st.session_state['ai_score'] is not None else "N/A"
                
                pesan = (f"📩 **LAPORAN AI HUMANIZER**\n"
                         f"📌 **Judul:** {catatan if catatan else '-'}\n"
                         f"🤖 **AI Score:** {ai_rep}\n"
                         f"📊 **HIR Score:** {hir:.1f}%\n\n"
                         f"📝 **Isi Teks:**\n{final_text}")
                
                try:
                    res_tele = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                                             data={"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"})
                    if res_tele.status_code == 200:
                        st.success("Teks berhasil dikirim ke Telegram!")
                    else:
                        st.error("Gagal kirim ke Telegram. Cek Chat ID atau Token.")
                except Exception as e:
                    st.error(f"Error Telegram: {str(e)}")
            else:
                st.error("Teks terlalu panjang untuk satu pesan Telegram (Max 4096 karakter)!")
        else:
            st.error("Teks Master Editor masih kosong!")
