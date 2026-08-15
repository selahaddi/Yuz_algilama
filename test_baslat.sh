#!/bin/bash
# Yüz Tanıma ve Kategorizasyon Sistemi - Test Aracı Başlatma Scripti

cd /home/selahaddin/Belgeler/Yüz_Tanıma_\&_Kategori

# Sanal ortam aktif değilse aktif et
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Sanal ortam (venv) bulunamadı. Lütfen önce kurulumu tamamlayın."
    exit 1
fi

echo "Test uygulaması başlatılıyor..."
streamlit run test_app.py
