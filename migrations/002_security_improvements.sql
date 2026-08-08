-- ═══════════════════════════════════════════════════════════════════════════════
-- Güvenlik ve Performans İyileştirme Migration'ı
-- Bu dosyayı Supabase SQL Editor'de çalıştırın
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. photos tablosuna aynı URL'nin iki kez eklenmesini engelleyen UNIQUE constraint
-- (Eğer tabloda zaten tekrarlı URL'ler varsa önce onları temizleyin)
ALTER TABLE photos ADD CONSTRAINT photos_image_url_unique UNIQUE (image_url);

-- 2. RLS Politikalarını Kısıtla
-- Önce mevcut açık politikaları kaldır
DROP POLICY IF EXISTS "Allow public read for photos" ON photos;
DROP POLICY IF EXISTS "Allow public insert for photos" ON photos;
DROP POLICY IF EXISTS "Allow public update for photos" ON photos;

DROP POLICY IF EXISTS "Allow public read for faces" ON faces;
DROP POLICY IF EXISTS "Allow public insert for faces" ON faces;
DROP POLICY IF EXISTS "Allow public update for faces" ON faces;
DROP POLICY IF EXISTS "Allow public delete for faces" ON faces;

-- 3. Yeni kısıtlı politikalar: anon kullanıcılar sadece okuyabilir ve fotoğraf ekleyebilir
-- photos: anon SELECT + INSERT (yeni URL kuyruğa ekleyebilir), UPDATE yok
CREATE POLICY "anon_select_photos" ON photos FOR SELECT TO anon USING (true);
CREATE POLICY "anon_insert_photos" ON photos FOR INSERT TO anon WITH CHECK (true);

-- faces: anon sadece SELECT (galeriyi görebilir)
CREATE POLICY "anon_select_faces" ON faces FOR SELECT TO anon USING (true);

-- authenticated (giriş yapmış) kullanıcılar da aynı yetkiler
CREATE POLICY "auth_select_photos" ON photos FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_photos" ON photos FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_select_faces" ON faces FOR SELECT TO authenticated USING (true);

-- service_role zaten RLS'yi bypass eder, ayrıca policy'ye gerek yok
-- Ancak GRANT ALL veriyoruz ki direkt SQL erişimi de çalışsın
GRANT ALL ON public.photos TO anon, authenticated, service_role;
GRANT ALL ON public.faces TO anon, authenticated, service_role;
