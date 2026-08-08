-- ═══════════════════════════════════════════════════════════════════════════════
-- Storage (Depolama) RLS Politikaları
-- Bu dosyayı Supabase SQL Editor'de çalıştırın
-- Bu işlem, frontend üzerinden 'anon' anahtarı ile fotoğraf yükleyebilmeniz içindir.
-- ═══════════════════════════════════════════════════════════════════════════════

-- Storage bucket'ı public olarak oluşturmadıysanız, öncelikle oluşturulduğundan emin olun:
INSERT INTO storage.buckets (id, name, public) 
VALUES ('wedding_photos', 'wedding_photos', true)
ON CONFLICT (id) DO NOTHING;

-- 'wedding_photos' bucket'ı için Storage Objects tablosunda anon kullanıcılarına yetki veriyoruz.

-- 1. Okuma İzni (Herkes dosyaları indirebilir/görebilir)
CREATE POLICY "Public Access" 
ON storage.objects FOR SELECT 
TO public 
USING (bucket_id = 'wedding_photos');

-- 2. Yükleme (Insert) İzni (Anon kullanıcılar fotoğraf yükleyebilir)
CREATE POLICY "Anon Upload Access" 
ON storage.objects FOR INSERT 
TO anon 
WITH CHECK (bucket_id = 'wedding_photos');

-- 3. (Opsiyonel) Silme İzni (İsterseniz bu satırı yorum satırından çıkarıp, silme yetkisi verebilirsiniz)
-- CREATE POLICY "Anon Delete Access" 
-- ON storage.objects FOR DELETE 
-- TO anon 
-- USING (bucket_id = 'wedding_photos');
