import os
import sys
import time
import json
import logging
import requests
import numpy as np
import cv2
from io import BytesIO
from PIL import Image
from supabase import create_client, Client
from dotenv import load_dotenv
import concurrent.futures
import threading

# Yapay Zeka Modüllerini İçe Aktar
from core.face_analyzer import FaceAnalyzer
from core.clusterer import FaceClusterer

# ─── Loglama Yapılandırması ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # Sadece terminale yaz (Cloud Logging otomatik yakalar)
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
MIN_FACE_SIZE = 120          # Piksel cinsinden minimum yüz boyutu
MIN_DET_SCORE = 0.7          # Minimum yüz tespit doğruluk skoru
MIN_BLUR_SCORE = 15.0        # Minimum bulanıklık eşiği
THUMBNAIL_MAX_SIZE = 800     # Maksimum thumbnail boyutu (piksel)

def update_clusters_for_event(clusterer: FaceClusterer, event_id: str):
    """
    Belirli bir etkinliğe ait tüm yüz vektörlerini çeker, yeniden kümeleme (DBSCAN) yapar.
    Önceki küme atamaları ile karşılaştırarak kararlı (stabil) ID'ler atar
    ve sadece değişenleri veritabanında günceller.
    """
    logger.info(f"[{event_id}] Etkinliği için yüzler kümeleniyor...")
    
    # Sadece o etkinliğe ait yüzleri çek (photo_id üzerinden)
    response = supabase.table("faces") \
        .select("id, embedding, cluster_id, photos!inner(event_id)") \
        .eq("photos.event_id", event_id) \
        .execute()
        
    faces_data = response.data
    
    if not faces_data:
        logger.info(f"[{event_id}] Veritabanında yüz bulunamadı.")
        return
        
    embeddings = []
    face_ids = []
    old_cluster_ids = []
    
    for row in faces_data:
        face_ids.append(row["id"])
        old_cluster_ids.append(row.get("cluster_id"))
        emb = row["embedding"]
        
        if isinstance(emb, str):
            emb = json.loads(emb)
            
        embeddings.append(np.array(emb, dtype=np.float32))
        
    # Kümeleme (DBSCAN) yap
    new_labels = clusterer.cluster(embeddings)
    
    # ─── Küme Kararlılığı (Cluster Stability) ──────────────────────────────
    stabilized_labels = _stabilize_cluster_ids(old_cluster_ids, new_labels)
    
    # ─── Toplu Güncelleme (Batch Update) ───────────────────────────────────
    updates_count = 0
    for face_id, old_label, new_label in zip(face_ids, old_cluster_ids, stabilized_labels):
        if old_label != new_label:
            supabase.table("faces").update({"cluster_id": int(new_label)}).eq("id", face_id).execute()
            updates_count += 1
        
    unique_people = len(set(label for label in stabilized_labels if label != -1))
    logger.info(
        f"[{event_id}] Kümeleme tamamlandı! {len(faces_data)} yüz -> {unique_people} kişi. "
        f"{updates_count} kayıt güncellendi."
    )

def _stabilize_cluster_ids(old_ids: list, new_ids: list) -> list:
    if not old_ids or all(o is None for o in old_ids):
        return new_ids
    
    from collections import Counter
    
    new_to_old_votes = {}
    for old_id, new_id in zip(old_ids, new_ids):
        if new_id == -1:
            continue
        if new_id not in new_to_old_votes:
            new_to_old_votes[new_id] = Counter()
        if old_id is not None and old_id != -1:
            new_to_old_votes[new_id][old_id] += 1
    
    new_to_stable = {}
    used_old_ids = set()
    
    mapping_candidates = []
    for new_id, votes in new_to_old_votes.items():
        if votes:
            best_old_id, best_count = votes.most_common(1)[0]
            mapping_candidates.append((best_count, new_id, best_old_id))
    
    mapping_candidates.sort(reverse=True)
    
    for _, new_id, old_id in mapping_candidates:
        if old_id not in used_old_ids:
            new_to_stable[new_id] = old_id
            used_old_ids.add(old_id)
    
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
            
    return [
        -1 if label == -1 else new_to_stable.get(label, label)
        for label in new_ids
    ]

def generate_and_upload_thumbnail(img_cv2, photo_id: str) -> str:
    """Orijinal resmi boyutlandırır, sıkıştırır ve Storage'a thumbnail olarak yükler."""
    try:
        # BGR'den RGB'ye çevir ve PIL Image oluştur
        img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        
        # Boyutlandırma (Oranı koruyarak max boyuta uyarla)
        pil_img.thumbnail((THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE), Image.Resampling.LANCZOS)
        
        # Bytes'a çevir (JPEG kalitesi 75 ile)
        buf = BytesIO()
        pil_img.save(buf, format="JPEG", quality=75)
        file_bytes = buf.getvalue()
        
        # Dosya adı ve upload
        file_name = f"thumbnails/{photo_id}.jpg"
        
        # Mevcut bucket: wedding_photos. Eğer hata verirse storage RLS'sini kontrol etmek gerekebilir.
        supabase.storage.from_("wedding_photos").upload(
            file_name, 
            file_bytes, 
            {"content-type": "image/jpeg"}
        )
        
        public_url = supabase.storage.from_("wedding_photos").get_public_url(file_name)
        return public_url
    except Exception as e:
        logger.error(f"Thumbnail oluşturulamadı ({photo_id}): {e}")
        return None

def process_single_photo(analyzer: FaceAnalyzer, photo: dict) -> int:
    photo_id = photo["id"]
    event_id = photo.get("event_id")
    url = photo["image_url"]
    
    logger.info(f"  Fotoğraf işleniyor: {url[:80]}...")
    
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
        
    # Yüzleri tespit et (Thread-safe yapmak için lock kullanabiliriz ancak ONNXRuntime genellikle sorun çıkarmaz. Yine de ağ I/O çok zaman alıyor)
    faces = analyzer.analyze_image(img)
    logger.info(f"   => Fotoğrafta {len(faces)} yüz bulundu.")
    
    valid_faces_count = 0
    for face in faces:
        bbox = face.bbox.astype(float).tolist()
        x1, y1, x2, y2 = bbox
        
        width = x2 - x1
        height = y2 - y1
        if width < MIN_FACE_SIZE or height < MIN_FACE_SIZE:
            continue
            
        if face.det_score < MIN_DET_SCORE:
            continue
            
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
        
        supabase.table("faces").insert({
            "photo_id": photo_id,
            "embedding": embedding,
            "bbox": bbox,
            "det_score": float(face.det_score)
        }).execute()
        valid_faces_count += 1
        
    logger.info(f"   => {valid_faces_count} adet net/geçerli yüz kaydedildi.")
    
    # Thumbnail üret
    thumbnail_url = generate_and_upload_thumbnail(img, photo_id)
    
    # Kaydı güncelle
    update_data = {"processed": True}
    if thumbnail_url:
        update_data["thumbnail_url"] = thumbnail_url
        
    supabase.table("photos").update(update_data).eq("id", photo_id).execute()
    
    return valid_faces_count

def start_worker():
    logger.info("Yapay Zeka Modelleri Yükleniyor (GPU aktif)...")
    analyzer = FaceAnalyzer(gpu_id=0)
    clusterer = FaceClusterer(eps=0.45)
    logger.info("Worker Başlatıldı ve Supabase Kuyruğunu (Queue) Dinliyor...")
    logger.info(f"   Yapılandırma: batch_size={BATCH_SIZE}, recluster_every={RECLUSTER_EVERY_N}")

    event_processed_counts = {}
    error_backoff = ERROR_BACKOFF_INITIAL
    consecutive_errors = 0

    while True:
        try:
            res = supabase.table("photos") \
                .select("*") \
                .eq("processed", False) \
                .limit(BATCH_SIZE) \
                .execute()
            
            if res.data:
                # Fotoğrafları paralel (aynı anda) işlemek için ThreadPoolExecutor kullan
                def process_task(photo):
                    event_id = photo.get("event_id")
                    if not event_id:
                        supabase.table("photos").update({"processed": True}).eq("id", photo["id"]).execute()
                        return None, 0
                        
                    try:
                        valid_count = process_single_photo(analyzer, photo)
                        return event_id, valid_count
                    except Exception as photo_err:
                        logger.error(f"Fotoğraf işlenirken kritik hata oluştu ({photo.get('id')}): {photo_err}")
                        supabase.table("photos").update({"processed": True}).eq("id", photo["id"]).execute()
                        return event_id, 0

                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    results = list(executor.map(process_task, res.data))
                
                for event_id, _ in results:
                    if event_id:
                        if event_id not in event_processed_counts:
                            event_processed_counts[event_id] = 0
                        event_processed_counts[event_id] += 1
                
                # Belirli bir event'in işlenen fotoğraf sayısı limiti aştıysa, o eventi kümele
                events_to_cluster = []
                for eid, count in event_processed_counts.items():
                    if count >= RECLUSTER_EVERY_N:
                        events_to_cluster.append(eid)
                        
                for eid in events_to_cluster:
                    update_clusters_for_event(clusterer, eid)
                    event_processed_counts[eid] = 0
                
                logger.info(f"Tur tamamlandı: {len(res.data)} fotoğraf işlendi.")
                consecutive_errors = 0
                error_backoff = ERROR_BACKOFF_INITIAL
                
            else:
                logger.info("İşlenecek fotoğraf kalmadı. Worker sonlanıyor (Cloud Run Job mode).")
                # İşlenmiş ama kümelenmemiş eventleri son kez kümele
                for eid, count in event_processed_counts.items():
                    if count > 0:
                        try:
                            update_clusters_for_event(clusterer, eid)
                        except Exception:
                            pass
                break
                
        except KeyboardInterrupt:
            logger.info("Worker kullanıcı tarafından durduruldu (Ctrl+C).")
            # Kapanmadan önce işlenmiş ama kümelenmemiş eventleri son kez kümele
            for eid, count in event_processed_counts.items():
                if count > 0:
                    try:
                        update_clusters_for_event(clusterer, eid)
                    except Exception:
                        pass
            break
            
        except Exception as e:
            consecutive_errors += 1
            logger.error(
                f"Beklenmeyen Hata (ardışık #{consecutive_errors}): {e}",
                exc_info=True
            )
            time.sleep(error_backoff)
            error_backoff = min(error_backoff * 2, ERROR_BACKOFF_MAX)
            
            if consecutive_errors >= 10:
                logger.critical(f"10 ardışık hata oluştu. Worker durduruluyor. Son hata: {e}")
                sys.exit(1)

if __name__ == "__main__":
    start_worker()
