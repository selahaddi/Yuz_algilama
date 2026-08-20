import streamlit as st
import os
import uuid
import requests as http_requests
from supabase import create_client, Client
from dotenv import load_dotenv
from PIL import Image, ImageOps
import io

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
                
                # Metadata'dan stüdyo adını al, yoksa "Stüdyo" kullan
                studio_name = res.user.user_metadata.get("studio_name", "Stüdyo") if res.user.user_metadata else "Stüdyo"
                
                st.session_state.studio_id = get_studio_id(res.user.id, login_email, studio_name)
                st.rerun()
            except Exception as e:
                err_msg = str(e)
                st.error(f"Giriş başarısız: {err_msg}")
                if "Email not confirmed" in err_msg or "Invalid login credentials" in err_msg:
                    st.warning("💡 İpucu: Supabase'de 'Email Confirmations' açık olabilir. Lütfen e-postanıza gelen doğrulama linkine tıklayın veya Supabase panelinden (Authentication -> Providers -> Email) 'Confirm email' ayarını kapatın.")
                
    with tab2:
        reg_name = st.text_input("Stüdyo Adı")
        reg_email = st.text_input("E-Posta", key="reg_email")
        reg_password = st.text_input("Şifre", type="password", key="reg_pass")
        if st.button("Kayıt Ol"):
            if not reg_name or not reg_email or not reg_password:
                st.warning("Lütfen tüm alanları doldurun.")
            else:
                try:
                    res = supabase.auth.sign_up({
                        "email": reg_email, 
                        "password": reg_password,
                        "options": {
                            "data": {
                                "studio_name": reg_name
                            }
                        }
                    })
                    st.success("✅ Kayıt başarılı! Lütfen giriş yapın.")
                    st.info("⚠️ NOT: Eğer Supabase ayarlarınızda 'Email Confirmations' açıksa, giriş yapabilmek için önce e-postanıza gelen doğrulama linkine tıklamanız gerekir.")
                except Exception as e:
                    err_msg = str(e)
                    st.error(f"Kayıt başarısız: {err_msg}")
                    if "rate limit" in err_msg.lower():
                        st.warning("⏱️ Çok fazla kayıt denemesi yaptınız. Supabase güvenlik limitine takıldınız. Lütfen daha sonra tekrar deneyin veya Supabase panelinden Rate Limit ayarlarını artırın.")
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
    
    # Misafir Linki (Çevresel değişkenden alınır, yoksa localhost kullanılır)
    base_url = os.environ.get("GUEST_API_URL", "https://guest-api-398389727192.europe-west1.run.app")
    guest_link = f"{base_url}/?event_id={ev['id']}"
    
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
                    file_name = f"{uuid.uuid4()}.jpg"
                    content_type = "image/jpeg"
                    
                    # Görseli RAM'de aç ve optimize et
                    img = Image.open(uploaded_file)
                    
                    # Telefon kameraları için Exif yönlendirmesini düzelt
                    try:
                        img = ImageOps.exif_transpose(img)
                    except Exception:
                        pass
                    
                    # Max çözünürlüğü 1920px (FHD) olarak sınırla
                    img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                    
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                        
                    # %85 kaliteyle JPEG olarak sıkıştır
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85)
                    file_bytes = buf.getvalue()
                    
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
                st.success(f"✅ {success_count} fotoğraf başarıyla yüklendi!")
                
                # Worker Job'ı otomatik tetikle (Yüz algılama ve kümeleme işlemi)
                with st.spinner("🤖 Yapay zeka yüz analizi başlatılıyor..."):
                    try:
                        trigger_url = f"{base_url}/api/trigger_worker"
                        trigger_res = http_requests.post(trigger_url, timeout=15)
                        trigger_data = trigger_res.json()
                        
                        if trigger_data.get("status") == "ok":
                            st.info("🚀 Yüz analizi arka planda başlatıldı. Birkaç dakika içinde işlenecek.")
                        elif trigger_data.get("status") == "skipped":
                            st.warning("⚠️ Worker yerel ortamda tetiklenemedi. Lütfen Cloud Run Jobs'ı manuel başlatın.")
                        else:
                            st.warning(f"⚠️ Worker tetikleme uyarısı: {trigger_data.get('message', 'Bilinmeyen')}")
                    except Exception as trigger_err:
                        st.warning(f"⚠️ Worker otomatik başlatılamadı: {trigger_err}. Fotoğraflar yüklendi, işleme manuel başlatılabilir.")
        else:
            st.warning("Lütfen dosya seçin.")

    st.markdown("---")
    
    # İşlem Durumu (Sadece bu event_id için)
    st.subheader("📊 Etkinlik İşlem Durumu")
    pending = supabase.table("photos").select("id", count="exact").eq("event_id", ev['id']).eq("processed", False).execute()
    processed = supabase.table("photos").select("id", count="exact").eq("event_id", ev['id']).eq("processed", True).execute()
    
    total_photos = (pending.count or 0) + (processed.count or 0)
    
    # Benzersiz kişileri (clusters) API'den çek
    try:
        clusters_url = f"{base_url}/api/clusters/{ev['id']}"
        clusters_res = http_requests.get(clusters_url, timeout=10)
        clusters_data = clusters_res.json()
        total_people = len(clusters_data.get("clusters", []))
    except Exception:
        total_people = "⏳"
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Fotoğraf", total_photos)
    c2.metric("Bulunan Kişi Sayısı", total_people)
    c3.metric("Bekleyen", pending.count or 0)
    c4.metric("İşlenmiş", processed.count or 0)
