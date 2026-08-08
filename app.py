import streamlit as st
import os
import requests
from io import BytesIO
from PIL import Image, ImageOps
from supabase import create_client, Client
from dotenv import load_dotenv

# Ortam değişkenlerini yükle
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
# Frontend yalnızca anon key kullanmalı (RLS kurallarına tabi olur)
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))

st.set_page_config(page_title="Düğün Fotoğraf Galerisi", layout="wide", page_icon="💍")

# ─── Supabase İstemcisi ────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        st.error("Lütfen .env dosyanızda SUPABASE_URL ve SUPABASE_ANON_KEY değerlerini tanımlayın.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

supabase = get_supabase_client()

# ─── Sabitler ──────────────────────────────────────────────────────────────────
ALBUMS_PER_PAGE = 12        # Albüm listesinde sayfa başına gösterilecek albüm
PHOTOS_PER_PAGE = 12        # Albüm detayında sayfa başına gösterilecek fotoğraf
COVER_CACHE_TTL = 300       # Kapak fotoğrafı önbellek süresi (saniye)
CLUSTERS_CACHE_TTL = 60     # Küme listesi önbellek süresi (saniye)


# ─── Responsive Grid Yardımcısı ───────────────────────────────────────────────
def get_cols_per_row() -> int:
    """Ekran genişliğine göre sütun sayısı (mobil uyumluluk)."""
    # Streamlit'te gerçek ekran genişliği almak mümkün olmadığından,
    # layout="wide" ile 3 sütun makul bir varsayılan
    return 3


# ─── Sayfa Başlığı ve Açıklama ────────────────────────────────────────────────
st.title("💍 Düğün Fotoğraf Galerisi")
st.markdown("Arka plandaki yapay zeka tarafından işlenip yüzlere göre kategorize edilmiş düğün fotoğraflarınızı inceleyin.")


# ─── Sol Menü: Fotoğraf Ekleme ────────────────────────────────────────────────
st.sidebar.header("➕ Yeni Fotoğraf Ekle")

upload_method = st.sidebar.radio("Yükleme Yöntemi:", ["Dosya Yükle (Bilgisayardan)", "URL Yapıştır"])

if upload_method == "URL Yapıştır":
    st.sidebar.markdown("Kuyruğa yeni bir fotoğraf URL'si ekleyin:")
    new_url = st.sidebar.text_input("Resim URL'si:", placeholder="https://ornek.com/resim.jpg")

    if st.sidebar.button("Kuyruğa Gönder", type="primary"):
        if new_url:
            try:
                supabase.table("photos").insert({"image_url": new_url}).execute()
                st.sidebar.success("✅ Kuyruğa eklendi! Worker işliyor...")
            except Exception as e:
                st.sidebar.error(f"Hata: {e}")
        else:
            st.sidebar.warning("Lütfen bir URL girin.")

elif upload_method == "Dosya Yükle (Bilgisayardan)":
    uploaded_files = st.sidebar.file_uploader(
        "Fotoğrafları Seç (Çoklu Seçim Yapabilirsiniz)", 
        type=["jpg", "jpeg", "png"], 
        accept_multiple_files=True
    )
    
    if st.sidebar.button("Yükle ve Kuyruğa Gönder", type="primary"):
        if uploaded_files:
            progress_bar = st.sidebar.progress(0, text="Yükleniyor...")
            success_count = 0
            import uuid
            
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
                    supabase.table("photos").insert({"image_url": public_url}).execute()
                    success_count += 1
                    
                except Exception as e:
                    st.sidebar.error(f"Hata ({uploaded_file.name}): {e}")
                
                progress_bar.progress(
                    (idx + 1) / len(uploaded_files), 
                    text=f"{idx + 1}/{len(uploaded_files)} yüklendi"
                )
            
            if success_count > 0:
                st.sidebar.success(f"✅ {success_count} fotoğraf başarıyla yüklendi ve kuyruğa eklendi!")
            
            if success_count < len(uploaded_files):
                st.sidebar.info(
                    "Eğer tüm dosyalar yüklenemediyse Supabase panelinizden 'Storage' bölümüne gidip "
                    "'wedding_photos' adında **Public (Herkese Açık)** bir kova (bucket) oluşturduğunuzdan emin olun."
                )
        else:
            st.sidebar.warning("Lütfen en az bir dosya seçin.")

st.sidebar.markdown("---")

# ─── Sol Menü: İşlem Durumu ────────────────────────────────────────────────────
st.sidebar.header("📊 İşlem Durumu")

@st.cache_data(ttl=30)
def get_queue_status():
    """Kuyrukta bekleyen ve işlenmiş fotoğraf sayılarını döndürür."""
    try:
        pending = supabase.table("photos").select("id", count="exact").eq("processed", False).execute()
        processed = supabase.table("photos").select("id", count="exact").eq("processed", True).execute()
        total_faces = supabase.table("faces").select("id", count="exact").execute()
        return {
            "pending": pending.count or 0,
            "processed": processed.count or 0,
            "faces": total_faces.count or 0,
        }
    except Exception:
        return {"pending": 0, "processed": 0, "faces": 0}

status = get_queue_status()
col_s1, col_s2, col_s3 = st.sidebar.columns(3)
col_s1.metric("Bekleyen", status["pending"])
col_s2.metric("İşlenen", status["processed"])
col_s3.metric("Yüzler", status["faces"])

if status["pending"] > 0:
    st.sidebar.warning(f"⏳ {status['pending']} fotoğraf işlenmeyi bekliyor...")

st.sidebar.markdown("---")


# ─── Veritabanı Sorguları ──────────────────────────────────────────────────────
@st.cache_data(ttl=CLUSTERS_CACHE_TTL)
def get_unique_clusters():
    """Gürültü olmayan (-1) benzersiz cluster_id'leri döndürür."""
    try:
        res = supabase.table("faces").select("cluster_id").neq("cluster_id", -1).execute()
        if res.data:
            clusters = list(set(row["cluster_id"] for row in res.data if row["cluster_id"] is not None))
            return sorted(clusters)
        return []
    except Exception as e:
        st.error(f"Veritabanına bağlanılamadı: {e}")
        return []


@st.cache_data(ttl=COVER_CACHE_TTL)
def get_album_cover_bytes(cluster_id: int) -> tuple:
    """
    Bir albümün kapak fotoğrafını indirir, yüzü kırpar ve bytes olarak döndürür.
    Önbelleğe alınarak tekrar tekrar indirilmesi engellenir.
    
    :return: (image_bytes, format) veya (None, None)
    """
    try:
        cover_res = supabase.table("faces") \
            .select("bbox, photos(image_url)") \
            .eq("cluster_id", cluster_id) \
            .limit(1) \
            .execute()
        
        if not cover_res.data or not cover_res.data[0].get("photos"):
            return None, None
        
        cover_url = cover_res.data[0]["photos"]["image_url"]
        bbox = cover_res.data[0].get("bbox")
        
        response = requests.get(cover_url, timeout=10)
        if response.status_code != 200:
            return None, None
        
        img = Image.open(BytesIO(response.content))
        img = ImageOps.exif_transpose(img)
        
        if bbox and len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            w, h = x2 - x1, y2 - y1
            pad_x, pad_y = w * 0.2, h * 0.2
            
            crop_box = (
                max(0, x1 - pad_x), 
                max(0, y1 - pad_y), 
                min(img.width, x2 + pad_x), 
                min(img.height, y2 + pad_y)
            )
            img = img.crop(crop_box)
        
        # PIL Image -> bytes (önbellek için serializable olmalı)
        buf = BytesIO()
        img_format = "JPEG"
        img.save(buf, format=img_format, quality=85)
        return buf.getvalue(), img_format
        
    except Exception:
        return None, None


@st.cache_data(ttl=CLUSTERS_CACHE_TTL)
def get_cluster_face_count(cluster_id: int) -> int:
    """Bir kişiye ait benzersiz fotoğraf sayısını döndürür."""
    try:
        res = supabase.table("faces") \
            .select("photo_id") \
            .eq("cluster_id", cluster_id) \
            .execute()
        if res.data:
            return len(set(row["photo_id"] for row in res.data))
        return 0
    except Exception:
        return 0


def get_cluster_photos_paginated(cluster_id: int, page: int, per_page: int) -> tuple:
    """
    Bir kişiye ait fotoğrafları sayfalı olarak döndürür.
    
    :return: (url_listesi, toplam_benzersiz_url_sayısı)
    """
    try:
        # Tüm photo URL'lerini çek ve benzersiz yap
        response = supabase.table("faces") \
            .select("photos(image_url)") \
            .eq("cluster_id", cluster_id) \
            .execute()
        
        if not response.data:
            return [], 0
        
        unique_urls = list(set(
            row["photos"]["image_url"] 
            for row in response.data 
            if row.get("photos") and row["photos"].get("image_url")
        ))
        
        total = len(unique_urls)
        
        # Sayfalama uygula
        start = (page - 1) * per_page
        end = start + per_page
        paginated_urls = unique_urls[start:end]
        
        return paginated_urls, total
        
    except Exception as e:
        st.error(f"Fotoğraflar çekilirken hata oluştu: {e}")
        return [], 0


# ─── Albüm Navigasyonu (Session State) ────────────────────────────────────────
if 'selected_cluster' not in st.session_state:
    st.session_state.selected_cluster = None
if 'album_page' not in st.session_state:
    st.session_state.album_page = 1
if 'photo_page' not in st.session_state:
    st.session_state.photo_page = 1


clusters = get_unique_clusters()

if not clusters:
    st.info(
        "Veritabanında henüz işlenmiş ve kategorize edilmiş bir yüz bulunmuyor. "
        "Arka planda worker.py'nin çalışıp fotoğrafları işlemesini bekleyin."
    )
else:
    if st.session_state.selected_cluster is None:
        # ═══════════════════════════════════════════════════════════════════════
        # ALBÜM LİSTESİ GÖRÜNÜMÜ
        # ═══════════════════════════════════════════════════════════════════════
        st.subheader(f"📸 Albümler ({len(clusters)} Kişi)")
        
        # Albüm listesi sayfalama
        total_album_pages = max(1, (len(clusters) + ALBUMS_PER_PAGE - 1) // ALBUMS_PER_PAGE)
        album_page = st.session_state.album_page
        
        start_idx = (album_page - 1) * ALBUMS_PER_PAGE
        end_idx = start_idx + ALBUMS_PER_PAGE
        visible_clusters = clusters[start_idx:end_idx]
        
        # Grid oluştur
        cols_per_row = get_cols_per_row()
        for i in range(0, len(visible_clusters), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < len(visible_clusters):
                    cluster_id = visible_clusters[i + j]
                    label = f"Kişi {cluster_id + 1}"
                    
                    with cols[j]:
                        with st.container(border=True):
                            # Önbelleğe alınmış kapak fotoğrafını göster
                            cover_bytes, _ = get_album_cover_bytes(cluster_id)
                            if cover_bytes:
                                st.image(
                                    cover_bytes, 
                                    caption=f"{label}", 
                                    use_container_width=True
                                )
                            else:
                                st.info("Kapak Yok")
                            
                            # Fotoğraf sayısını göster
                            photo_count = get_cluster_face_count(cluster_id)
                            st.caption(f"📷 {photo_count} fotoğraf")
                            
                            if st.button(
                                f"📂 Albümü Aç", 
                                key=f"btn_{cluster_id}", 
                                use_container_width=True
                            ):
                                st.session_state.selected_cluster = cluster_id
                                st.session_state.photo_page = 1
                                st.rerun()
        
        # Albüm sayfaları navigasyonu
        if total_album_pages > 1:
            st.markdown("---")
            nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
            
            with nav_col1:
                if album_page > 1:
                    if st.button("⬅️ Önceki", key="prev_album_page"):
                        st.session_state.album_page -= 1
                        st.rerun()
            
            with nav_col2:
                st.markdown(
                    f"<p style='text-align: center;'>Sayfa {album_page} / {total_album_pages}</p>", 
                    unsafe_allow_html=True
                )
            
            with nav_col3:
                if album_page < total_album_pages:
                    if st.button("Sonraki ➡️", key="next_album_page"):
                        st.session_state.album_page += 1
                        st.rerun()

    else:
        # ═══════════════════════════════════════════════════════════════════════
        # ALBÜM DETAY GÖRÜNÜMÜ
        # ═══════════════════════════════════════════════════════════════════════
        selected_cluster_id = st.session_state.selected_cluster
        selected_label = f"Kişi {selected_cluster_id + 1}"
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("⬅️ Albümlere Dön", use_container_width=True):
                st.session_state.selected_cluster = None
                st.session_state.photo_page = 1
                st.rerun()
        
        with col2:
            st.subheader(f"📂 {selected_label} Fotoğrafları")
            
        st.markdown("---")
        
        # Sayfalı fotoğrafları çek
        current_page = st.session_state.photo_page
        urls, total_photos = get_cluster_photos_paginated(
            selected_cluster_id, current_page, PHOTOS_PER_PAGE
        )
        total_photo_pages = max(1, (total_photos + PHOTOS_PER_PAGE - 1) // PHOTOS_PER_PAGE)
        
        if urls:
            st.success(
                f"{selected_label} için toplam {total_photos} fotoğraf bulundu. "
                f"(Sayfa {current_page}/{total_photo_pages})"
            )
            
            # Fotoğrafları grid yapısında göster
            cols_per_row = get_cols_per_row()
            for i in range(0, len(urls), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(urls):
                        url = urls[i + j]
                        with cols[j]:
                            st.image(
                                url, 
                                caption=f"{selected_label} - Fotoğraf {(current_page - 1) * PHOTOS_PER_PAGE + i + j + 1}",
                                use_container_width=True
                            )
            
            # Fotoğraf sayfaları navigasyonu
            if total_photo_pages > 1:
                st.markdown("---")
                nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                
                with nav_col1:
                    if current_page > 1:
                        if st.button("⬅️ Önceki Sayfa", key="prev_photo_page"):
                            st.session_state.photo_page -= 1
                            st.rerun()
                
                with nav_col2:
                    st.markdown(
                        f"<p style='text-align: center;'>Sayfa {current_page} / {total_photo_pages}</p>",
                        unsafe_allow_html=True
                    )
                
                with nav_col3:
                    if current_page < total_photo_pages:
                        if st.button("Sonraki Sayfa ➡️", key="next_photo_page"):
                            st.session_state.photo_page += 1
                            st.rerun()
        else:
            st.warning("Bu kişiye ait fotoğraf bulunamadı.")
