# Project-Scoped Rules for AI Agents

## 1. Mimari Prensipler (Architecture Principles)
- **Frontend sadece `public/` dizinindedir.** Tüm arayüz (HTML/JS/CSS) dosyaları `public/` klasöründe bulunur. Vercel üzerinden bu klasör hizmet vermektedir. Projede Streamlit **yoktur ve kullanılmaz**.
- **Backend Kesinlikle Cloud Run (FastAPI):** Projede arka uç olarak çalışan sistem `guest_api.py` adlı FastAPI uygulamasıdır. Backend güncellemeleri yapıldığında Google Cloud Run `guest-api` servisi yeniden derlenmelidir (Build & Deploy). CPU-heavy resim işleyen endpoint'ler (`/api/search_selfie`) event-loop kilitlememesi için senkron (`def`) yazılmalıdır.
- **Yüz Tanıma (AI Worker):** AI işlemleri `worker.py` içinde InsightFace `buffalo_s` kullanılarak asenkron `ThreadPoolExecutor` ile yapılır. Bu servis Cloud Run Jobs üzerinde `face-worker-job` adıyla çalışır. ONNX Runtime çökmesini engellemek için `analyze_image` çağrıları thread lock ile korunur.
- **Vercel Konfigürasyonu:** `vercel.json` dosyası `public/` dizininde bulunur ve sadece Vercel yönlendirmelerini (API rewrites) içerir. Vercel Root Directory ayarı `public/` olarak yapılandırılmıştır.

## 2. Maliyet ve Optimizasyon Kuralları (Cost Optimization)
- Yüz tanıma işlemi (storage'a yazma süreci) öncesinde `public/studio.js` içinde `resizeImage` canvas fonksiyonu mevcuttur. `blueimp-load-image` ile EXIF yönelim verisi korunarak resmi döndüren ve küçülten yapı korunmalıdır. Storage maliyetini önlemek için asla yüksek çözünürlüklü fotoğraflar doğrudan Supabase'e kaydedilmemelidir, tarayıcıda küçültülmelidir.
- **Filigran (Watermark) Optimizasyonu:** Storage maliyetlerini düşürmek ve orijinalliği korumak için Supabase'e her zaman fotoğrafın **1920px'e küçültülmüş ama filigransız orijinal hali** yüklenir. Filigran, sunucuda (veya upload aşamasında canvas'ta) fotoğrafa kalıcı olarak (burn-in) işlenmez. Misafir fotoğraflara bakarken (Frontend), filigran `watermark-overlay` CSS sınıfı ile dinamik olarak resmin üzerine bindirilir.
- Veritabanı şişkinliğini önlemek için `cleanup_events.py` aktif tutulmalıdır. Yeni veri tabloları oluşturulurken hep Storage maliyetleri dikkate alınmalıdır.

## 3. Kod ve Deployment Akışı
- Frontend (Vercel) değişikliği için: Localde düzenle -> `git add` -> `git commit` -> `git push origin master`.
- Backend (Cloud Run) değişikliği için: Localde düzenle -> `gcloud builds submit` -> `gcloud run deploy guest-api --region europe-west4`. 
  - **DİKKAT (Bölge Uyuşmazlığı):** Vercel'deki (`public/vercel.json`) API yönlendirmesi `guest-api`'nin `europe-west4` bölgesindeki adresine (https://guest-api-398389727192.europe-west4.run.app) gitmektedir. `guest-api` sunucusu mutlaka `europe-west4`'e deploy edilmelidir. Yüz tanıma işlemi (`face-worker-job`) ise `europe-west1`'dedir; bu yüzden `guest_api.py` içerisinde işleyiciyi tetikleyen URL'de bölge sabit olarak `europe-west1` verilmelidir. (Ortam değişkeninden dinamik bölge okunursa 404 hatası alınır ve hata yutulduğu için sessizce takılır).

## 4. Yapay Zeka (AI) ve Yüz Tanıma Parametreleri
- **Eşik Değerleri (Thresholds):** Sistemdeki yüz tanıma doğruluğunu artırmak ve uzaktaki küçük yüzleri tespit edebilmek için sabit değerler şu şekildedir:
  - `MIN_FACE_SIZE = 50` (Piksel cinsinden minimum yüz boyutu)
  - `MIN_DET_SCORE = 0.70` (Minimum yüz tespit doğruluk skoru)
  - `MIN_BLUR_SCORE = 15.00` (Minimum bulanıklık eşiği)
- Bu değerler `worker.py` ve `tests/test_app.py` içinde standart olarak korunmalıdır.

## 5. API ve Routing Kuralları
- **FastAPI Statik Dosya Hizmeti:** `guest_api.py` içinde statik dosyaları servis etmek için kullanılan `app.mount("/", StaticFiles(directory="public", html=True), name="public")` satırı **DAİMA dosyanın en sonunda** bulunmalıdır. Aksi takdirde, POST ve diğer API route'larını engelleyip `405 Method Not Allowed` hatasına yol açar.
- **Frontend ID Parametreleri:** Veritabanından (Supabase) fotoğraf verisi çekerken `id` alanı daima sorgulanmalı ve frontend'e iletilmelidir. İstemci tarafında seçim işlemlerinin (örneğin sepet) sorunsuz çalışması için eşsiz bir ID elzemdir.
