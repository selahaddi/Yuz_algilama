import streamlit as st
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

# Ortam değişkenlerini yükle
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))

st.set_page_config(page_title="Stüdyo Yönetim Paneli", layout="wide", page_icon="🏢")

@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        st.error("Lütfen .env dosyanızda SUPABASE_URL ve SUPABASE_ANON_KEY tanımlayın.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

supabase = get_supabase_client()

# --- Session State Tanımlamaları ---
if "user" not in st.session_state:
    st.session_state.user = None
if "studio_id" not in st.session_state:
    st.session_state.studio_id = None
if "current_event" not in st.session_state:
    st.session_state.current_event = None

# --- Yardımcı Fonksiyonlar ---
def get_studio_id(auth_user_id: str, email: str, name: str = "Stüdyo"):
    # Önce stüdyoyu bulmaya çalış
    res = supabase.table("studios").select("id").eq("email", email).execute()
    if res.data:
        return res.data[0]["id"]
    
    # Yoksa yeni stüdyo oluştur
    new_studio = supabase.table("studios").insert({
        "auth_id": auth_user_id,
        "name": name,
        "email": email
    }).execute()
    return new_studio.data[0]["id"]

# --- AUTH (GİRİŞ/KAYIT) EKRANI ---
if st.session_state.user is None:
    st.title("🏢 Stüdyo Girişi")
    
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        login_email = st.text_input("E-Posta", key="login_email")
        login_password = st.text_input("Şifre", type="password", key="login_pass")
        if st.button("Giriş Yap"):
            try:
                res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_password})
                st.session_state.user = res.user
                st.session_state.studio_id = get_studio_id(res.user.id, login_email)
                st.rerun()
            except Exception as e:
                st.error(f"Giriş başarısız: {e}")
                
    with tab2:
        reg_name = st.text_input("Stüdyo Adı")
        reg_email = st.text_input("E-Posta", key="reg_email")
        reg_password = st.text_input("Şifre", type="password", key="reg_pass")
        if st.button("Kayıt Ol"):
            try:
                res = supabase.auth.sign_up({"email": reg_email, "password": reg_password})
                st.success("Kayıt başarılı! Lütfen giriş yapın (Eğer e-posta onayı gerekiyorsa onaylayın).")
            except Exception as e:
                st.error(f"Kayıt başarısız: {e}")
    st.stop()

# --- ANA PANEL ---
st.sidebar.title(f"Hoşgeldiniz, Stüdyo!")
if st.sidebar.button("Çıkış Yap"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.studio_id = None
    st.session_state.current_event = None
    st.rerun()

st.sidebar.markdown("---")

# Etkinlik Listesini Çek
events_res = supabase.table("events").select("*").eq("studio_id", st.session_state.studio_id).order("created_at", desc=True).execute()
events = events_res.data

st.sidebar.subheader("📅 Etkinlikleriniz")
if not events:
    st.sidebar.info("Henüz etkinlik oluşturmadınız.")
else:
    for ev in events:
        if st.sidebar.button(ev["title"], key=f"ev_{ev['id']}", use_container_width=True):
            st.session_state.current_event = ev

# Yeni Etkinlik Ekleme
st.sidebar.markdown("---")
with st.sidebar.expander("➕ Yeni Etkinlik Oluştur"):
    new_title = st.text_input("Etkinlik Adı", placeholder="Ayşe & Ahmet Düğünü")
    new_date = st.date_input("Tarih")
    if st.button("Oluştur"):
        if new_title:
            try:
                inserted = supabase.table("events").insert({
                    "studio_id": st.session_state.studio_id,
                    "title": new_title,
                    "event_date": str(new_date)
                }).execute()
                st.session_state.current_event = inserted.data[0]
                st.rerun()
            except Exception as e:
                st.error(f"Oluşturulamadı: {e}")
        else:
            st.warning("Etkinlik adı giriniz.")

# --- ETKİNLİK DETAY EKRANI ---
if st.session_state.current_event is None:
    st.title("🏢 Stüdyo Yönetim Paneli")
    st.info("Sol menüden bir etkinlik seçin veya yeni bir etkinlik oluşturun.")
else:
    ev = st.session_state.current_event
    st.title(f"📂 Etkinlik: {ev['title']}")
    
    # Misafir Linki (Geliştirme için localhost varsayıyoruz, canlıda değiştirilir)
    guest_link = f"http://localhost:8503/?event_id={ev['id']}"
    
    st.markdown("### 🔗 Misafir Paylaşım Linki")
    st.code(guest_link, language="text")
    st.caption("Bu linki misafirlerinizle paylaşabilir veya QR koda çevirerek masalara koyabilirsiniz.")
    
    st.markdown("---")
    
    # Fotoğraf Yükleme Bölümü
    st.subheader("📸 Fotoğraf Yükle")
    uploaded_files = st.file_uploader(
        "Bu etkinlik için fotoğraf seçin (Çoklu Seçim Yapabilirsiniz)", 
        type=["jpg", "jpeg", "png"], 
        accept_multiple_files=True
    )
    
    if st.button("Seçili Fotoğrafları Yükle", type="primary"):
        if uploaded_files:
            progress_bar = st.progress(0, text="Yükleniyor...")
            success_count = 0
            
            for idx, uploaded_file in enumerate(uploaded_files):
                try:
                    file_ext = uploaded_file.name.split('.')[-1]
                    file_name = f"{uuid.uuid4()}.{file_ext}"
                    file_bytes = uploaded_file.read()
                    content_type = "image/jpeg" if file_ext.lower() in ["jpg", "jpeg"] else "image/png"
                    
                    supabase.storage.from_("wedding_photos").upload(
                        file_name, 
                        file_bytes, 
                        {"content-type": content_type}
                    )
                    
                    public_url = supabase.storage.from_("wedding_photos").get_public_url(file_name)
                    supabase.table("photos").insert({
                        "event_id": ev['id'],
                        "image_url": public_url
                    }).execute()
                    success_count += 1
                    
                except Exception as e:
                    st.error(f"Hata ({uploaded_file.name}): {e}")
                
                progress_bar.progress(
                    (idx + 1) / len(uploaded_files), 
                    text=f"{idx + 1}/{len(uploaded_files)} yüklendi"
                )
            
            if success_count > 0:
                st.success(f"✅ {success_count} fotoğraf başarıyla yüklendi! Arka planda işleniyor...")
        else:
            st.warning("Lütfen dosya seçin.")

    st.markdown("---")
    
    # İşlem Durumu (Sadece bu event_id için)
    st.subheader("📊 Etkinlik İşlem Durumu")
    pending = supabase.table("photos").select("id", count="exact").eq("event_id", ev['id']).eq("processed", False).execute()
    processed = supabase.table("photos").select("id", count="exact").eq("event_id", ev['id']).eq("processed", True).execute()
    
    c1, c2 = st.columns(2)
    c1.metric("Bekleyen Fotoğraflar", pending.count or 0)
    c2.metric("İşlenmiş Fotoğraflar", processed.count or 0)
