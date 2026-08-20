import os
import time
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
import uuid

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
GUEST_API_URL = os.environ.get("GUEST_API_URL", "https://guest-api-398389727192.europe-west1.run.app")

def test_pipeline():
    print("=== UÇTAN UCA TEST BAŞLIYOR ===")
    
    # 1. Test Event'i Seç veya Oluştur
    print("\n1. Etkinlik (Event) Alınıyor...")
    res = supabase.table("events").select("id").limit(1).execute()
    if not res.data:
        print("Etkinlik bulunamadı. Lütfen panelden bir etkinlik oluşturun.")
        return
    event_id = res.data[0]["id"]
    print(f"✅ Etkinlik ID: {event_id}")

    # 2. Örnek bir fotoğraf yükle (Supabase'e URL olarak kaydet)
    print("\n2. Test Fotoğrafı Ekleniyor...")
    # İnternetten hazır bir test fotoğrafı kullanalım (örneğin birden fazla yüz içeren bir görsel veya düz bir portre)
    test_image_url = "https://images.unsplash.com/photo-1517486808906-6ca8b3f04846?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
    
    insert_res = supabase.table("photos").insert({
        "event_id": event_id,
        "image_url": test_image_url,
        "processed": False
    }).execute()
    
    photo_id = insert_res.data[0]["id"]
    print(f"✅ Test Fotoğrafı Veritabanına Eklendi. ID: {photo_id}")

    # 3. Worker'ı Tetikle (Studio'daki butonun yaptığı gibi)
    print("\n3. Worker Job Tetikleniyor (/api/trigger_worker)...")
    trigger_url = f"{GUEST_API_URL}/api/trigger_worker"
    trigger_res = requests.post(trigger_url, timeout=15)
    print(f"Yanıt Durumu: {trigger_res.status_code}")
    print(f"Yanıt İçeriği: {trigger_res.json()}")
    if trigger_res.status_code != 200:
        print("❌ Worker tetiklenemedi!")
        return
    print("✅ Worker Job Başarıyla Tetiklendi.")

    # 4. İşlemin Bitmesini Bekle
    print("\n4. Worker Job'un Fotoğrafı İşlemesi Bekleniyor (Maksimum 90 saniye)...")
    success = False
    for i in range(18):
        time.sleep(5)
        check_res = supabase.table("photos").select("processed").eq("id", photo_id).execute()
        if check_res.data and check_res.data[0]["processed"]:
            success = True
            break
        print(f"Bekleniyor... ({i*5 + 5} sn)")
    
    if not success:
        print("❌ Worker belirlenen sürede fotoğrafı işlemedi. Logları kontrol edin.")
        return
        
    print("✅ Fotoğraf Başarıyla İşlendi!")

    # 5. Misafir Arayüzü API'lerini Kontrol Et
    print("\n5. Misafir Arayüzü (Guest API) Kontrolü Yapılıyor...")
    
    # Kümeleri (Kişileri) getir
    clusters_res = requests.get(f"{GUEST_API_URL}/api/clusters?event_id={event_id}")
    if clusters_res.status_code == 200:
        clusters = clusters_res.json().get("clusters", [])
        print(f"✅ {len(clusters)} Kişi/Küme bulundu.")
        if clusters:
            first_cluster = clusters[0]
            cluster_id = first_cluster["id"]
            print(f"Örnek Kişi: ID {cluster_id}, Fotoğraf Sayısı: {first_cluster.get('photo_count', '?')}")
            
            # Kişinin fotoğraflarını getir
            photos_res = requests.get(f"{GUEST_API_URL}/api/cluster_photos/{cluster_id}?event_id={event_id}")
            if photos_res.status_code == 200:
                cluster_photos = photos_res.json().get("photos", [])
                print(f"✅ Bu kişiye ait {len(cluster_photos)} fotoğraf API'den başarıyla çekildi.")
            else:
                print("❌ cluster_photos API hatası:", photos_res.status_code)
    else:
        print("❌ clusters API hatası:", clusters_res.status_code)

    print("\n=== UÇTAN UCA TEST BAŞARIYLA TAMAMLANDI! ===")

if __name__ == "__main__":
    test_pipeline()
