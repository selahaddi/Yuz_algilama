import os
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv
import json
import requests
import io
import threading
from functools import lru_cache
from collections import OrderedDict

# Ortam değişkenlerini yükle
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
# Cloud Run arka plan servisi olduğu için yetkili (service role) anahtarını kullanmalı
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_ANON_KEY", "")))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL ve SUPABASE_KEY .env dosyasında bulunamadı.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Yüz Tanıma SaaS - Guest API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme/Vercel için herkese açık
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Lazy Model Loading ───────────────────────────────────────────────────────
# InsightFace modeli (~600MB RAM) yalnızca selfie araması yapıldığında yüklenir.
# Bu sayede Cloud Run container'ı daha hızlı başlar ve az RAM kullanır.
_analyzer = None
_analyzer_lock = threading.Lock()

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        with _analyzer_lock:
            if _analyzer is None:
                from core.face_analyzer import FaceAnalyzer
                _analyzer = FaceAnalyzer(gpu_id=0)
    return _analyzer

# ─── Avatar Cache (LRU, Max 200 entry) ────────────────────────────────────────
# Bellek taşmasını önlemek için maksimum 200 avatar cache'lenir.
class LRUAvatarCache:
    def __init__(self, maxsize=200):
        self.cache = OrderedDict()
        self.maxsize = maxsize

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

avatar_cache = LRUAvatarCache(maxsize=200)


@app.get("/api/event/{event_id}")
def get_event(event_id: str):
    res = supabase.table("events").select("*, studios(name, primary_color, logo_url, watermark_text)").eq("id", event_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Etkinlik bulunamadı")
    event_data = res.data[0]
    
    # Düz (flat) formata çevirerek frontende dön (opsiyonel ama daha temiz olur)
    studio = event_data.pop("studios", {})
    if studio:
        event_data["studio_name"] = studio.get("name")
        event_data["primary_color"] = studio.get("primary_color") or "#685d4a"
        event_data["logo_url"] = studio.get("logo_url")
        event_data["watermark_text"] = studio.get("watermark_text")
        
    return event_data


@app.post("/api/search_selfie")
async def search_selfie(event_id: str = Form(...), search_mode: str = Form("single"), file: UploadFile = File(...)):
    # search_mode: "single" (en büyük yüz), "any" (herhangi biri), "all" (herkesin olduğu)
    analyzer = get_analyzer()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Fotoğraf okunamadı")
        
    faces = analyzer.analyze_image(img)
    if not faces:
        raise HTTPException(status_code=400, detail="Yüz tespit edilemedi. Daha net bir fotoğraf yükleyin.")
        
    try:
        if search_mode == "single" or len(faces) == 1:
            # En büyük yüzü al (Selfie çeken kişi)
            best_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
            embedding_list = best_face.embedding.astype(float).tolist()
            embedding_str = f"[{','.join(map(str, embedding_list))}]"
            
            res = supabase.rpc(
                "match_faces", 
                {
                    "query_embedding": embedding_str,
                    "match_threshold": 0.45,
                    "match_count": 50,
                    "target_event_id": event_id
                }
            ).execute()
            return {"matches": res.data}
        else:
            # Çoklu yüz araması
            all_matches = []
            for face in faces:
                embedding_list = face.embedding.astype(float).tolist()
                embedding_str = f"[{','.join(map(str, embedding_list))}]"
                res = supabase.rpc(
                    "match_faces", 
                    {
                        "query_embedding": embedding_str,
                        "match_threshold": 0.45,
                        "match_count": 100,
                        "target_event_id": event_id
                    }
                ).execute()
                all_matches.append(res.data)
            
            if search_mode == "any":
                # Birleşim: Herhangi birinin olduğu fotoğrafları al, duplicate olanları id'ye göre çıkar
                merged = {}
                for matches in all_matches:
                    for m in matches:
                        merged[m["photo_id"]] = m
                return {"matches": list(merged.values())}
            
            elif search_mode == "all":
                # Kesişim: Herkesin olduğu fotoğrafları bul
                if not all_matches:
                    return {"matches": []}
                
                # İlk yüzün bulduğu photo_id'leri set olarak al
                common_photo_ids = set([m["photo_id"] for m in all_matches[0]])
                
                # Diğer yüzlerin bulduğu photo_id'ler ile kesiştir
                for matches in all_matches[1:]:
                    current_ids = set([m["photo_id"] for m in matches])
                    common_photo_ids = common_photo_ids.intersection(current_ids)
                
                # Sadece common olanları listele (tüm detayları ilk eşleşmeden alabiliriz)
                merged = {}
                for m in all_matches[0]:
                    if m["photo_id"] in common_photo_ids:
                        merged[m["photo_id"]] = m
                
                return {"matches": list(merged.values())}
            
            return {"matches": []}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clusters/{event_id}")
def get_clusters(event_id: str):
    """Bu etkinlikteki benzersiz cluster_id'leri bul ve her biri için fotoğraf sayısını döndür."""
    res = supabase.table("faces") \
        .select("cluster_id, bbox, photos!inner(event_id, thumbnail_url, image_url)") \
        .eq("photos.event_id", event_id) \
        .neq("cluster_id", -1) \
        .execute()
        
    if not res.data:
        return {"clusters": []}
        
    # Cluster'ları grupla ve her biri için fotoğraf sayısını hesapla
    clusters_dict = {}
    for row in res.data:
        cid = row.get("cluster_id")
        if cid is None:
            continue
        if cid not in clusters_dict:
            clusters_dict[cid] = {
                "id": cid,
                "name": f"Kişi #{cid}",
                "photo_count": 0,
                "photo_ids": set()
            }
        # Benzersiz fotoğraf sayısını hesapla (aynı fotoğraftaki birden fazla yüz sayılmasın)
        photo_info = row.get("photos", {})
        if photo_info and photo_info.get("image_url"):
            clusters_dict[cid]["photo_ids"].add(photo_info["image_url"])
    
    # photo_ids set'ini temizle (JSON serializable değil) ve sayıya çevir
    sorted_clusters = []
    for cid in sorted(clusters_dict.keys()):
        cluster = clusters_dict[cid]
        sorted_clusters.append({
            "id": cluster["id"],
            "name": cluster["name"],
            "photo_count": len(cluster["photo_ids"])
        })
    
    return {"clusters": sorted_clusters}


@app.get("/api/avatar/{cluster_id}")
def get_avatar(cluster_id: int, event_id: str = Query(None)):
    """Cluster avatar'ını döndür. event_id verilmişse sadece o etkinlikteki yüzlerden avatar oluşturur."""
    cache_key = f"{event_id or 'global'}_{cluster_id}"

    cached = avatar_cache.get(cache_key)
    if cached:
        return StreamingResponse(
            io.BytesIO(cached), 
            media_type="image/jpeg", 
            headers={"Cache-Control": "public, max-age=86400"}
        )

    # Sorguyu oluştur
    query = supabase.table("faces") \
        .select("bbox, photos!inner(image_url, event_id)") \
        .eq("cluster_id", cluster_id)

    # event_id filtresi varsa ekle
    if event_id:
        query = query.eq("photos.event_id", event_id)

    res = query.limit(1).execute()
        
    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")
        
    photo = res.data[0].get("photos", {})
    bbox = res.data[0].get("bbox")
    image_url = photo.get("image_url")
    
    if not image_url or not bbox:
        raise HTTPException(status_code=404, detail="Not found")
        
    try:
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        nparr = np.frombuffer(response.content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=500, detail="Image decode failed")
            
        x1, y1, x2, y2 = map(int, bbox)
        fw = x2 - x1
        fh = y2 - y1
        pad_w = int(fw * 0.5)
        pad_h = int(fh * 0.5)
        
        y1_pad = max(0, y1 - pad_h)
        y2_pad = min(img.shape[0], y2 + pad_h)
        x1_pad = max(0, x1 - pad_w)
        x2_pad = min(img.shape[1], x2 + pad_w)
        
        face_crop = img[y1_pad:y2_pad, x1_pad:x2_pad]
        face_crop = cv2.resize(face_crop, (256, 256))
        
        _, buffer = cv2.imencode('.jpg', face_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        jpeg_bytes = buffer.tobytes()
        
        avatar_cache.set(cache_key, jpeg_bytes)
        return StreamingResponse(
            io.BytesIO(jpeg_bytes), 
            media_type="image/jpeg", 
            headers={"Cache-Control": "public, max-age=86400"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cluster_photos/{cluster_id}")
def get_cluster_photos(cluster_id: int, event_id: str = Query(None)):
    """
    Belirli bir cluster'a ait fotoğrafları döndür.
    event_id verilmişse, yalnızca o etkinlikteki fotoğrafları filtreler.
    """
    query = supabase.table("faces") \
        .select("photos!inner(id, image_url, thumbnail_url, event_id)") \
        .eq("cluster_id", cluster_id)

    # event_id filtresi varsa ekle (güvenlik: başka etkinliklerin fotoğrafları karışmasın)
    if event_id:
        query = query.eq("photos.event_id", event_id)

    res = query.execute()
        
    if not res.data:
        return {"photos": []}
        
    unique_photos = {}
    for row in res.data:
        p = row.get("photos")
        if p:
            unique_photos[p["image_url"]] = {
                "id": p["id"],
                "image_url": p["image_url"],
                "thumbnail_url": p.get("thumbnail_url")
            }
            
    return {"photos": list(unique_photos.values())}


@app.post("/api/trigger_worker")
def trigger_worker():
    """
    Cloud Run Worker Job'ı tetikler.
    Studio App fotoğraf yüklemesi tamamlandığında bu endpoint çağrılır.
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "yuz-tanima-app-9947")
    region = os.environ.get("GCP_REGION", "europe-west1")
    job_name = "face-worker-job"

    # Google Cloud Run Jobs Admin API v2 — doğru URL formatı
    url = f"https://run.googleapis.com/v2/projects/{project_id}/locations/{region}/jobs/{job_name}:run"

    try:
        # Cloud Run içinden metadata server üzerinden access token al
        # NOT: Doğru path /token'dır, /access_token değil!
        token_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
        token_res = requests.get(token_url, headers={"Metadata-Flavor": "Google"}, timeout=5)
        token_res.raise_for_status()
        access_token = token_res.json()["access_token"]

        # Worker Job'ı tetikle
        run_res = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={},
            timeout=30
        )
        run_res.raise_for_status()
        return {"status": "ok", "message": "Worker Job tetiklendi."}

    except requests.exceptions.ConnectionError:
        # Yerel geliştirme ortamında metadata server erişilemez — sessizce geç
        return {"status": "skipped", "message": "Yerel ortamda çalışıyor, Cloud Run Job tetiklenemedi."}
    except Exception as e:
        # Tetikleme başarısız olsa bile fotoğraflar yüklendi, kritik bir hata değil
        return {"status": "error", "message": f"Worker tetiklenemedi: {str(e)}"}



class OrderRequest(BaseModel):
    event_id: str
    guest_name: str
    guest_contact: str
    photo_ids: list[str]
    total_price: float

@app.post("/api/order")
def create_order(order: OrderRequest):
    try:
        data = {
            "event_id": order.event_id,
            "guest_name": order.guest_name,
            "guest_contact": order.guest_contact,
            "photo_ids": order.photo_ids,
            "total_price": order.total_price,
            "status": "pending"
        }
        res = supabase.table("orders").insert(data).execute()
        return {"status": "success", "order": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class FeedbackRequest(BaseModel):
    cluster_id: int
    photo_id: str
    status: str = "wrong_match"

@app.post("/api/feedback")
def submit_feedback(feedback: FeedbackRequest):
    try:
        # Önce bu cluster ve photo için doğru face_id'yi bul
        res_face = supabase.table("faces").select("id").eq("photo_id", feedback.photo_id).eq("cluster_id", feedback.cluster_id).execute()
        if not res_face.data:
            raise Exception("Yüz bulunamadı")
        
        face_id = res_face.data[0]["id"]
        
        data = {
            "face_id": face_id,
            "photo_id": feedback.photo_id,
            "status": feedback.status
        }
        supabase.table("feedbacks").insert(data).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Statik frontend dosyalarını servis et (HTML/CSS/JS)
app.mount("/", StaticFiles(directory="public", html=True), name="public")
