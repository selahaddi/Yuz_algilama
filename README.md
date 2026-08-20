# 👥 Yüz Tanıma SaaS - Fotoğraf Stüdyosu Yönetim Sistemi

Bu proje, düğün ve etkinlik fotoğrafçıları için geliştirilmiş, yapay zeka tabanlı bir yüz tanıma ve fotoğraf dağıtım SaaS (Software as a Service) uygulamasıdır.

Sistem, yüklenen fotoğraflardaki yüzleri tespit eder, benzerliklerine göre otomatik kümelendirir ve stüdyoların yüzlerce etkinlik fotoğrafını misafirlerin kendi yüzlerini bularak saniyeler içinde alabilmesini sağlar.

## 🌟 Öne Çıkan Özellikler

- **Gözetimsiz Öğrenme (DBSCAN) ve AI:** InsightFace (`buffalo_s`) modeli ile veri tabanına önceden kayıtlı yüze ihtiyaç duymadan yüz haritası çıkarımı.
- **Bulut Mimarisi & Paralel İşleme:** Google Cloud Run üzerinde çalışan `FastAPI` (Guest API) ve arka planda `worker.py` (Cloud Run Job) ile 4'erli paralel işleme mimarisi (ThreadPool).
- **İstemci Taraflı Optimizasyon:** HTML Canvas ile yüklenen fotoğraflar Vercel frontend tarafında tarayıcıda 1920px (FHD) boyutuna sıkıştırılır; Storage maliyetlerinden %90 tasarruf sağlanır.
- **Gerçek Zamanlı Veritabanı:** Supabase PostgreSQL ve Storage ile anlık etkinlik/fotoğraf yönetimi.
- **Otomatik Temizlik (Cost Saver):** `cleanup_events.py` scripti sayesinde 30 günü geçen eski etkinlikler Cloud Storage ve veritabanından otomatik silinir.

---

## 🛠️ Mimari ve Kullanılan Teknolojiler

Proje mimarisi frontend, backend ve yapay zeka worker'ı olmak üzere üçe ayrılmıştır. Lütfen eski Streamlit altyapısını dikkate almayın.

### 1. Frontend (Vercel)
- **Konum:** `public/` dizini.
- **Teknoloji:** Saf HTML, JS, CSS ve Supabase JS SDK.
- **Önemli Dosyalar:** `index.html` (Misafir yüz arama), `studio.html` (Fotoğrafçı paneli).
- **Yayınlama:** Vercel üzerinden GitHub bağlantılı olarak yayınlanır. `vercel.json` dosyasındaki kurallarla API çağrıları Google Cloud'a (`guest-api`) yönlendirilir.

### 2. Backend API (Google Cloud Run)
- **Konum:** `guest_api.py` (Kök dizin).
- **Teknoloji:** Python, FastAPI, Supabase Python Client.
- **İşlev:** Misafirlerin "Benim yüzümü bul" isteklerini alır, referans resimden embedding çıkarır ve veritabanındaki yüzleri kosinüs benzerliğine göre eşleştirir.

### 3. AI Worker Job (Google Cloud Run Jobs)
- **Konum:** `worker.py`, `core/face_analyzer.py`
- **Teknoloji:** Python, InsightFace (`buffalo_s`), Scikit-Learn (DBSCAN).
- **İşlev:** Stüdyo yeni fotoğraflar yüklediğinde arka planda tetiklenir. Yüzleri bulur, vektörleştirir ve gruplar. İşlemleri `ThreadPoolExecutor` ile asenkron yürütür.
- **Yüz Tanıma Eşikleri:** Uzaktaki/küçük yüzlerin tespiti için `MIN_FACE_SIZE = 20`, `MIN_DET_SCORE = 0.70`, `MIN_BLUR_SCORE = 15.00` olarak optimize edilmiştir.

---

## 🚀 Dağıtım (Deployment) Bilgileri

### Frontend (Vercel)
* Tüm arayüz (HTML/JS) kodları `public` klasöründedir.
* GitHub master dalına kod atıldığında (`git push origin master`) Vercel otomatik olarak günceller.
* Yönlendirmeler ana dizindeki `vercel.json` dosyası tarafından yönetilir.

### Backend ve Worker (Google Cloud)
Aşağıdaki komutlar üzerinden Google Cloud'a `gcloud` ile Docker imajı olarak yollanır:
```bash
# Proje ID ve Region
PROJECT_ID=$(cat gcp_project_id.txt)
REGION="europe-west1"
IMAGE="europe-west1-docker.pkg.dev/${PROJECT_ID}/yuz-tanima-repo/app-image:latest"

# 1. Image Build Etme
gcloud builds submit --tag $IMAGE --project=$PROJECT_ID

# 2. Guest API Güncelleme
gcloud run deploy guest-api --image $IMAGE --cpu 2 --min-instances 1 --region $REGION --project $PROJECT_ID

# 3. Worker Job Güncelleme
gcloud run jobs update face-worker-job --image $IMAGE --cpu 2 --region $REGION --project $PROJECT_ID
```
