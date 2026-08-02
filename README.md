# 👥 Yüz Tanıma ve Kategorizasyon Sistemi

Bu proje, sisteme yüklenen fotoğraflardaki yüzleri tespit eden ve kimliklerinin önceden sisteme tanıtılmasına (veri girişi yapılmasına) gerek kalmadan, tamamen yüz özelliklerinin benzerliğine göre kişileri otomatik olarak gruplandıran yapay zeka tabanlı bir Streamlit web uygulamasıdır.

## 🌟 Öne Çıkan Özellikler

- **Gözetimsiz Öğrenme ile Gruplandırma:** Sistem, veri tabanına kayıtlı yüzlere ihtiyaç duymaz. Resimdeki tüm yüzleri tarar, her birinin haritasını (embedding) çıkarır ve benzer olanları "Kişi 1", "Kişi 2" şeklinde otomatik olarak kümeler.
- **Ekran Kartı (GPU) Hızlandırması:** Ağır yapay zeka işlemlerinin milisaniyeler içerisinde gerçekleşmesi için NVIDIA GTX 1650 Ti GPU desteği (CUDA & ONNXRuntime) entegre edilmiştir.
- **Hassasiyet Ayarı (Confidence Threshold):** Yanlış tespitleri ve düşük çözünürlüklü/bozuk yüzlerin analize dahil olmasını engellemek için sol menüden ayarlanabilen dinamik bir yüz tespit doğruluk sınırı filtresi bulunur. Yüzler ekrana basılırken altlarında tespit doğruluk oranları (Örn: `%98.5`) yer alır.
- **Kullanıcı Dostu Web Arayüzü:** Çoklu dosya seçimi, modern tasarım, yükleme animasyonları ve şık bir ızgara (grid) görünümü sunan Streamlit altyapısı.
- **Tak & Çalıştır Script:** Bağımlılıkların ve Python sanal ortamının (venv) otomatik kurulumunu üstlenen hazır bir Bash scripti (`baslat.sh`) içerir.

---

## 🛠️ Kullanılan Teknolojiler

- **[InsightFace](https://github.com/deepinsight/insightface):** Derin öğrenme tabanlı, state-of-the-art 2D ve 3D yüz analiz kütüphanesi. Projede, yüz tespiti ve 512 boyutlu özellik vektörü (embedding) çıkarımı için varsayılan ve en yetenekli modeli olan `buffalo_l` kullanılmaktadır.
- **ONNXRuntime-GPU:** InsightFace modelinin NVIDIA CUDA çekirdekleri üzerinde yüksek performansla çalışmasını sağlayan inference (çıkarım) motoru.
- **Scikit-Learn (DBSCAN):** Yoğunluk tabanlı mekansal kümeleme algoritması. Yüzlerin birbirinden ne kadar uzak/yakın olduğunu "Kosinüs Uzaklığı (Cosine Distance)" metriği ile hesaplayarak, kaç farklı kişi olduğunu baştan bilmeye gerek duymadan dinamik gruplama (clustering) yapar.
- **Streamlit:** Python kodlarını hızlı ve interaktif web uygulamalarına dönüştüren açık kaynaklı UI kütüphanesi.
- **OpenCV & NumPy:** Görüntü matrislerinin (RGB/BGR) okunması, yüzlerin kırpılması ve matematiksel vektör işlemleri için.

---

## 📂 Proje Dosya Yapısı ve Mimari İşleyiş

```text
Yüz_Tanıma_&_Kategori/
├── core/
│   ├── face_analyzer.py   # InsightFace ile yüzleri bulan ve özelliklerini çıkaran modül
│   └── clusterer.py       # Scikit-learn DBSCAN ile yüzleri benzerliğe göre gruplayan modül
├── app.py                 # Streamlit web arayüzü ve uygulamanın ana akış kontrolörü
├── baslat.sh              # venv oluşturan, gereksinimleri kuran ve app.py'yi başlatan script
└── requirements.txt       # Projenin çalışması için gereken Python kütüphanelerinin listesi
```

### Akış Senaryosu (Pipeline)

1. **Giriş:** Kullanıcı web arayüzü üzerinden bir veya birden fazla resim dosyası seçer.
2. **Yüz Tespiti (Detection):** `FaceAnalyzer`, her bir resmi okur. Resimdeki yüzlerin koordinatlarını (Bounding Box) ve doğruluk puanını (Det Score) çıkarır.
3. **Filtreleme:** Ayarlanan "Yüz Tespit Doğruluk Sınırı" (örn: %50) altında kalan yüzler, gürültü/hata varsayılarak elenir.
4. **Özellik Çıkarımı (Embedding):** Kalan her bir geçerli yüz için 512 boyutlu sayısal bir "kimlik dizisi (embedding)" oluşturulur ve yüz resimden kırpılarak belleğe alınır.
5. **Kümeleme (Clustering):** Toplanan tüm yüz kimlik dizileri (embeddings) `FaceClusterer` modülüne yollanır. DBSCAN algoritması, bu vektörler arasındaki açısal farkları (kosinüs benzerliği) ölçer. Birbirine yakın olan vektörler aynı "Kişi" ID'sini (etiketini) alır. Birbirine hiç benzemeyen veya çok uzak kalan vektörler "Gürültü (-1)" olarak etiketlenir.
6. **Çıkış:** `app.py`, dönen etiketleri işleyerek aynı ID'ye sahip kırpılmış yüz görsellerini arayüzde alt alta, gruplar halinde ekrana basar.

---

## 🚀 Kurulum ve Çalıştırma

Proje dosyalarının bulunduğu dizine terminalden girerek başlatma scriptini çalıştırmanız yeterlidir. Script, ilk çalıştırmada sizin yerinize bir `venv` oluşturacak, `requirements.txt` içerisindeki tüm bağımlılıkları indirecek ve sunucuyu başlatacaktır.

```bash
# Proje dizinine geçiş yapın
cd "/home/selahaddin/Belgeler/Yüz_Tanıma_&_Kategori"

# Betiği çalıştırılabilir yapın (gerekliyse)
chmod +x baslat.sh

# Uygulamayı başlatın
./baslat.sh
```

**Not:** İlk analiz işleminde uygulamanın kullanacağı yapay zeka ağırlık dosyası (`buffalo_l` - ~330 MB) otomatik olarak indirileceği için kısa bir bekleme yaşanabilir. Sonraki analizler doğrudan diske önbelleklenmiş model üzerinden çok daha hızlı gerçekleşecektir.
