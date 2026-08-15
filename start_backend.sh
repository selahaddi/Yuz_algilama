#!/bin/bash
# ========================================
# Yüz Tanıma SaaS - Komple Backend Başlatıcı
# ========================================

echo "Sistem başlatılıyor..."

# 1. Proje dizinine geç ve Venv aktif et
cd "/home/selahaddin/Belgeler/Yüz_Tanıma_SaaS" || exit 1
source "../Yüz_Tanıma_&_Kategori/venv/bin/activate" 2>/dev/null || { echo "Venv bulunamadı!"; exit 1; }

# 2. Worker (Arkaplan Yapay Zeka İşçisi)
echo "[1/4] Arka plan AI İşçisi (worker.py) başlatılıyor..."
python worker.py &
WORKER_PID=$!

# 3. Studio App (Fotoğrafçı Paneli)
echo "[2/4] Stüdyo Yönetim Paneli (studio_app.py) başlatılıyor..."
streamlit run studio_app.py --server.port 8504 &
STUDIO_PID=$!

# 4. Guest API (FastAPI)
echo "[3/4] Misafir API (guest_api.py) başlatılıyor..."
uvicorn guest_api:app --port 8503 &
API_PID=$!

# 5. LocalTunnel ile Dışarı Açma
echo "[4/4] LocalTunnel ile 8503 portu internete açılıyor..."
npx -y localtunnel --port 8503 > lt.log 2>&1 &
LT_PID=$!

echo "LocalTunnel URL bekleniyor (ilk kurulumda 5-10 saniye sürebilir)..."
sleep 6
LT_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.loca\.lt' lt.log | tail -n 1)

if [ -z "$LT_URL" ]; then
    sleep 4
    LT_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.loca\.lt' lt.log | tail -n 1)
fi

if [ -z "$LT_URL" ]; then
    echo "LocalTunnel URL alınamadı! (Ağ bağlantınızı veya npm kurulumunuzu kontrol edin)"
else
    echo "=================================================="
    echo "✅ SISTEM BAŞARIYLA BAŞLATILDI"
    echo "=================================================="
    echo "📡 LocalTunnel URL: $LT_URL"
    echo "⚠️  Lütfen public/vercel.json dosyasındaki URL kısmını bu adresle güncelleyin ve Vercel'e pushlayın!"
    echo "=================================================="
fi

# Uygulamayı kapatırken hepsini durdurma
cleanup() {
    echo "Sistem kapatılıyor..."
    kill $WORKER_PID $STUDIO_PID $API_PID $LT_PID 2>/dev/null
    echo "Tüm süreçler sonlandırıldı."
}
trap cleanup EXIT INT TERM

wait
