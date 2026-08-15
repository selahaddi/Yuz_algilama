import os
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv
from core.face_analyzer import FaceAnalyzer
import json
import requests
import io

# Ortam değişkenlerini yükle
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("SUPABASE_URL ve SUPABASE_ANON_KEY .env dosyasında bulunamadı.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

app = FastAPI(title="Yüz Tanıma SaaS - Guest API")

# Hızlı Yüz Analiz Modeli (CPU/GPU)
analyzer = FaceAnalyzer(gpu_id=0)

@app.get("/api/event/{event_id}")
def get_event(event_id: str):
    res = supabase.table("events").select("*").eq("id", event_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Etkinlik bulunamadı")
    return res.data[0]

@app.post("/api/search_selfie")
async def search_selfie(event_id: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Fotoğraf okunamadı")
        
    faces = analyzer.analyze_image(img)
    if not faces:
        raise HTTPException(status_code=400, detail="Yüz tespit edilemedi. Daha net bir fotoğraf yükleyin.")
        
    # En büyük yüzü al (Selfie çeken kişi)
    best_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
    embedding_list = best_face.embedding.astype(float).tolist()
    embedding_str = f"[{','.join(map(str, embedding_list))}]"
    
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clusters/{event_id}")
def get_clusters(event_id: str):
    # Bu etkinlikteki benzersiz cluster_id'leri bul ve her biri için örnek bir fotoğraf getir
    res = supabase.table("faces") \
        .select("cluster_id, bbox, photos!inner(event_id, thumbnail_url, image_url)") \
        .eq("photos.event_id", event_id) \
        .neq("cluster_id", -1) \
        .execute()
        
    if not res.data:
        return {"clusters": []}
        
    # Cluster'ları grupla ve her biri için ilk fotoğrafı avatar yap
    clusters_dict = {}
    for row in res.data:
        cid = row.get("cluster_id")
        if cid is None:
            continue
        if cid not in clusters_dict:
            clusters_dict[cid] = {
                "id": cid,
                "name": f"Kişi #{cid}"
            }
            
    # id'ye göre sırala
    sorted_clusters = sorted(list(clusters_dict.values()), key=lambda x: x["id"])
    return {"clusters": sorted_clusters}

avatar_cache = {}

@app.get("/api/avatar/{cluster_id}")
def get_avatar(cluster_id: int):
    if cluster_id in avatar_cache:
        return StreamingResponse(
            io.BytesIO(avatar_cache[cluster_id]), 
            media_type="image/jpeg", 
            headers={"Cache-Control": "public, max-age=86400"}
        )
        
    res = supabase.table("faces") \
        .select("bbox, photos!inner(image_url)") \
        .eq("cluster_id", cluster_id) \
        .limit(1) \
        .execute()
        
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
        
        avatar_cache[cluster_id] = jpeg_bytes
        return StreamingResponse(
            io.BytesIO(jpeg_bytes), 
            media_type="image/jpeg", 
            headers={"Cache-Control": "public, max-age=86400"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cluster_photos/{cluster_id}")
def get_cluster_photos(cluster_id: int):
    res = supabase.table("faces") \
        .select("photos(image_url, thumbnail_url)") \
        .eq("cluster_id", cluster_id) \
        .execute()
        
    if not res.data:
        return {"photos": []}
        
    unique_photos = {}
    for row in res.data:
        p = row.get("photos")
        if p:
            unique_photos[p["image_url"]] = p
            
    return {"photos": list(unique_photos.values())}

# Statik frontend dosyalarını servis et (HTML/CSS/JS)
app.mount("/", StaticFiles(directory="public", html=True), name="public")
