import os
import time
import requests
import numpy as np
import cv2
from supabase import create_client, Client
from dotenv import load_dotenv

# Yapay Zeka Modüllerini İçe Aktar
from core.face_analyzer import FaceAnalyzer
from core.clusterer import FaceClusterer

# .env dosyasındaki ortam değişkenlerini yükle
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "BURAYA_SUPABASE_URL_GELECEK")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "BURAYA_SUPABASE_ANON_VEYA_SERVICE_KEY_GELECEK")

# URL ve Key tanımlanmamışsa uyar
if SUPABASE_URL == "BURAYA_SUPABASE_URL_GELECEK":
    print("UYARI: Lütfen .env dosyanızı oluşturup SUPABASE_URL ve SUPABASE_KEY değerlerinizi giriniz.")
    # Şimdilik devam ediyoruz, ancak bağlantı başarısız olabilir

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Supabase Client oluşturulamadı: {e}")

def update_clusters(clusterer: FaceClusterer):
    """
    Tüm veritabanındaki yüz vektörlerini çeker, yeniden kümeleme (DBSCAN) yapar
    ve sonuçları veritabanında günceller.
    """
    print("Tüm yüzler veritabanından çekiliyor ve yeniden kümeleniyor...")
    
    # Tüm yüzleri ve vektörleri çek
    response = supabase.table("faces").select("id, embedding").execute()
    faces_data = response.data
    
    if not faces_data:
        print("Veritabanında yüz bulunamadı.")
        return
        
    embeddings = []
    face_ids = []
    
    for row in faces_data:
        face_ids.append(row["id"])
        emb = row["embedding"]
        
        # pgvector veriyi string "[0.1, 0.2, ...]" olarak veya liste olarak döndürebilir.
        if isinstance(emb, str):
            import ast
            emb = ast.literal_eval(emb)
            
        embeddings.append(np.array(emb, dtype=np.float32))
        
    # Kümeleme (DBSCAN) yap
    labels = clusterer.cluster(embeddings)
    
    # Küme kimliklerini (cluster_id) güncelle
    for face_id, label in zip(face_ids, labels):
        supabase.table("faces").update({"cluster_id": label}).eq("id", face_id).execute()
        
    unique_people = len(set(label for label in labels if label != -1))
    print(f"Kümeleme tamamlandı! {len(faces_data)} yüz, {unique_people} farklı kişiye atandı.")


def start_worker():
    print("Yapay Zeka Modelleri Yükleniyor (GPU aktif)...")
    analyzer = FaceAnalyzer(gpu_id=0)
    clusterer = FaceClusterer(eps=0.45)
    print("✅ Worker Başlatıldı ve Supabase Kuyruğunu (Queue) Dinliyor...")

    while True:
        try:
            # 1. Kuyruktan işlenmemiş 1 adet fotoğraf al
            res = supabase.table("photos").select("*").eq("processed", False).limit(1).execute()
            
            if res.data:
                photo = res.data[0]
                photo_id = photo["id"]
                url = photo["image_url"]
                
                print(f"⏳ Yeni fotoğraf işleniyor: {url}")
                
                # 2. İnternetten orijinal fotoğrafı indir ve OpenCV formatına çevir
                try:
                    response = requests.get(url, timeout=15)
                    response.raise_for_status() # Hata varsa tetikler
                    image_np = np.frombuffer(response.content, np.uint8)
                    img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
                except Exception as dl_err:
                    print(f"❌ Fotoğraf indirilemedi ({url}): {dl_err}")
                    # Hatalı fotoğrafı tekrar denememek için processed=True yapıyoruz
                    supabase.table("photos").update({"processed": True}).eq("id", photo_id).execute()
                    continue
                
                if img is not None:
                    # 3. Yüzleri tespit et ve vektörleri (embedding) çıkar
                    faces = analyzer.analyze_image(img)
                    print(f"   => Fotoğrafta {len(faces)} yüz bulundu.")
                    
                    for face in faces:
                        # Düşük tespit skoruna sahip yüzleri yoksay (Gürültü filtreleme)
                        if face.det_score < 0.5:
                            continue
                        
                        # NumPy arrayleri Python listelerine ve float türüne çevir
                        bbox = face.bbox.astype(float).tolist()
                        embedding = face.embedding.astype(float).tolist()
                        
                        # 4. Yüzleri Supabase 'faces' tablosuna kaydet
                        supabase.table("faces").insert({
                            "photo_id": photo_id,
                            "embedding": embedding,
                            "bbox": bbox,
                            "det_score": float(face.det_score)
                        }).execute()
                    
                    # 5. Yeni yüzler eklendiği için tüm sistemi tekrar kümele
                    if len(faces) > 0:
                        update_clusters(clusterer)
                
                # 6. İşlem bittiğinde kuyruktan (queue) çıkar
                supabase.table("photos").update({"processed": True}).eq("id", photo_id).execute()
                print(f"✅ Fotoğraf başarıyla işlendi ve kuyruktan çıkarıldı.")
                
            else:
                # Kuyruk boşsa bir süre bekle
                time.sleep(3)
                
        except Exception as e:
            print(f"❌ Beklenmeyen Hata: {e}")
            time.sleep(5) # Hata durumunda döngünün çökmemesi için bekleme

if __name__ == "__main__":
    start_worker()
