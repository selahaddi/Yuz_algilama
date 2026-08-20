#!/bin/bash
# Yüz Tanıma ve Kategorizasyon Sistemi Başlatma Scripti

cd /home/selahaddin/Belgeler/Yüz_Tanıma_\&_Kategori

# Sanal ortam aktif değilse aktif et
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Sanal ortam (venv) bulunamadı. Kurulum yapılıyor..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

echo "Uygulama başlatılıyor..."
streamlit run app.py
