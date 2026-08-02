#!/bin/bash
# Yüz Tanıma ve Kategorizasyon Sistemi Komple Başlatıcı

echo "Proje dizinine geçiliyor..."
cd "/home/selahaddin/Belgeler/Yüz_Tanıma_&_Kategori" || { echo "Klasör bulunamadı"; read -p "Kapatmak için Enter'a basın..."; exit 1; }

echo "Sanal ortam (venv) aktif ediliyor..."
source venv/bin/activate || { echo "Venv bulunamadı"; read -p "Kapatmak için Enter'a basın..."; exit 1; }

echo "Arka plan AI İşçisi (worker.py) başlatılıyor..."
python worker.py &
WORKER_PID=$!

# Terminal kapandığında veya Ctrl+C yapıldığında worker işlemini de sonlandır
trap "kill $WORKER_PID 2>/dev/null" EXIT

echo "Arayüz (Streamlit) başlatılıyor..."
streamlit run app.py || { echo "Streamlit başlatılamadı!"; }

echo "----------------------------------------"
echo "Program kapandı veya bir hata oluştu."
read -p "Pencereyi kapatmak için Enter'a basın..."
