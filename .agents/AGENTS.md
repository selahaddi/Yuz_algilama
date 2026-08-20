# Project-Scoped Rules for AI Agents

## 1. Mimari Prensipler (Architecture Principles)
- **Frontend Kesinlikle Streamlit Değildir:** Eski prototipten kalma `app.py` veya `studio_app.py` dosyaları artık canlı web sitesini temsil YETMEZ. Her türlü arayüz ve frontend işlemi **sadece `public/` dizini içindeki (HTML/JS/CSS)** dosyalara yapılmalıdır. Vercel üzerinden bu klasör hizmet vermektedir.
- **Backend Kesinlikle Cloud Run (FastAPI):** Projede arka uç olarak çalışan sistem `guest_api.py` adlı FastAPI uygulamasıdır. Backend güncellemeleri yapıldığında Google Cloud Run `guest-api` servisi yeniden derlenmelidir (Build & Deploy).
- **Yüz Tanıma (AI Worker):** AI işlemleri `worker.py` içinde InsightFace `buffalo_s` kullanılarak asenkron `ThreadPoolExecutor` ile yapılır. Bu servis Cloud Run Jobs üzerinde `face-worker-job` adıyla çalışır.
- **Vercel Konfigürasyonu:** `vercel.json` dosyası kök dizinde kalmalıdır ve sadece Vercel yönlendirmelerini (API rewrites) içermelidir. Vercel Root Directory ayarı kullanılmamaktadır, output doğrudan public'e eşlenmiştir.

## 2. Maliyet ve Optimizasyon Kuralları (Cost Optimization)
- Yüz tanıma işlemi (storage'a yazma süreci) öncesinde `public/studio.js` içinde `resizeImage` canvas fonksiyonu mevcuttur. Storage maliyetini önlemek için asla yüksek çözünürlüklü fotoğraflar doğrudan Supabase'e kaydedilmemelidir, tarayıcıda küçültülmelidir.
- Veritabanı şişkinliğini önlemek için `cleanup_events.py` aktif tutulmalıdır. Yeni veri tabloları oluşturulurken hep Storage maliyetleri dikkate alınmalıdır.

## 3. Kod ve Deployment Akışı
- Frontend (Vercel) değişikliği için: Localde düzenle -> `git add` -> `git commit` -> `git push origin master`.
- Backend (Cloud Run) değişikliği için: Localde düzenle -> `gcloud builds submit` -> `gcloud run deploy guest-api`.
