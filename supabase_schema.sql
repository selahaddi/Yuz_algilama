-- 1. pgvector eklentisini aktif et (Vektör tabanlı benzerlik araması ve depolama için)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Düğün fotoğraflarının orijinal hallerini (URL) ve kuyruk durumunu tutacak tablo
CREATE TABLE IF NOT EXISTS photos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    image_url TEXT NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. İşlenen fotoğraflardaki her bir yüzü ve detaylarını tutacak tablo
CREATE TABLE IF NOT EXISTS faces (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    photo_id UUID REFERENCES photos(id) ON DELETE CASCADE,
    embedding vector(512), -- InsightFace buffalo_l modeli 512 boyutlu vektör döner
    bbox JSONB NOT NULL,   -- Yüzün koordinatları [x1, y1, x2, y2] formatında JSON listesi olarak tutulacak
    det_score FLOAT,       -- Yüz tespit doğruluk oranı (opsiyonel)
    cluster_id INTEGER,    -- DBSCAN tarafından atanacak kişi kimliği (örn: 0, 1, 2)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Opsiyonel: Hızlı arama için indexler
CREATE INDEX IF NOT EXISTS faces_cluster_id_idx ON faces(cluster_id);
CREATE INDEX IF NOT EXISTS photos_processed_idx ON photos(processed);

-- RLS (Row Level Security) ayarları (Test/Geliştirme için şimdilik anonim erişime açıyoruz, canlıda yetkilendirme eklenmelidir)
ALTER TABLE photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE faces ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read for photos" ON photos FOR SELECT USING (true);
CREATE POLICY "Allow public insert for photos" ON photos FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update for photos" ON photos FOR UPDATE USING (true);

CREATE POLICY "Allow public read for faces" ON faces FOR SELECT USING (true);
CREATE POLICY "Allow public insert for faces" ON faces FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update for faces" ON faces FOR UPDATE USING (true);
CREATE POLICY "Allow public delete for faces" ON faces FOR DELETE USING (true);
