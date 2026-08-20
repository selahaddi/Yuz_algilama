import streamlit as st
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.face_analyzer import FaceAnalyzer

st.set_page_config(page_title="Yüz Filtre Test Aracı", layout="wide", page_icon="🧪")

@st.cache_resource
def get_analyzer():
    return FaceAnalyzer(gpu_id=0)

st.title("🧪 Yüz Filtre Test Aracı")
st.markdown("Arka plandaki yüzleri elemek için doğru değerleri buradan interaktif olarak test edebilirsiniz.")

DIR = "/home/selahaddin/Belgeler/denemeresim"

if not os.path.exists(DIR):
    st.error(f"Klasör bulunamadı: {DIR}")
    st.stop()

images = sorted([f for f in os.listdir(DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
if not images:
    st.warning("Klasörde resim bulunamadı.")
    st.stop()

# Session state navigasyonu
if 'sb_select_box' not in st.session_state:
    st.session_state.sb_select_box = images[0]

# ─── Sol Menü: Ayarlar ────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Filtre Ayarları")

min_face_size = st.sidebar.slider("MIN_FACE_SIZE (Boyut)", 20, 300, 120, 5, 
                                  help="Piksel cinsinden yüzün minimum genişliği/yüksekliği.")
min_det_score = st.sidebar.slider("MIN_DET_SCORE (Doğruluk)", 0.0, 1.0, 0.7, 0.05,
                                  help="Yapay zekanın tespit ettiği bölgenin yüz olma ihtimali.")
min_blur_score = st.sidebar.slider("MIN_BLUR_SCORE (Bulanıklık)", 0.0, 100.0, 15.0, 1.0,
                                   help="Netlik sınırı.")

st.sidebar.markdown("---")
st.sidebar.header("🖼️ Resim Seçimi")

# İleri - Geri Fonksiyonları
def prev_image():
    idx = images.index(st.session_state.sb_select_box)
    if idx > 0:
        st.session_state.sb_select_box = images[idx - 1]

def next_image():
    idx = images.index(st.session_state.sb_select_box)
    if idx < len(images) - 1:
        st.session_state.sb_select_box = images[idx + 1]

current_idx = images.index(st.session_state.sb_select_box)

col_sb1, col_sb2 = st.sidebar.columns(2)
with col_sb1:
    st.button("⬅️ Önceki", on_click=prev_image, disabled=(current_idx == 0), use_container_width=True)
with col_sb2:
    st.button("Sonraki ➡️", on_click=next_image, disabled=(current_idx == len(images) - 1), use_container_width=True)

# Selectbox ile de seçebilmesini sağla
selected_image = st.sidebar.selectbox(
    "Veya Listeden Seç:", 
    images, 
    key="sb_select_box"
)

current_image_name = selected_image

st.sidebar.markdown("---")
st.sidebar.info("💡 Ayarları değiştirdiğinizde sonuçlar anında güncellenir.")

# ─── Ana Sayfa Navigasyon Çubuğu ─────────────────────────────────────────────
nav_c1, nav_c2, nav_c3 = st.columns([1, 3, 1])

with nav_c1:
    st.button("⬅️ Önceki Resim", key="main_prev", on_click=prev_image, disabled=(current_idx == 0), use_container_width=True)

with nav_c2:
    st.markdown(f"<h4 style='text-align: center; margin:0;'>[{current_idx + 1} / {len(images)}] {current_image_name}</h4>", unsafe_allow_html=True)

with nav_c3:
    st.button("Sonraki Resim ➡️", key="main_next", on_click=next_image, disabled=(current_idx == len(images) - 1), use_container_width=True)

st.markdown("---")

# ─── Analiz ve Gösterim ────────────────────────────────────────────────────────
analyzer = get_analyzer()
filepath = os.path.join(DIR, current_image_name)

# Resmi oku
img_cv2 = cv2.imread(filepath)
if img_cv2 is None:
    st.error("Resim okunamadı.")
    st.stop()

img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)

with st.spinner("Yüzler analiz ediliyor..."):
    faces = analyzer.analyze_image(img_cv2)

# Çizim için PIL kopyası
pil_img = Image.fromarray(img_rgb)
draw = ImageDraw.Draw(pil_img)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
except Exception:
    font = ImageFont.load_default()

face_details = []

for i, face in enumerate(faces):
    bbox = face.bbox
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    det_score = face.det_score
    
    # Bulanıklık Skoru
    crop_img = img_cv2[max(0, int(y1)):min(img_cv2.shape[0], int(y2)), 
                   max(0, int(x1)):min(img_cv2.shape[1], int(x2))]
    blur_score = 0
    if crop_img.size > 0:
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
    # Filtreleri uygula
    reasons = []
    if width < min_face_size or height < min_face_size:
        reasons.append("Boyut çok küçük")
    if det_score < min_det_score:
        reasons.append("Doğruluk düşük")
    if blur_score < min_blur_score:
        reasons.append("Çok bulanık")
        
    is_valid = len(reasons) == 0
    
    # Yüzün etrafına kutu çiz (Kabul = Yeşil, Red = Kırmızı)
    box_color = "green" if is_valid else "red"
    draw.rectangle([x1, y1, x2, y2], outline=box_color, width=8)
    
    # Numarayı yaz (Kutunun üstüne)
    text_label = f"#{i+1}"
    draw.text((x1, max(0, y1 - 45)), text_label, fill=box_color, font=font)
    
    # Detay listesine ekle
    face_details.append({
        "id": i + 1,
        "crop": cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB),
        "width": width,
        "height": height,
        "det_score": det_score,
        "blur_score": blur_score,
        "is_valid": is_valid,
        "reasons": reasons
    })

# 1. Tam resmi göster (Kutulu)
st.image(pil_img, use_container_width=True)

st.markdown("---")
st.subheader(f"🕵️‍♂️ Yüz Detayları (Bulunan: {len(faces)} Yüz)")

# 2. Her bir yüzü tek tek kırpılmış olarak ve verileriyle göster
if face_details:
    cols_per_row = 4
    for i in range(0, len(face_details), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(face_details):
                detail = face_details[i + j]
                
                with cols[j]:
                    with st.container(border=True):
                        st.markdown(f"**Yüz #{detail['id']}**")
                        st.image(detail['crop'], use_container_width=True)
                        
                        st.markdown(f"**Boyut:** {detail['width']:.0f} x {detail['height']:.0f}")
                        st.markdown(f"**Skor:** {detail['det_score']:.3f}")
                        st.markdown(f"**Bulanıklık:** {detail['blur_score']:.1f}")
                        
                        if detail['is_valid']:
                            st.success("✅ KABUL")
                        else:
                            st.error("❌ REDDEDİLDİ")
                            for reason in detail['reasons']:
                                st.caption(f"- {reason}")
else:
    st.info("Bu resimde yüz bulunamadı.")
