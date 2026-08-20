# 🤖 Yüz Tanıma SaaS - AI Onboarding (Projeye Giriş Rehberi)

> **Yapay Zeka Asistanı İçin Not:** Eğer bu dosyayı okuyorsan, kullanıcı yeni bir göreve başlıyor demektir. Lütfen aşağıdaki mimariyi, kuralları ve proje yapısını dikkatlice oku. Projede asla Streamlit kullanılmamaktadır!

## 1. Proje Özeti
Bu proje, düğün ve etkinlik fotoğrafçıları için yapay zeka tabanlı yüz tanıma SaaS platformudur. 
Misafirler, stüdyonun paylaştığı link üzerinden kendi selfielerini yükler ve binlerce etkinlik fotoğrafı arasından sadece kendi yüzlerinin bulunduğu fotoğrafları bulurlar.

## 2. Kullanılan Teknolojiler ve Mimari
Sistem 3 ana parçadan oluşmaktadır:

### A. Frontend (İstemci - Vercel)
- **Konum:** Sadece `public/` dizini.
- **Teknoloji:** Saf HTML, JS, CSS, TailwindCSS ve Supabase JS SDK.
- **Kritik Dosyalar:** 
  - `public/index.html` & `public/app.js` (Misafir Yüz Arama Arayüzü)
  - `public/studio.html` & `public/studio.js` (Fotoğrafçı Yönetim Paneli)
  - `public/config.js` (API ve Supabase Key ayarları)
- **Önemli Kural:** Storage maliyetlerini düşürmek için fotoğraflar Supabase'e yüklenmeden önce **mutlaka tarayıcıda Canvas ile 1920px'e** küçültülür (`studio.js` -> `resizeImage`).

### B. Backend API (Google Cloud Run)
- **Konum:** Kök dizindeki `guest_api.py`
- **Teknoloji:** Python, FastAPI, Supabase Python Client.
- **İşlev:** Vercel üzerinden gelen API isteklerini karşılar (`/api/search_selfie`, `/api/trigger_worker` vb.).
- **Önemli:** InsightFace modeli burada "Lazy Loading" ile (sadece selfie arandığında) yüklenir. Cloud Run deploy edilirken `uvicorn guest_api:app` komutu ile başlatılır.

### C. AI Worker (Google Cloud Run Jobs / Background Task)
- **Konum:** Kök dizindeki `worker.py` ve `core/` klasörü.
- **Teknoloji:** Python, InsightFace (`buffalo_s`), Scikit-Learn (DBSCAN).
- **İşlev:** Stüdyo yeni fotoğraflar yüklediğinde arka planda çalışır. Yüzleri tespit eder, 512 boyutlu vektör (embedding) çıkarır ve benzer yüzleri DBSCAN ile kümelendirir.
- **Yüz Eşikleri:** Uzaktaki yüzleri kaçırmamak için: `MIN_FACE_SIZE = 20`, `MIN_DET_SCORE = 0.70`, `MIN_BLUR_SCORE = 15.00`.

## 3. Veritabanı Yapısı (Supabase PostgreSQL)
- **studios:** Kayıtlı fotoğrafçıları tutar.
- **events:** Düğün/Etkinlik bilgilerini tutar.
- **photos:** Yüklenen etkinlik fotoğraflarının Storage URL'lerini tutar.
- **faces:** Fotoğraflarda tespit edilen her bir yüzün embedding vektörünü (`vector(512)` pgvector) tutar. Yüz arama burada cosine distance ile yapılır.

## 4. Deployment (Yayınlama) Süreçleri
- **Frontend:** GitHub `master` dalına pushlandığında Vercel otomatik derler. `public/` dizini serve edilir.
- **Backend / Worker:** `gcloud` ile Google Cloud'a deploy edilir. 
  ```bash
  # API için:
  gcloud run deploy guest-api --image $IMAGE --command="uvicorn" --args="guest_api:app,--host=0.0.0.0,--port=8080"
  
  # Worker için:
  gcloud run jobs update face-worker-job --image $IMAGE
  ```

## 5. Kritik Dosya İşlemleri (Önemli Uyarılar)
1. Backend kütüphanesi eklenecekse **sadece `requirements-all.txt`** güncellenir.
2. Vercel yönlendirmeleri **sadece `public/vercel.json`** üzerinden yapılır.
3. Kullanılmayan eski (legacy) dosyalar projeden tamamen temizlenmiştir. Yeniden `st.write` vb. Streamlit kodları **üretilmemelidir**.
