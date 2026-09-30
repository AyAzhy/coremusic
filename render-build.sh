#!/usr/bin/env bash
# Render.com için build script - FFmpeg'i otomatik kurar

set -e

echo "🔧 FFmpeg kuruluyor..."
apt-get update
apt-get install -y ffmpeg

echo "📦 Python bağımlılıkları yükleniyor..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Kurulum tamamlandı!"
