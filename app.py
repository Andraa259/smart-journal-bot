import streamlit as st
from groq import Groq
from Levenshtein import ratio

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="AI Humanizer & Paraphraser", layout="wide")

# 2. INISIALISASI CLIENT GROQ
# Kita mengambil API Key dari Secret Streamlit (untuk keamanan)
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def get_ai_response(text, style, major, temp):
    # Prompt dinamis berdasarkan input user
    system_prompt = f"""
    Anda adalah asisten ahli parafrase untuk bidang {major}.
    Tugas Anda adalah menulis ulang teks agar memiliki gaya {style}.
    Gunakan kalimat dengan panjang yang bervariasi (burstiness tinggi).
    Hindari kata-kata klise AI seperti 'perlu diingat', 'komprehensif', atau 'signifikan'.
    Tuliskan hasil dalam Bahasa Indonesia yang sangat natural.
    """
    
    # Meminta 3 variasi (kita panggil 3 kali untuk variasi maksimal)
    variations = []
    for _ in range(3):
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Parafrasekan teks ini: {text}"}
            ],
            model="llama3-70b-8192", # Versi paling pintar
            temperature=temp,
        )
        variations.append(chat_completion.choices[0].message.content)
    return variations

# 3. ANTARMUKA PENGGUNA (UI)
st.title("🛡️ AI Humanizer: Style Transfer & Mixer")
st.markdown("Ubah draf AI menjadi tulisan manusia yang unik untuk menghindari deteksi AI.")

with st.sidebar:
    st.header("⚙️ Pengaturan")
    major = st.text_input("Jurusan/Bidang Ilmu:", "Psikologi & IT")
    style = st.selectbox("Gaya Bahasa:", 
                         ["Formal Akademik", "Kritis & Tajam", "Naratif & Mengalir", "Percakapan Santai"])
    temp = st.slider("Tingkat Kreativitas (Temperature)", 0.5, 1.0, 0.8)
    st.info("Tips: Semakin tinggi kreativitas, semakin acak pola kalimatnya.")

# Layout Kolom Input
user_input = st.text_area("Tempel Teks Asli AI di Sini:", height=200, placeholder="Masukkan paragraf dari ChatGPT...")

if st.button("Proses & Buat 3 Variasi"):
    if user_input.strip() == "":
        st.error("Isi dulu teksnya, ya!")
    else:
        with st.spinner("Llama sedang meracik kata..."):
            st.session_state['results'] = get_ai_response(user_input, style, major, temp)
            st.session_state['original_input'] = user_input

# 4. TAHAP MIX & MATCH (HUMAN-IN-THE-LOOP)
if 'results' in st.session_state:
    st.subheader("Pilih & Gabungkan Hasil")
    col1, col2, col3 = st.columns(3)
    
    res = st.session_state['results']
    
    with col1:
        st.markdown("**Variasi 1**")
        st.caption(res[0][:150] + "...")
        if st.button("Pakai Opsi 1"): st.session_state['master'] = res[0]
            
    with col2:
        st.markdown("**Variasi 2**")
        st.caption(res[1][:150] + "...")
        if st.button("Pakai Opsi 2"): st.session_state['master'] = res[1]
            
    with col3:
        st.markdown("**Variasi 3**")
        st.caption(res[2][:150] + "...")
        if st.button("Pakai Opsi 3"): st.session_state['master'] = res[2]

    st.divider()

    # 5. MASTER EDITOR & HIR CALCULATION
    st.subheader("🛠️ Master Editor")
    final_text = st.text_area("Edit manual di sini untuk menaikkan HIR Score:", 
                              value=st.session_state.get('master', ""), 
                              height=300)

    # Logika HIR Score menggunakan Levenshtein Distance
    # Membandingkan draf pilihan AI dengan hasil editan akhir manusia
    if 'master' in st.session_state:
        # Menghitung seberapa banyak perubahan yang dilakukan user
        diff_ratio = (1 - ratio(st.session_state['master'], final_text)) * 100
        # Kita batasi maksimal 100%
        hir_score = min(diff_ratio * 2.5, 100.0) # Pengali 2.5 agar perubahan kecil tetap dihargai
        
        st.metric("Human-Input Ratio (HIR)", f"{hir_score:.1f}%")
        st.progress(hir_score / 100)
        
        if hir_score < 20:
            st.warning("HIR Rendah: Tambahkan beberapa kalimat atau ubah diksi agar tidak terdeteksi.")
        elif hir_score < 50:
            st.info("HIR Sedang: Sudah cukup baik, tapi satu atau dua perubahan lagi akan lebih aman.")
        else:
            st.success("HIR Tinggi: Tulisan ini sudah memiliki 'sidik jari' manusia yang kuat!")

    st.download_button("Simpan Hasil Akhir (.txt)", final_text, file_name="hasil_humanizer.txt")
