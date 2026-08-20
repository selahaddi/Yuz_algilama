import os
import datetime
from urllib.parse import urlparse
from supabase import create_client, Client
from dotenv import load_dotenv

def main():
    print("🧹 Temizlik Botu Başlıyor...")
    load_dotenv()
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY"))
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("HATA: SUPABASE_URL veya SUPABASE_SERVICE_KEY bulunamadı.")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # 30 gün öncesinin tarihi
    days_to_keep = 30
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_to_keep)
    cutoff_str = cutoff_date.isoformat()
    
    print(f"[{cutoff_str}] tarihinden eski etkinlikler aranıyor...")
    
    # 30 günden eski etkinlikleri bul
    events_res = supabase.table("events").select("id, title").lt("created_at", cutoff_str).execute()
    old_events = events_res.data
    
    if not old_events:
        print("🎉 Silinecek eski etkinlik bulunamadı. Her şey temiz!")
        return
        
    print(f"🚨 {len(old_events)} adet eski etkinlik bulundu. Temizlik başlıyor...")
    
    for event in old_events:
        event_id = event["id"]
        event_title = event["title"]
        print(f"\n🗑️ Etkinlik Siliniyor: {event_title} (ID: {event_id})")
        
        # 1. Bu etkinliğe ait fotoğrafları bul
        photos_res = supabase.table("photos").select("image_url, thumbnail_url").eq("event_id", event_id).execute()
        photos = photos_res.data
        
        files_to_delete = []
        for p in photos:
            if p.get("image_url"):
                parsed = urlparse(p["image_url"])
                file_name = parsed.path.split("/")[-1]
                files_to_delete.append(file_name)
            if p.get("thumbnail_url"):
                parsed = urlparse(p["thumbnail_url"])
                thumb_name = parsed.path.split("/")[-1]
                files_to_delete.append(f"thumbnails/{thumb_name}")
                
        # 2. Storage'dan dosyaları sil (batch)
        if files_to_delete:
            print(f"   -> Storage'dan {len(files_to_delete)} adet dosya siliniyor...")
            # Supabase remove max 100 limitine takılabilir, parçalara ayırmak iyi olur
            batch_size = 100
            for i in range(0, len(files_to_delete), batch_size):
                batch = files_to_delete[i:i + batch_size]
                try:
                    supabase.storage.from_("wedding_photos").remove(batch)
                except Exception as e:
                    print(f"      Hata: Dosyalar silinirken bir sorun oluştu: {e}")
        
        # 3. Veritabanından etkinliği sil (Cascade ile bağlantılı kayıtlar da gider)
        print("   -> Veritabanından etkinlik kaydı siliniyor...")
        try:
            supabase.table("events").delete().eq("id", event_id).execute()
            print("   ✅ Başarıyla temizlendi.")
        except Exception as e:
            print(f"   ❌ Hata: Etkinlik silinemedi: {e}")

    print("\n🏁 Temizlik botu işlemini tamamladı.")

if __name__ == "__main__":
    main()
