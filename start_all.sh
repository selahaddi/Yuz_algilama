#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Yüz Tanıma ve Kategorizasyon Sistemi — Komple Başlatıcı
# Worker otomatik restart mekanizması dahil
# ═══════════════════════════════════════════════════════════════════════════════

echo "========================================"
echo "  Düğün Fotoğraf Galerisi Sistemi"
echo "========================================"

# Proje dizinine geç
cd "/home/selahaddin/Belgeler/Yüz_Tanıma_&_Kategori" || { echo "Klasör bulunamadı!"; read -p "Kapatmak için Enter'a basın..."; exit 1; }

# Sanal ortam (venv) aktif et
echo "Sanal ortam aktif ediliyor..."
source venv/bin/activate || { echo "Venv bulunamadı! 'python3 -m venv venv' ile oluşturun."; read -p "Kapatmak için Enter'a basın..."; exit 1; }

# ─── Worker'ı Otomatik Restart ile Başlat ──────────────────────────────────────
echo "Arka plan AI İşçisi (worker.py) başlatılıyor (otomatik restart aktif)..."

(
    RESTART_COUNT=0
    MAX_RESTARTS=20
    
    while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
        python worker.py
        EXIT_CODE=$?
        RESTART_COUNT=$((RESTART_COUNT + 1))
        
        if [ $EXIT_CODE -eq 0 ]; then
            echo "Worker normal şekilde kapandı."
            break
        fi
        
        echo "[$(date)] Worker çöktü (exit: $EXIT_CODE)! $RESTART_COUNT/$MAX_RESTARTS yeniden başlatılıyor... (5sn bekleniyor)"
        sleep 5
    done
    
    if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
        echo "[$(date)] Worker $MAX_RESTARTS kez çöktü. Otomatik restart durduruldu."
    fi
) &
WORKER_PID=$!

# Terminal kapandığında veya Ctrl+C yapıldığında worker işlemini de sonlandır
cleanup() {
    echo ""
    echo "Sistem kapatılıyor..."
    kill $WORKER_PID 2>/dev/null
    # Alt süreçleri de temizle
    pkill -P $WORKER_PID 2>/dev/null
    wait $WORKER_PID 2>/dev/null
    echo "Tüm süreçler sonlandırıldı."
}
trap cleanup EXIT INT TERM

echo "Arayüz (Streamlit) başlatılıyor..."
streamlit run app.py || { echo "Streamlit başlatılamadı!"; }

echo "----------------------------------------"
echo "Program kapandı veya bir hata oluştu."
read -p "Pencereyi kapatmak için Enter'a basın..."
