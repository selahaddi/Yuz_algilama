-- 1. pgvector eklentisini aktif et (Vektör tabanlı benzerlik araması ve depolama için)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Stüdyolar Tablosu (Supabase Auth ile entegre edilebilir)
CREATE TABLE IF NOT EXISTS studios (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    auth_id UUID, -- Supabase auth.users tablosundaki ID ile eşleşmesi için (Opsiyonel)
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    primary_color TEXT DEFAULT '#685d4a', -- White-label ana renk
    logo_url TEXT, -- White-label logo URL
    watermark_text TEXT, -- Stüdyonun fotoğraf üzerindeki filigran metni
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Etkinlikler Tablosu (Düğün, Nişan vb.)
CREATE TABLE IF NOT EXISTS events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    studio_id UUID REFERENCES studios(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    event_date DATE,
    price_per_photo NUMERIC DEFAULT 0, -- 0 ise ücretsiz
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Düğün fotoğraflarının orijinal hallerini, küçük resimlerini ve kuyruk durumunu tutacak tablo
CREATE TABLE IF NOT EXISTS photos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    thumbnail_url TEXT, -- Hızlı yükleme için 800px vb. sıkıştırılmış versiyon
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. İşlenen fotoğraflardaki her bir yüzü ve detaylarını tutacak tablo
CREATE TABLE IF NOT EXISTS faces (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    photo_id UUID REFERENCES photos(id) ON DELETE CASCADE,
    embedding vector(512), -- InsightFace buffalo_l modeli 512 boyutlu vektör döner
    bbox JSONB NOT NULL,   -- Yüzün koordinatları [x1, y1, x2, y2] formatında JSON listesi olarak tutulacak
    det_score FLOAT,       -- Yüz tespit doğruluk oranı (opsiyonel)
    cluster_id INTEGER,    -- DBSCAN tarafından atanacak kişi kimliği
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Opsiyonel: Hızlı arama için indexler
CREATE INDEX IF NOT EXISTS faces_cluster_id_idx ON faces(cluster_id);
CREATE INDEX IF NOT EXISTS photos_processed_idx ON photos(processed);
CREATE INDEX IF NOT EXISTS photos_event_id_idx ON photos(event_id);
CREATE INDEX IF NOT EXISTS faces_embedding_idx ON faces USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 6. Siparişler (Sepet / Ödeme) Tablosu
CREATE TABLE IF NOT EXISTS orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    guest_name TEXT NOT NULL,
    guest_contact TEXT NOT NULL, -- Email veya Telefon
    photo_ids JSONB NOT NULL, -- Satın alınan/istenen fotoğrafların ID'leri listesi ["uuid1", "uuid2"]
    total_price NUMERIC NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, completed, cancelled
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 7. Yüz Tanıma Geri Bildirimleri (Bu ben değilim) Tablosu
CREATE TABLE IF NOT EXISTS feedbacks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    face_id UUID REFERENCES faces(id) ON DELETE CASCADE,
    photo_id UUID REFERENCES photos(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'wrong_match',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. RPC: Selfie ile Eşleşen Yüzleri Bulma Fonksiyonu
-- Bu fonksiyon, verilen bir embedding'e (selfie) en yakın yüzleri `faces` tablosundan Cosine Distance ile bulur.
CREATE OR REPLACE FUNCTION match_faces(query_embedding vector(512), match_threshold float, match_count int, target_event_id uuid)
RETURNS TABLE (
    face_id uuid,
    photo_id uuid,
    image_url text,
    thumbnail_url text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.id AS face_id,
        f.photo_id,
        p.image_url,
        p.thumbnail_url,
        1 - (f.embedding <=> query_embedding) AS similarity
    FROM faces f
    JOIN photos p ON f.photo_id = p.id
    WHERE p.event_id = target_event_id
      AND 1 - (f.embedding <=> query_embedding) > match_threshold
    ORDER BY f.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- RLS (Row Level Security) ayarları (Şimdilik public erişim, daha sonra Supabase Auth kısıtlamaları eklenecek)
ALTER TABLE studios ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE faces ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedbacks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public all for studios" ON studios FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public all for events" ON events FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public all for photos" ON photos FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public all for faces" ON faces FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public all for orders" ON orders FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public all for feedbacks" ON feedbacks FOR ALL USING (true) WITH CHECK (true);

-- Önemli Hata Çözümü: RLS açık bile olsa service_role ve anon'a temel yetkiler verilmelidir.
GRANT ALL ON public.orders TO anon, authenticated, service_role;
GRANT ALL ON public.feedbacks TO anon, authenticated, service_role;
