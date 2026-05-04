import streamlit as st
from groq import Groq
from Levenshtein import ratio
import requests
import time

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="AI Humanizer Elite", layout="wide", page_icon="🛡️")

# CSS untuk UI Mobile & Progress Bar
st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px !important; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    @media (max-width: 640px) { .stActionButton { width: 100%; } }
    </style>
    """, unsafe_allow_html=True)

# 2. INISIALISASI CLIENT & API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
HF_TOKEN = st.secrets["HF_API_KEY"]

# Fungsi Detektor DeBERTa-v3-Large
def query_deberta(text):
    # Menggunakan model DeBERTa-v3-Large yang di-fine-tune untuk deteksi AI
    API_URL = "https://api-inference.huggingface.co/models/Duskfall77/deberta-v3-large-ai-detector"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=10)
        result = response.json()
        
        # Parsing hasil: Cari skor untuk label AI/FAKE
        # Format HF biasanya: [[{'label': 'AI', 'score': 0.9}, {'label': 'Human', 'score': 0.1}]]
        if isinstance(result, list) and len(result) > 0:
            for item in result[0]:
                if item['label'].upper() in ['AI', 'FAKE', 'LABEL_1']:
                    return item['score'] * 100
        return 0
    except:
        return None

def get_ai_response(text, style, major, temp, feedback_note=""):
    # Prompt diperkuat dengan instruksi anti-deteksi
    feedback_instruction = f"\nCATATAN PERBAIKAN: {feedback_note}" if feedback_note else ""
    
    system_prompt = f"""
    Anda pakar parafrase {major}. Ubah teks ke gaya {style}.
    TUGAS: Lakukan rekonstruksi total untuk mengelabui detektor AI paling ketat (Copyleaks/DeBERTa).
    ATURAN:
    1. Hancurkan pola repetitif. Gunakan variasi panjang kalimat (Burstiness).
    2. Tingkatkan kerumitan diksi (Perplexity) tapi tetap natural.
    3. Mulai kalimat dengan cara yang tidak terduga.
    4. PERTAHANKAN jumlah informasi asli, jangan bertele-tele.{feedback_instruction}
    """
    
    variations = []
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
    prompt = f"Sintesiskan teks berikut menjadi satu paragraf bidang {major}. Pastikan alur sangat halus, tidak redundan, dan memiliki 'suara' manusia yang kuat. Jangan lebih panjang dari aslinya."
    chat_completion = client.chat.completions.create(
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": combined}],
        model="llama-3.3-70b-versatile",
        temperature=0.6,
    )
    return chat_completion.choices[0].message.content

def send_telegram(text, hir, ai_score, catatan):
    token = st.secrets["TELEGRAM_BOT_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    
    pesan = (f"📩 **LAPORAN HUMANIZER**\n"
             f"📌 **Judul:** {catatan if catatan else '-'}\n"
             f"📊 **HIR Score:** {hir:.1f}%\n"
             f"🤖 **DeBERTa AI Score:** {ai_score:.1f}%\n\n"
             f"📝 **Teks:**\n{text}")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return requests.post(url, data={"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"})

# 3. UI UTAMA
st.title("🛡️ AI Humanizer Elite (DeBERTa Edition)")
st.caption("Sistem Parafrase dengan Umpan Balik Detektor AI Real-time.")

with st.sidebar:
    st.header("⚙️ Konfigurasi")
    major = st.text_input("Bidang Ilmu:", "Psikologi & IT")
    style = st.selectbox("Gaya Penulisan:", ["Kritis & Analitis", "Formal Akademik", "Naratif", "Ringkas"])
    temp = st.slider("Kreativitas (Temperature)", 0.6, 1.0, 0.85)
    st.divider()
    threshold = st.slider("Ambang Batas Aman AI (%)", 5, 50, 20)
    st.info("Sistem akan mencoba memparafrase sampai skor di bawah angka ini.")

user_input = st.text_area("Masukkan Teks AI (ChatGPT/Lainnya):", height=150)

if st.button("🚀 Humanize & Scan"):
    if user_input.strip():
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # FEEDBACK LOOP LOGIC
        current_text = user_input
        best_candidate = ""
        final_score = 100
        
        for i in range(2): # Maksimal 2x percobaan otomatis untuk hemat waktu
            status_text.text(f"Iterasi {i+1}: Mencuci teks...")
            progress_bar.progress(30 if i==0 else 60)
            
            variations = get_ai_response(current_text, style, major, temp, 
                                         feedback_note=f"Teks sebelumnya masih terdeteksi {final_score}% AI" if i > 0 else "")
            
            candidate = variations[0]
            status_text.text(f"Iterasi {i+1}: Memindai dengan DeBERTa-v3-Large...")
            
            score = query_deberta(candidate)
            
            if score is not None:
                final_score = score
                best_candidate = candidate
                if score <= threshold:
                    break
            else:
                best_candidate = candidate
                break
        
        progress_bar.progress(100)
        status_text.text("Selesai!")
        
        st.session_state['results'] = variations
        st.session_state['ai_score'] = final_score
        st.session_state['master'] = best_candidate
    else:
        st.error("Teks belum diisi!")

# 4. HASIL & MIXER
if 'results' in st.session_state:
    st.divider()
    col_score1, col_score2 = st.columns(2)
    with col_score1:
        st.metric("DeBERTa AI Score", f"{st.session_state['ai_score']:.1f}%")
    with col_score2:
        if st.session_state['ai_score'] <= threshold:
            st.success("✅ AMAN: Lolos deteksi DeBERTa.")
        else:
            st.warning("⚠️ WASPADA: Masih terdeteksi AI. Gunakan Mix atau Edit Manual.")

    st.subheader("📋 Pilihan Variasi (Full Text)")
    res = st.session_state['results']
    s1 = st.checkbox("Variasi 1", value=True)
    st.info(res[0])
    s2 = st.checkbox("Variasi 2")
    st.info(res[1])
    s3 = st.checkbox("Variasi 3")
    st.info(res[2])

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🪄 Mix Pilihan"):
            sel = [res[i] for i, s in enumerate([s1, s2, s3]) if s]
            if len(sel) >= 2:
                st.session_state['master'] = mix_ai_logic(sel, major)
                # Rescan setelah mix
                st.session_state['ai_score'] = query_deberta(st.session_state['master'])
            else: st.warning("Pilih minimal 2!")
    with c2:
        if st.button("🤖 Auto-Mix Semua"):
            st.session_state['master'] = mix_ai_logic(res, major)
            st.session_state['ai_score'] = query_deberta(st.session_state['master'])

    st.divider()

    # 5. MASTER EDITOR
    st.subheader("🛠️ Master Editor")
    final_text = st.text_area("Sentuhan Akhir Manusia:", value=st.session_state.get('master', ""), height=250)
    
    char_count = len(final_text)
    col_a, col_b = st.columns(2)
    with col_a:
        st.caption(f"📏 Karakter: {char_count}/4096")
        if char_count > 4096: st.error("Melebihi batas Telegram!")
    with col_b:
        if 'master' in st.session_state:
            hir = min((1 - ratio(st.session_state['master'], final_text)) * 300, 100.0)
            st.metric("HIR Score", f"{hir:.1f}%")

    st.code(final_text, language=None)
    catatan = st.text_input("Keterangan untuk Telegram:")
    
    if st.button("✈️ Kirim ke Telegram"):
        if char_count <= 4096:
            res_tele = send_telegram(final_text, hir, st.session_state['ai_score'], catatan)
            if res_tele.status_code == 200: st.success("Terkirim!")
            else: st.error("Gagal! Cek API/ChatID.")
        else: st.error("Teks terlalu panjang.")
