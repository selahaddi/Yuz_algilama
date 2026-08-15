#!/bin/bash
echo "🚀 GitHub'a yükleniyor..."

# Tüm değişen dosyaları (public/vercel.json ve diğerleri) ekle
git add .

# Otomatik saat ve tarih ile commit at
git commit -m "Vercel güncellemesi: $(date +'%Y-%m-%d %H:%M:%S')"

# Mevcut depoya (Yuz_algilama) gönder
git push origin master

echo "=================================================="
echo "✅ Başarıyla yüklendi!"
echo "⚠️ Vercel'in bu güncellemeyi algılayıp siteyi yayınlaması 1-2 dakika sürebilir."
echo "=================================================="
