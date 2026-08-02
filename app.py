import streamlit as st
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Ortam değişkenlerini yükle
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

st.set_page_config(page_title="Düğün Fotoğraf Galerisi", layout="wide", page_icon="💍")

# Supabase istemcisini oluştur (Önbelleğe alarak performansı artırıyoruz)
@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Lütfen .env dosyanızda SUPABASE_URL ve SUPABASE_KEY değerlerini tanımlayın.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

st.title("💍 Düğün Fotoğraf Galerisi")
st.markdown("Arka plandaki yapay zeka tarafından işlenip yüzlere göre kategorize edilmiş düğün fotoğraflarınızı inceleyin.")

# Sol menüye (Sidebar) kolay fotoğraf ekleme arayüzü
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
    uploaded_files = st.sidebar.file_uploader("Fotoğrafları Seç (Çoklu Seçim Yapabilirsiniz)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if st.sidebar.button("Yükle ve Kuyruğa Gönder", type="primary"):
        if uploaded_files: # Eğer liste boş değilse
            with st.spinner(f"{len(uploaded_files)} fotoğraf yükleniyor..."):
                success_count = 0
                import uuid
                
                for uploaded_file in uploaded_files:
                    try:
                        # Dosya adını benzersiz yap
                        file_ext = uploaded_file.name.split('.')[-1]
                        file_name = f"{uuid.uuid4()}.{file_ext}"
                        
                        # Supabase Storage 'wedding_photos' adlı public bucket'a yükle
                        file_bytes = uploaded_file.read()
                        
                        # Content-type belirterek yükle
                        content_type = "image/jpeg" if file_ext.lower() in ["jpg", "jpeg"] else "image/png"
                        
                        res = supabase.storage.from_("wedding_photos").upload(
                            file_name, 
                            file_bytes, 
                            {"content-type": content_type}
                        )
                        
                        # Yüklenen dosyanın herkese açık (public) linkini al
                        public_url = supabase.storage.from_("wedding_photos").get_public_url(file_name)
                        
                        # URL'yi veritabanı kuyruğuna ekle
                        supabase.table("photos").insert({"image_url": public_url}).execute()
                        
                        success_count += 1
                        
                    except Exception as e:
                        st.sidebar.error(f"Hata ({uploaded_file.name}): {e}")
                
                if success_count > 0:
                    st.sidebar.success(f"✅ {success_count} fotoğraf başarıyla yüklendi ve kuyruğa eklendi!")
                
                if success_count < len(uploaded_files):
                    st.sidebar.info("Eğer tüm dosyalar yüklenemediyse Supabase panelinizden 'Storage' bölümüne gidip 'wedding_photos' adında **Public (Herkese Açık)** bir kova (bucket) oluşturduğunuzdan emin olun.")
        else:
            st.sidebar.warning("Lütfen en az bir dosya seçin.")

st.sidebar.markdown("---")

# 1. Veritabanından mevcut olan tüm benzersiz Kişi Kimliklerini (Cluster ID) çek
@st.cache_data(ttl=60) # 1 dakikada bir yenile
def get_unique_clusters():
    try:
        # Gürültü olmayan (-1) tüm cluster_id'leri getir
        res = supabase.table("faces").select("cluster_id").neq("cluster_id", -1).execute()
        if res.data:
            # Python'da set kullanarak benzersiz olanları ayıkla
            clusters = list(set(row["cluster_id"] for row in res.data if row["cluster_id"] is not None))
            return sorted(clusters)
        return []
    except Exception as e:
        st.error(f"Veritabanına bağlanılamadı: {e}")
        return []

clusters = get_unique_clusters()

if not clusters:
    st.info("Veritabanında henüz işlenmiş ve kategorize edilmiş bir yüz bulunmuyor. Arka planda worker.py'nin çalışıp fotoğrafları işlemesini bekleyin.")
else:
    # 2. Kullanıcıdan hangi kişiyi (Cluster) görüntülemek istediğini seçmesini iste
    # Kullanıcı dostu olması için "Kişi 1", "Kişi 2" şeklinde gösteriyoruz
    cluster_options = {f"Kişi {c + 1}": c for c in clusters}
    selected_label = st.selectbox("Görüntülemek İstediğiniz Kişiyi Seçin:", list(cluster_options.keys()))
    
    selected_cluster_id = cluster_options[selected_label]
    
    st.markdown("---")
    
    # 3. Seçilen kişiye ait fotoğrafların URL'lerini çek (JOIN işlemi)
    with st.spinner("Fotoğraflar getiriliyor..."):
        try:
            # Supabase'in Foreign Key yapısını kullanarak faces üzerinden photos tablosundaki URL'leri çekiyoruz
            response = supabase.table("faces") \
                .select("photos(image_url)") \
                .eq("cluster_id", selected_cluster_id) \
                .execute()
            
            if response.data:
                # Bir kişi aynı fotoğrafta birden fazla algılanmış olabilir (nadiren),
                # bu yüzden URL'leri set() ile benzersiz (unique) yapıyoruz.
                unique_urls = list(set(
                    row["photos"]["image_url"] 
                    for row in response.data 
                    if row.get("photos") and row["photos"].get("image_url")
                ))
                
                st.success(f"{selected_label} için toplam {len(unique_urls)} orijinal fotoğraf bulundu.")
                
                # 4. Orijinal fotoğrafları ızgara (Grid) yapısında göster
                cols_per_row = 3
                for i in range(0, len(unique_urls), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j in range(cols_per_row):
                        if i + j < len(unique_urls):
                            url = unique_urls[i + j]
                            with cols[j]:
                                # Tam boy orijinal fotoğraf gösteriliyor (Kırpılmış yüz değil)
                                st.image(url, use_container_width=True)
            else:
                st.warning("Bu kişiye ait fotoğraf bulunamadı.")
                
        except Exception as e:
            st.error(f"Fotoğraflar çekilirken hata oluştu: {e}")
