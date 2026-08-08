import os
import sys
import time
import json
import logging
import requests
import numpy as np
import cv2
from supabase import create_client, Client
from dotenv import load_dotenv

# Yapay Zeka Modüllerini İçe Aktar
from core.face_analyzer import FaceAnalyzer
from core.clusterer import FaceClusterer

# ─── Loglama Yapılandırması ────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # Terminale yaz
        logging.FileHandler(      # Dosyaya yaz
            os.path.join(LOG_DIR, "worker.log"),
            encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("worker")

# ─── Ortam Değişkenleri ───────────────────────────────────────────────────────
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
# Worker yalnızca service_role anahtarını kullanmalı (RLS'yi bypass eder)
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", ""))

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.critical("SUPABASE_URL ve/veya SUPABASE_SERVICE_KEY tanımlanmamış. .env dosyanızı kontrol edin.")
    sys.exit(1)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    logger.info("Supabase bağlantısı başarılı.")
except Exception as e:
    logger.critical(f"Supabase Client oluşturulamadı: {e}")
    sys.exit(1)

# ─── Yapılandırma Sabitleri ────────────────────────────────────────────────────
BATCH_SIZE = 5              # Her turda en fazla kaç fotoğraf işlensin
RECLUSTER_EVERY_N = 10      # Kaç fotoğraftan sonra yeniden kümeleme yapılsın
POLL_INTERVAL = 3            # Kuyruk boşken bekleme süresi (saniye)
ERROR_BACKOFF_INITIAL = 5    # İlk hata bekleme süresi (saniye)
ERROR_BACKOFF_MAX = 60       # Maksimum hata bekleme süresi (saniye)
MIN_FACE_SIZE = 120          # Piksel cinsinden minimum yüz boyutu (Arka planı elemek için artırıldı)
MIN_DET_SCORE = 0.7          # Minimum yüz tespit doğruluk skoru
MIN_BLUR_SCORE = 15.0        # Minimum bulanıklık eşiği (Laplacian varyansı)


def update_clusters(clusterer: FaceClusterer):
    """
    Tüm veritabanındaki yüz vektörlerini çeker, yeniden kümeleme (DBSCAN) yapar.
    Önceki küme atamaları ile karşılaştırarak kararlı (stabil) ID'ler atar
    ve sadece değişenleri veritabanında günceller.
    """
    logger.info("Tüm yüzler veritabanından çekiliyor ve yeniden kümeleniyor...")
    
    # Tüm yüzleri ve vektörleri çek
    response = supabase.table("faces").select("id, embedding, cluster_id").execute()
    faces_data = response.data
    
    if not faces_data:
        logger.info("Veritabanında yüz bulunamadı.")
        return
        
    embeddings = []
    face_ids = []
    old_cluster_ids = []
    
    for row in faces_data:
        face_ids.append(row["id"])
        old_cluster_ids.append(row.get("cluster_id"))
        emb = row["embedding"]
        
        # pgvector veriyi string "[0.1, 0.2, ...]" olarak veya liste olarak döndürebilir.
        if isinstance(emb, str):
            emb = json.loads(emb)
            
        embeddings.append(np.array(emb, dtype=np.float32))
        
    # Kümeleme (DBSCAN) yap
    new_labels = clusterer.cluster(embeddings)
    
    # ─── Küme Kararlılığı (Cluster Stability) ──────────────────────────────
    # DBSCAN her çalıştığında farklı sıra ile farklı ID'ler atayabilir.
    # Önceki atamaları referans alarak yeni ID'leri eşleştiriyoruz.
    stabilized_labels = _stabilize_cluster_ids(old_cluster_ids, new_labels)
    
    # ─── Toplu Güncelleme (Batch Update) ───────────────────────────────────
    # Sadece gerçekten değişen kayıtları güncelle (gereksiz API çağrısı önlenir)
    updates_count = 0
    for face_id, old_label, new_label in zip(face_ids, old_cluster_ids, stabilized_labels):
        if old_label != new_label:
            supabase.table("faces").update({"cluster_id": new_label}).eq("id", face_id).execute()
            updates_count += 1
        
    unique_people = len(set(label for label in stabilized_labels if label != -1))
    logger.info(
        f"Kümeleme tamamlandı! {len(faces_data)} yüz -> {unique_people} kişi. "
        f"{updates_count} kayıt güncellendi."
    )


def _stabilize_cluster_ids(old_ids: list, new_ids: list) -> list:
    """
    Yeni küme ID'lerini eski atamalara göre eşleştirip kararlı hale getirir.
    
    Mantık: Her yeni küme ID'si (new_label) için, o kümedeki yüzlerin
    çoğunluğunun daha önce hangi eski kümeye (old_label) ait olduğuna bakar.
    Böylece "Kişi 1" her zaman aynı kişiyi ifade eder.
    """
    if not old_ids or all(o is None for o in old_ids):
        # İlk kümeleme — doğrudan yeni ID'leri kullan
        return new_ids
    
    from collections import Counter
    
    # Yeni -> Eski eşleme tablosu oluştur
    new_to_old_votes = {}
    for old_id, new_id in zip(old_ids, new_ids):
        if new_id == -1:
            continue  # Gürültü noktalarını atla
        if new_id not in new_to_old_votes:
            new_to_old_votes[new_id] = Counter()
        if old_id is not None and old_id != -1:
            new_to_old_votes[new_id][old_id] += 1
    
    # Çoğunluk oylaması ile yeni->eski eşleme belirle
    new_to_stable = {}
    used_old_ids = set()
    
    # Önce en güçlü eşleşmeleri (en çok oy alanları) ata
    mapping_candidates = []
    for new_id, votes in new_to_old_votes.items():
        if votes:
            best_old_id, best_count = votes.most_common(1)[0]
            mapping_candidates.append((best_count, new_id, best_old_id))
    
    # En güçlü eşleşmeden zayıfa doğru sırala
    mapping_candidates.sort(reverse=True)
    
    for _, new_id, old_id in mapping_candidates:
        if old_id not in used_old_ids:
            new_to_stable[new_id] = old_id
            used_old_ids.add(old_id)
    
    # Eşleşemeyen yeni kümelere yeni ID ata
    max_existing_id = max(
        (oid for oid in old_ids if oid is not None and oid != -1),
        default=-1
    )
    next_id = max_existing_id + 1
    
    for new_id in set(new_ids):
        if new_id == -1:
            continue
        if new_id not in new_to_stable:
            new_to_stable[new_id] = next_id
            next_id += 1
    
    # Sonuç listesini oluştur
    return [
        -1 if label == -1 else new_to_stable.get(label, label)
        for label in new_ids
    ]


def process_single_photo(analyzer: FaceAnalyzer, photo: dict) -> int:
    """
    Tek bir fotoğrafı indir, analiz et ve geçerli yüzleri veritabanına kaydet.
    
    :return: Kaydedilen geçerli yüz sayısı
    """
    photo_id = photo["id"]
    url = photo["image_url"]
    
    logger.info(f"  Fotoğraf işleniyor: {url[:80]}...")
    
    # Fotoğrafı indir ve OpenCV formatına çevir
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        image_np = np.frombuffer(response.content, np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    except Exception as dl_err:
        logger.warning(f"Fotoğraf indirilemedi ({url[:60]}): {dl_err}")
        supabase.table("photos").update({"processed": True}).eq("id", photo_id).execute()
        return 0
    
    if img is None:
        logger.warning(f"Fotoğraf decode edilemedi: {url[:60]}")
        supabase.table("photos").update({"processed": True}).eq("id", photo_id).execute()
        return 0
    
    # Yüzleri tespit et ve vektörleri çıkar
    faces = analyzer.analyze_image(img)
    logger.info(f"   => Fotoğrafta {len(faces)} yüz bulundu.")
    
    valid_faces_count = 0
    for face in faces:
        bbox = face.bbox.astype(float).tolist()
        x1, y1, x2, y2 = bbox
        
        # 1. BOYUT FİLTRESİ
        width = x2 - x1
        height = y2 - y1
        if width < MIN_FACE_SIZE or height < MIN_FACE_SIZE:
            continue
            
        # 2. DOĞRULUK FİLTRESİ
        if face.det_score < MIN_DET_SCORE:
            continue
            
        # 3. BULANIKLIK FİLTRESİ
        try:
            crop_img = img[max(0, int(y1)):min(img.shape[0], int(y2)), 
                         max(0, int(x1)):min(img.shape[1], int(x2))]
            
            if crop_img.size > 0:
                gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
                blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                
                if blur_score < MIN_BLUR_SCORE:
                    continue
        except Exception:
            continue
        
        embedding = face.embedding.astype(float).tolist()
        
        # Geçerli yüzü Supabase'e kaydet
        supabase.table("faces").insert({
            "photo_id": photo_id,
            "embedding": embedding,
            "bbox": bbox,
            "det_score": float(face.det_score)
        }).execute()
        valid_faces_count += 1
        
    logger.info(f"   => {valid_faces_count} adet net/geçerli yüz kaydedildi.")
    
    # Fotoğrafı kuyruktan çıkar
    supabase.table("photos").update({"processed": True}).eq("id", photo_id).execute()
    
    return valid_faces_count


def start_worker():
    logger.info("Yapay Zeka Modelleri Yükleniyor (GPU aktif)...")
    analyzer = FaceAnalyzer(gpu_id=0)
    clusterer = FaceClusterer(eps=0.45)
    logger.info("Worker Başlatıldı ve Supabase Kuyruğunu (Queue) Dinliyor...")
    logger.info(f"   Yapılandırma: batch_size={BATCH_SIZE}, recluster_every={RECLUSTER_EVERY_N}")

    processed_since_cluster = 0
    error_backoff = ERROR_BACKOFF_INITIAL
    consecutive_errors = 0

    while True:
        try:
            # Kuyruktan işlenmemiş fotoğrafları batch halinde al
            res = supabase.table("photos") \
                .select("*") \
                .eq("processed", False) \
                .limit(BATCH_SIZE) \
                .execute()
            
            if res.data:
                total_valid_faces = 0
                
                for photo in res.data:
                    valid_count = process_single_photo(analyzer, photo)
                    total_valid_faces += valid_count
                
                processed_since_cluster += len(res.data)
                
                # Yeni geçerli yüzler eklendiğinde ve eşik aşıldığında yeniden kümele
                if total_valid_faces > 0 and processed_since_cluster >= RECLUSTER_EVERY_N:
                    update_clusters(clusterer)
                    processed_since_cluster = 0
                
                logger.info(
                    f"Tur tamamlandı: {len(res.data)} fotoğraf işlendi. "
                    f"Sonraki kümelemeye {RECLUSTER_EVERY_N - processed_since_cluster} fotoğraf kaldı."
                )
                
                # Başarılı işlem — hata sayacını sıfırla
                consecutive_errors = 0
                error_backoff = ERROR_BACKOFF_INITIAL
                
            else:
                # Kuyruk boşsa bekle
                time.sleep(POLL_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Worker kullanıcı tarafından durduruldu (Ctrl+C).")
            
            # Son kez kümeleme yap (işlenmiş ama henüz kümelenmemiş yüzler varsa)
            if processed_since_cluster > 0:
                logger.info("Kapanmadan önce son kümeleme yapılıyor...")
                try:
                    update_clusters(clusterer)
                except Exception:
                    pass
            break
            
        except Exception as e:
            consecutive_errors += 1
            logger.error(
                f"Beklenmeyen Hata (ardışık #{consecutive_errors}): {e}",
                exc_info=True
            )
            
            # Üstel geri çekilme (exponential backoff)
            time.sleep(error_backoff)
            error_backoff = min(error_backoff * 2, ERROR_BACKOFF_MAX)
            
            if consecutive_errors >= 10:
                logger.critical(
                    f"10 ardışık hata oluştu. Worker durduruluyor. "
                    f"Son hata: {e}"
                )
                sys.exit(1)


if __name__ == "__main__":
    start_worker()
