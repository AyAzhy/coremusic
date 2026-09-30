# 🚀 Render.com'a Deploy Rehberi

## Gereksinimler
- GitHub/GitLab hesabı
- Render.com hesabı
- Discord Bot Token

## Adım 1: Repoyu Oluştur
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <repo-url>
git push -u origin main
```

## Adım 2: Render'da Yeni Servis Oluştur

1. [Render Dashboard](https://dashboard.render.com) > **New** > **Web Service**
2. Repoyu bağla
3. Ayarları yap:
   - **Name**: music-bot (veya istediğin isim)
   - **Runtime**: Python 3
   - **Build Command**: `bash render-build.sh`
   - **Start Command**: `python main.py`
   - **Instance Type**: Free (veya Starter)

## Adım 3: Environment Variables Ekle

Render panelinde **Environment** sekmesine git:

```
DISCORD_TOKEN=your_bot_token_here
FFMPEG_PATH=ffmpeg
DATABASE_PATH=/opt/render/project/src/data/musicbot.db
LOG_LEVEL=INFO
```

## FFmpeg Kurulumu (3 Yöntem)

### ✅ Yöntem 1: Build Script (Önerilen)
`render-build.sh` dosyası otomatik kuracak (zaten hazır)

### ✅ Yöntem 2: Aptfile
`aptfile` dosyası Render tarafından otomatik okunur (zaten hazır)

### ✅ Yöntem 3: render.yaml
Repo root'da `render.yaml` var, Render otomatik algılar (Blueprint)

## Adım 4: Deploy

Tüm ayarları yaptıktan sonra **Create Web Service** > Deploy başlayacak!

## ⚠️ Önemli Notlar

1. **Free Plan Sınırlamaları:**
   - 750 saat/ay ücretsiz
   - 15 dakika inaktivite sonrası uyur
   - İlk istekte 30-60 sn başlatma süresi

2. **Database:**
   - Free plan'da disk kalıcı DEĞİL
   - Önemli veriler için Render Persistent Disk ekle (ücretli)
   - Ya da dış PostgreSQL kullan

3. **Ses Kalitesi:**
   - Free plan düşük CPU, ses kesintisi olabilir
   - Starter ($7/ay) önerilir

## 🐛 Sorun Giderme

### Bot başlamıyor:
```bash
# Render logs'a bak:
# Dashboard > Service > Logs
```

### FFmpeg bulunamıyor:
```bash
# Build log'da şunu ara:
# "FFmpeg kuruluyor..."
# Yoksa render-build.sh çalışmamış
```

### Database hatası:
```bash
# data/ klasörünün oluştuğunu kontrol et
# veya DATABASE_PATH'i güncelle
```

## 🎉 Başarılı Deploy Sonrası

Bot online olacak! Discord'da `/play` ile test et.

---

**Faydalı Linkler:**
- [Render Python Docs](https://render.com/docs/deploy-python)
- [Discord.py Voice](https://discordpy.readthedocs.io/en/stable/api.html#voice-related)
- [FFmpeg Docs](https://ffmpeg.org/documentation.html)
