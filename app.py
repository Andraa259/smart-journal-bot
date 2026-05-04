import streamlit as st
from groq import Groq
from Levenshtein import ratio
import requests

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="AI Humanizer Pro", layout="wide")

# CSS untuk tampilan mobile
st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px !important; }
    @media (max-width: 640px) { .stActionButton { width: 100%; } }
    </style>
    """, unsafe_allow_html=True)

# 2. INISIALISASI CLIENT
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def get_ai_response(text, style, major, temp):
    system_prompt = f"Anda pakar parafrase {major}. Ubah teks ke gaya {style}. Variasikan struktur kalimat (burstiness tinggi) dan hindari kata klise AI. Hasil harus sangat natural dalam Bahasa Indonesia."
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
    prompt = f"Gabungkan (mix) teks-teks berikut menjadi satu paragraf yang utuh, mengalir secara logis, dan sangat manusiawi untuk bidang {major}. Pastikan tidak ada pengulangan ide."
    chat_completion = client.chat.completions.create(
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": combined}],
        model="llama-3.3-70b-versatile",
        temperature=0.7,
    )
    return chat_completion.choices[0].message.content

def send_telegram(text, hir, catatan):
    token = st.secrets["TELEGRAM_BOT_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    
    header = f"📌 **JUDUL/CATATAN:** {catatan if catatan else 'Tanpa Judul'}\n"
    stats = f"📊 **HIR Score:** {hir:.1f}%\n"
    isi = f"\n📝 **TEKS:**\n{text}"
    
    pesan_lengkap = f"📩 **HASIL AI HUMANIZER**\n\n{header}{stats}{isi}"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": pesan_lengkap, "parse_mode": "Markdown"}
    return requests.post(url, data=payload)

# 3. UI UTAMA
st.title("🛡️ AI Humanizer: Mixer Edition")

with st.sidebar:
    st.header("⚙️ Pengaturan")
    major = st.text_input("Jurusan:", "Psikologi & IT")
    style = st.selectbox("Gaya:", ["Formal Akademik", "Kritis & Tajam", "Naratif", "Percakapan Santai"])
    temp = st.slider("Kreativitas", 0.5, 1.0, 0.8)

user_input = st.text_area("Tempel Teks AI Asli:", height=200)

if st.button("🚀 Buat 3 Variasi"):
    if user_input.strip():
        with st.spinner("Meracik variasi..."):
            st.session_state['results'] = get_ai_response(user_input, style, major, temp)
    else:
        st.error("Isi teks dulu!")

# 4. TAHAP VARIASI & MIXING
if 'results' in st.session_state:
    st.subheader("📋 Hasil Variasi")
    res = st.session_state['results']
    
    select_1 = st.checkbox("Pilih Variasi 1", value=True)
    st.info(res[0])
    
    select_2 = st.checkbox("Pilih Variasi 2")
    st.info(res[1])
    
    select_3 = st.checkbox("Pilih Variasi 3")
    st.info(res[2])

    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🪄 Mix Pilihan"):
            selected = [res[i] for i, sel in enumerate([select_1, select_2, select_3]) if sel]
            if len(selected) >= 2:
                with st.spinner("Menggabungkan variasi..."):
                    st.session_state['master'] = mix_ai_logic(selected, major)
            else:
                st.warning("Pilih minimal 2 variasi untuk di-mix!")
                
    with c2:
        if st.button("🤖 Auto-Mix Semua"):
            with st.spinner("Mixing 3 variasi otomatis..."):
                st.session_state['master'] = mix_ai_logic(res, major)

    st.divider()

    # 5. MASTER EDITOR & HIR
    st.subheader("🛠️ Master Editor")
    final_text = st.text_area("Edit manual hasil mix di sini:", 
                              value=st.session_state.get('master', ""), 
                              height=300)

    # --- TAMBAHAN INFO KARAKTER ---
    char_count = len(final_text)
    if char_count > 4096:
        st.error(f"⚠️ Karakter: **{char_count}** / 4096 - **Batas Terlampaui!** Pesan akan gagal kirim ke Telegram.")
    elif char_count > 3800:
        st.warning(f"📏 Karakter: **{char_count}** / 4096 - **Hampir Penuh.**")
    else:
        st.caption(f"📏 Karakter: **{char_count}** / 4096")

    if 'master' in st.session_state:
        hir_score = min((1 - ratio(st.session_state['master'], final_text)) * 250, 100.0)
        st.metric("Human-Input Ratio (HIR)", f"{hir_score:.1f}%")
        st.progress(hir_score / 100)

        st.subheader("📤 Kirim Hasil")
        
        st.write("Klik ikon copy di bawah:")
        st.code(final_text, language=None)
        
        catatan_user = st.text_input("Judul atau Keterangan Tambahan (untuk Telegram):", 
                                    placeholder="Contoh: Revisi Bab 1")
        
        if st.button("✈️ Kirim ke Telegram"):
            if final_text.strip():
                if char_count <= 4096:
                    with st.spinner("Mengirim..."):
                        response = send_telegram(final_text, hir_score, catatan_user)
                        if response.status_code == 200:
                            st.success("Berhasil dikirim ke Telegram!")
                        else:
                            st.error("Gagal kirim. Cek Secrets Telegram kamu.")
                else:
                    st.error("Teks terlalu panjang untuk Telegram! Kurangi hingga di bawah 4096 karakter.")
            else:
                st.error("Teks masih kosong!")
