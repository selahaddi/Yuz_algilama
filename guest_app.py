import streamlit as st
import os
import cv2
import numpy as np
from PIL import Image
from supabase import create_client, Client
from dotenv import load_dotenv
from core.face_analyzer import FaceAnalyzer

# Ortam değişkenlerini yükle
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
# Misafir arayüzü sadece anon key kullanmalı
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))

st.set_page_config(page_title="Fotoğraf Bul", layout="wide", page_icon="📷")

@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        st.error("Lütfen .env dosyanızda SUPABASE_URL ve SUPABASE_ANON_KEY tanımlayın.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@st.cache_resource
def get_face_analyzer():
    # Misafir selfie işlemleri için FaceAnalyzer (Hızlı tespit için)
    return FaceAnalyzer(gpu_id=0)

supabase = get_supabase_client()
analyzer = get_face_analyzer()

# URL'den event_id al (st.query_params)
query_params = st.query_params
event_id = query_params.get("event_id")

if not event_id:
    st.title("📷 Etkinlik Bulunamadı")
    st.error("Lütfen geçerli bir etkinlik linki (veya QR kod) kullandığınızdan emin olun.")
    st.stop()

# Etkinlik Bilgilerini Çek
@st.cache_data(ttl=300)
def get_event_details(eid):
    res = supabase.table("events").select("*").eq("id", eid).execute()
    return res.data[0] if res.data else None

event = get_event_details(event_id)
if not event:
    st.error("Etkinlik bulunamadı veya silinmiş.")
    st.stop()

st.title(f"🎉 {event['title']} - Hoşgeldiniz!")
st.markdown("Fotoğraflarınızı bulmak için aşağıdaki yöntemlerden birini seçin.")

# KVKK Onayı
if "kvkk_accepted" not in st.session_state:
    st.session_state.kvkk_accepted = False

kvkk = st.checkbox(
    "Yüz verilerimin eşleştirme amacıyla işlenmesine ve etkinlik sonrasında silineceğine onay veriyorum. (Aydınlatma Metni)",
    value=st.session_state.kvkk_accepted
)

if not kvkk:
    st.session_state.kvkk_accepted = False
    st.warning("Devam etmek için KVKK metnini onaylamanız gerekmektedir.")
    st.stop()
else:
    st.session_state.kvkk_accepted = True

st.markdown("---")

tab1, tab2 = st.tabs(["🤳 Selfie ile Bul (Önerilen)", "📂 Kişi Listesinden Seç"])

# --- YÖNTEM 1: SELFIE ARAMASI ---
with tab1:
    st.markdown("Kameranızı açarak veya galerinizden bir selfie yükleyerek tüm fotoğraflarınızı saniyeler içinde bulun!")
    
    input_method = st.radio("Fotoğraf Kaynağı:", ["Kamera (Çek)", "Dosya Yükle"])
    img_file = None
    
    if input_method == "Kamera (Çek)":
        img_file = st.camera_input("Selfie Çek")
    else:
        img_file = st.file_uploader("Selfie Yükle", type=['jpg', 'jpeg', 'png'])
        
    if img_file is not None:
        with st.spinner("Yüzünüz analiz ediliyor ve eşleşmeler aranıyor..."):
            # Fotoğrafı oku ve analiz et
            file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            if img is not None:
                faces = analyzer.analyze_image(img)
                if not faces:
                    st.error("Yüz tespit edilemedi. Lütfen daha net ve aydınlık bir selfie çekin.")
                else:
                    # En büyük yüzü al (Selfie çeken kişi)
                    best_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
                    embedding_list = best_face.embedding.astype(float).tolist()
                    embedding_str = f"[{','.join(map(str, embedding_list))}]"
                    
                    # RPC çağrısı ile vektör araması
                    try:
                        res = supabase.rpc(
                            "match_faces", 
                            {
                                "query_embedding": embedding_str,
                                "match_threshold": 0.45,  # Benzerlik eşiği (Cosine similarity)
                                "match_count": 50,        # En fazla kaç sonuç dönecek
                                "target_event_id": event_id
                            }
                        ).execute()
                        
                        matches = res.data
                        if not matches:
                            st.info("Üzgünüz, size ait bir fotoğraf bulunamadı.")
                        else:
                            st.success(f"Harika! Size ait {len(matches)} fotoğraf bulundu.")
                            
                            # Sonuçları göster
                            cols = st.columns(3)
                            for i, match in enumerate(matches):
                                with cols[i % 3]:
                                    with st.container(border=True):
                                        # Thumbnail varsa onu kullan, yoksa orijinali
                                        display_url = match.get("thumbnail_url") or match["image_url"]
                                        st.image(display_url, use_container_width=True)
                                        # İndirme linki
                                        st.markdown(f"[📥 Orijinali İndir (Yüksek Çözünürlük)]({match['image_url']})")
                                        
                    except Exception as e:
                        st.error(f"Arama sırasında hata oluştu: {e}")
            else:
                st.error("Fotoğraf okunamadı.")


# --- YÖNTEM 2: KÜME SEÇİMİ (ESKİ SİSTEM) ---
with tab2:
    st.markdown("Arka planda aynı kişiye ait olduğu tespit edilen fotoğraf gruplarını buradan inceleyebilirsiniz.")
    
    @st.cache_data(ttl=60)
    def get_event_clusters(eid):
        # Bu etkinlikteki benzersiz cluster_id'leri bul
        res = supabase.table("faces") \
            .select("cluster_id, photos!inner(event_id)") \
            .eq("photos.event_id", eid) \
            .neq("cluster_id", -1) \
            .execute()
            
        if res.data:
            clusters = list(set(row["cluster_id"] for row in res.data if row["cluster_id"] is not None))
            return sorted(clusters)
        return []
        
    clusters = get_event_clusters(event_id)
    
    if not clusters:
        st.info("Bu etkinlik için henüz yüzler gruplanmadı veya hazır değil.")
    else:
        st.write(f"Sistem toplam **{len(clusters)}** farklı kişi tespit etti.")
        
        # Seçili cluster'ı session_state'de tutalım (Sayfalama gerekirse eklenebilir)
        selected_cluster = st.selectbox("Kişi Seçin:", clusters, format_func=lambda x: f"Kişi #{x}")
        
        if st.button("Seçili Kişinin Fotoğraflarını Getir", type="primary"):
            with st.spinner("Fotoğraflar getiriliyor..."):
                res = supabase.table("faces") \
                    .select("photos(image_url, thumbnail_url)") \
                    .eq("cluster_id", selected_cluster) \
                    .execute()
                    
                if res.data:
                    # Duplicate (aynı fotoğraf içinde birden fazla yüz varsa) urls olmaması için filtrele
                    unique_photos = {}
                    for row in res.data:
                        if row.get("photos"):
                            p = row["photos"]
                            unique_photos[p["image_url"]] = p
                            
                    photo_list = list(unique_photos.values())
                    st.success(f"{len(photo_list)} fotoğraf bulundu.")
                    
                    cols = st.columns(3)
                    for i, p in enumerate(photo_list):
                        with cols[i % 3]:
                            with st.container(border=True):
                                display_url = p.get("thumbnail_url") or p["image_url"]
                                st.image(display_url, use_container_width=True)
                                st.markdown(f"[📥 Orijinali İndir]({p['image_url']})")
                else:
                    st.warning("Bu kişiye ait fotoğraf bulunamadı (Veritabanı ilişkisi hatası).")
