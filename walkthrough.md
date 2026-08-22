# Özellik Geliştirme Turu (Walkthrough)

Stüdyo ve Misafir arayüzleri için talep ettiğiniz tüm geliştirmeler tamamlandı. İşte eklenen yeni özellikler ve sistemdeki işleyişleri:

## 1. Stüdyo Paneli Geliştirmeleri (`studio.html` & `studio.js`)

- **Stüdyo Ayarları (White-label):** Sol menüye eklenen "Ayarlar" butonu ile tema rengi (HEX), Logo URL'si ve Filigran Metni belirlenebiliyor. Bu ayarlar veritabanında saklanarak misafir arayüzünü dinamik olarak şekillendiriyor.
- **Etkinlik Fiyatlandırması:** Yeni etkinlik oluşturulurken "Fotoğraf Fiyatı" (TL) girilebiliyor. Fiyat 0 (sıfır) bırakılırsa, misafir sitesinde fotoğraflar "Ücretsiz" olarak görünüyor.
- **QR Kod Oluşturucu:** Etkinlik detay ekranındaki "QR Kod" butonu tıklandığında, misafir linkine yönlendiren bir QR kod modalı açılıyor. Bu kod anında indirilebiliyor.
- **Gelişmiş Fotoğraf Yükleyici:** Yükleme işlemi sırasında "Duraklat" ve "Devam Et" butonları eklendi. Ayrıca stüdyo ayarlarında bir "Filigran Metni" belirlenmişse, tarayıcı tarafında küçültme (resize) yapılırken doğrudan resim üzerine filigran basılıyor.
- **Sipariş Takibi:** Dashboard üzerindeki istatistiklere, etkinlik bazlı "Bekleyen Sipariş" sayısı eklendi.

## 🐛 Troubleshooting & Bug Fixes

**1. SyntaxError in `index.html` (Unescaped Single Quotes)**
- **Issue:** The `photo.id` or other string fields in `encodedPhoto` occasionally contained single quotes (or string formats like `photo_id` were mismatched), breaking the HTML string injection in `index.html`.
- **Fix:** Used `.replace(/'/g, "%27")` after `encodeURIComponent(JSON.stringify(photo))` to ensure the generated HTML `onclick` handler doesn't break due to unescaped quotes.

**2. Photo Selection Bug (Selecting One Selects All)**
- **Issue:** The frontend was attempting to use `photo.id` for each photo to handle selection uniquely. However, some API endpoints (`/api/cluster_photos`) did not return the `id` field from the database, meaning `photo.id` was `undefined`. This resulted in all photos having `data-photo-id="undefined"`, causing mass-selection when one photo was clicked.
- **Fix:** 
    - Updated `guest_api.py` to ensure `id` is retrieved and returned from the `photos` table.
    - Updated `index.html` to fallback to `photo.photo_id` if `photo.id` is missing.

**3. Checkout Order Error (Method Not Allowed)**
- **Issue:** When submitting an order, the `/api/order` endpoint returned a `405 Method Not Allowed` error. This happened because `app.mount("/", StaticFiles(directory="public", html=True))` was placed *before* the order POST route in `guest_api.py`, intercepting the request and assuming it was a request for a static file (which only accepts GET).
- **Fix:** Moved `app.mount` to the very bottom of `guest_api.py` so all API routes take precedence before falling back to static files.

## 2. Misafir Arayüzü Geliştirmeleri (`index.html`)

- **PWA (Progressive Web App) Desteği:** `manifest.json` ve `sw.js` (Service Worker) dosyaları eklendi. Kullanıcılar artık siteyi ana ekranlarına bir uygulama gibi ekleyebilirler.
- **Dinamik Tema Uygulaması:** Stüdyo ayarlarından gelen "Ana Renk" (Primary Color) ve "Logo", sayfa yüklendiğinde Tailwind renklerini ezecek şekilde (CSS değişkenleri benzeri bir mantıkla) dinamik olarak uygulanıyor.
- **Sepet ve Satın Alma (Cart):**
  - Fotoğraf kartlarına seçim (Checkbox) özelliği eklendi. Tıklandığında fotoğraf sepete ekleniyor.
  - Alttan yapışkanlı olarak çıkan Sepet çubuğu, kaç fotoğraf seçildiğini ve stüdyonun belirlediği fiyata göre toplam tutarı gösteriyor.
  - Fotoğraflar ücretsizse "Sipariş İste", ücretliyse "Satın Al / Sipariş Ver" butonu çıkıyor. Sipariş butonu ile isim ve iletişim bilgisi alınarak veritabanındaki `orders` tablosuna kayıt atılıyor.
- **Toplu İndirme:** Sepet çubuğundaki "İndir (ZIP)" butonu `jszip` ve `FileSaver.js` kullanarak seçilen tüm fotoğrafları tek bir ZIP dosyası halinde indiriyor.
- **Tam Ekran Görünüm (Lightbox) ve Hata Bildirimi:** Fotoğraf kartlarındaki büyüteç ikonuna tıklandığında açılan tam ekran modalı içerisine "Bu ben değilim" butonu eklendi. Bu buton sayesinde yanlış eşleşmeler `feedbacks` tablosuna bildiriliyor.
- **Grup Özçekim Modu:** Selfie ile arama sekmesine "Herhangi biri yeterli" ve "Sadece hepimizin bir arada oldukları" şeklinde bir açılır liste eklendi. Bu değer arka uçtaki `search_mode` (single/all) parametresini tetikliyor.

## 3. Doğrulama (Verification)

1. Backend API (`/api/order`, `/api/feedback`, `/api/search_selfie`) tarafının bu özellikleri destekleyecek şekilde güncellendiği ve veritabanı tablolarının önceki seansta yaratıldığı doğrulandı.
2. `public` dizininde oluşturulan yeni mantıkların Vercel üzerinden başarıyla sunulabileceği, statik dosya yapıları içerisinde çalıştığı kontrol edildi.
3. Canvas filigran işleyişi sadece `thumbnail_url` üzerinden çalışacak şekilde asenkron yükleme (queue) fonksiyonuna dahil edildi. (Optimizasyon: Storage alanından ve bandwidth'ten tasarruf edildi.)

Artık bu değişiklikleri yerelinizde `npm run dev` ile (veya `python -m http.server 8000` public dizininde) başlatarak veya doğrudan Vercel üzerinden (commit/push sonrası) test edebilirsiniz.
