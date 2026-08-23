import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

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

# Global Lock for FaceAnalyzer Thread-Safety (Prevent ONNX Runtime segfaults)
analyzer_lock = threading.Lock()

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
BATCH_SIZE = 20             # Her turda en fazla kaç fotoğraf işlensin
RECLUSTER_EVERY_N = 10      # Kaç fotoğraftan sonra yeniden kümeleme yapılsın
POLL_INTERVAL = 3            # Kuyruk boşken bekleme süresi (saniye)
ERROR_BACKOFF_INITIAL = 5    # İlk hata bekleme süresi (saniye)
ERROR_BACKOFF_MAX = 60       # Maksimum hata bekleme süresi (saniye)
MIN_FACE_SIZE = 50           # Piksel cinsinden minimum yüz boyutu
MIN_DET_SCORE = 0.7          # Minimum yüz tespit doğruluk skoru
MIN_BLUR_SCORE = 15.0        # Minimum bulanıklık eşiği
THUMBNAIL_MAX_SIZE = 800     # Maksimum thumbnail boyutu (piksel)

def update_clusters_for_event(clusterer: FaceClusterer, event_id: str):
    """
    Kademeli (Incremental) Kümeleme:
    Tüm yüzleri baştan kümelemek yerine, sadece yeni gelen yüzleri mevcut kümelerin 
    merkezleri (Centroid) ile Kosinüs Benzerliği üzerinden eşleştirir.
    Eşleşmeyenleri kendi arasında DBSCAN ile yeni kümelere ayırır.
    """
    logger.info(f"[{event_id}] Etkinliği için kademeli (incremental) kümeleme yapılıyor...")
    
    # 1. Tüm yüzleri çek
    response = supabase.table("faces") \
        .select("id, embedding, cluster_id, photos!inner(event_id)") \
        .eq("photos.event_id", event_id) \
        .execute()
        
    faces_data = response.data
    if not faces_data:
        return
        
    clustered_faces = []
    new_faces = []
    
    for row in faces_data:
        emb = row["embedding"]
        if isinstance(emb, str):
            emb = json.loads(emb)
        emb = np.array(emb, dtype=np.float32)
        
        cid = row.get("cluster_id")
        if cid is not None and cid != -1:
            clustered_faces.append({"id": row["id"], "cluster_id": cid, "embedding": emb})
        else:
            new_faces.append({"id": row["id"], "embedding": emb})
            
    if not new_faces:
        logger.info(f"[{event_id}] İşlenecek yeni yüz bulunamadı.")
        return
        
    updates_count = 0
    max_existing_id = -1
    
    # 2. Mevcut Kümelerin Merkezlerini (Centroids) Hesapla
    centroids = {}
    if clustered_faces:
        from collections import defaultdict
        cluster_embs = defaultdict(list)
        for cf in clustered_faces:
            cluster_embs[cf["cluster_id"]].append(cf["embedding"])
            if cf["cluster_id"] > max_existing_id:
                max_existing_id = cf["cluster_id"]
                
        for cid, embs in cluster_embs.items():
            mean_emb = np.mean(embs, axis=0)
            norm = np.linalg.norm(mean_emb)
            if norm > 0:
                mean_emb = mean_emb / norm
            centroids[cid] = mean_emb
            
    # 3. Yeni Yüzleri Centroid'ler ile Eşleştir (Cosine Similarity)
    leftover_faces = []
    from numpy import dot
    
    # InsightFace buffalo_s için Kosinüs Benzerliği Eşiği
    # Bu değer ne kadar yüksekse eşleşme o kadar katı (strict) olur.
    SIMILARITY_THRESHOLD = 0.50 
    
    for nf in new_faces:
        best_cid = -1
        best_sim = -1.0
        
        if centroids:
            nf_norm = np.linalg.norm(nf["embedding"])
            nf_emb_norm = nf["embedding"] / nf_norm if nf_norm > 0 else nf["embedding"]
            
            for cid, c_emb in centroids.items():
                sim = dot(nf_emb_norm, c_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_cid = cid
                    
        if best_sim >= SIMILARITY_THRESHOLD:
            # Mevcut kümeye ata
            supabase.table("faces").update({"cluster_id": int(best_cid)}).eq("id", nf["id"]).execute()
            updates_count += 1
        else:
            leftover_faces.append(nf)
            
    # 4. Kalan (Leftover) Yüzleri Kendi İçinde DBSCAN ile Kümele
    if leftover_faces:
        leftover_embs = [f["embedding"] for f in leftover_faces]
        new_labels = clusterer.cluster(leftover_embs)
        
        # Noise (-1) noktalarını benzersiz kümelere çevir (Ayrı kişiler olarak değerlendir)
        local_max = max(new_labels) if len(new_labels) > 0 else -1
        for i in range(len(new_labels)):
            if new_labels[i] == -1:
                local_max += 1
                new_labels[i] = local_max
                
        # Mevcut en yüksek ID'nin üzerine ekleyerek veritabanına kaydet
        for i, nf in enumerate(leftover_faces):
            final_cluster_id = int(max_existing_id + 1 + new_labels[i])
            supabase.table("faces").update({"cluster_id": final_cluster_id}).eq("id", nf["id"]).execute()
            updates_count += 1
            
    logger.info(f"[{event_id}] Kademeli Kümeleme tamamlandı! {len(new_faces)} yeni yüz işlendi. {updates_count} kayıt güncellendi.")

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
        
    # Yüzleri tespit et (Thread-safe yapmak için lock)
    with analyzer_lock:
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
            # Sadece 'active' statüsündeki etkinliklerin fotoğraflarını çek (Race Condition Fix)
            res = supabase.table("photos") \
                .select("*, events!inner(status)") \
                .eq("processed", False) \
                .eq("events.status", "active") \
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
