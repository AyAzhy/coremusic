# 🎵 Core Music

**Premium Discord Müzik Botu** - Kesintisiz müzik deneyimi için tasarlandı!

Made by **rywax** 💜

---

## ✨ Özellikler

- 🎶 **YouTube Desteği** - Şarkı adı veya link ile çal
- 🔍 **Akıllı Arama** - YouTube'da ara, seçip çal
- 🎮 **Interaktif Kontroller** - Embed'e gömülü şık butonlar
- 📜 **Kuyruk Sistemi** - Sınırsız şarkı sırası
- 🔁 **Döngü Modları** - Şarkı / Kuyruk / Kapalı
- 🔀 **Shuffle** - Kuyruğu karıştır
- 🎧 **DJ Rolü** - Sunucu yöneticileri için özel kontrol
- 📊 **İstatistikler** - Sunucu bazlı müzik istatistikleri
- 🎨 **Premium Tasarım** - Özel renkler ve "Made by rywax" branding
- 🚀 **Render Ready** - Tek tıkla cloud'a deploy

---

## 🎮 Komutlar

### 🎶 Müzik
- `/play [sorgu]` - Şarkı çal (YouTube link veya arama)
- `/search [sorgu]` - YouTube'da ara ve seç
- `/pause` - Şarkıyı duraklat
- `/resume` - Devam ettir
- `/nowplaying` - Çalan şarkıyı göster (butonlarla)
- `/queue [sayfa]` - Şarkı kuyruğunu göster
- `/loop [mod]` - Döngü modu ayarla

### 🎧 DJ Komutları
- `/skip` - Şarkıyı atla
- `/stop` - Müziği durdur, kuyruğu temizle
- `/clear` - Kuyruğu temizle
- `/remove [sıra]` - Kuyruktan şarkı sil
- `/shuffle` - Kuyruğu karıştır
- `/volume [0-100]` - Ses seviyesini ayarla
- `/disconnect` - Botu ses kanalından çıkar

### ⚙️ Ayarlar & Diğer
- `/yardim` - Bu komutu göster
- `/ping` - Bot gecikmesini ölç
- `/istatistik` - Sunucu müzik istatistikleri
- `/ayar goster` - Sunucu ayarlarını göster
- `/ayar dj [rol]` - DJ rolü ayarla
- `/ayar ses [0-100]` - Varsayılan ses
- `/ayar bekleme [saniye]` - Boşta kalınca ayrılma süresi
- `/ayar otomatik_ayril [açık/kapalı]` - Otomatik ayrılma

---

## 🚀 Kurulum (Lokal)

### 1. Gereksinimleri Yükle

```bash
# Python 3.11+ gerekli
pip install -r requirements.txt
```

### 2. FFmpeg Kur

**Windows (Chocolatey):**
```powershell
choco install ffmpeg
```

**Windows (Winget):**
```powershell
winget install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

### 3. .env Dosyası Oluştur

```env
DISCORD_TOKEN=your_bot_token_here
FFMPEG_PATH=ffmpeg
DATABASE_PATH=data/musicbot.db
LOG_LEVEL=INFO
DEV_GUILD_ID=  # Opsiyonel: test sunucusu ID'si
```

### 4. Botu Başlat

```bash
python main.py
```

---

## ☁️ Render.com'a Deploy

### Hızlı Deploy (Blueprint)

1. Bu repoyu GitHub'a pushla
2. [Render Dashboard](https://dashboard.render.com) > **New** > **Blueprint**
3. Repoyu seç
4. Environment Variables ekle:
   - `DISCORD_TOKEN`: Bot tokenin

Deploy otomatik başlar! FFmpeg `render-build.sh` ile otomatik kurulur.

### Manuel Deploy

Detaylı rehber için: [RENDER_DEPLOY.md](./RENDER_DEPLOY.md)

---

## 🎨 Branding & Tasarım

- **Renk Şeması:**
  - Ana: `#FF4982` (Premium pembe)
  - Başarı: `#57F287` (Neon yeşil)
  - Hata: `#ED4245` (Kırmızı)

- **Footer:** Her embed'de "Made by rywax" görünür

- **Butonlar:** Emoji-first tasarım, compact layout

- **Bot Aktivitesi:** "Core Music 🎵 | /play"

---

## 📁 Proje Yapısı

```
music/
├── commands/          # Slash komutları
│   ├── music.py       # Müzik komutları
│   └── utility.py     # Yardımcı komutlar
├── database/          # Veritabanı
│   └── database.py    # SQLite yönetimi
├── music/             # Müzik motoru
│   ├── ffmpeg.py      # FFmpeg wrapper
│   ├── manager.py     # Müzik manager
│   ├── player.py      # Guild player
│   ├── queue.py       # Kuyruk sistemi
│   └── youtube.py     # YouTube resolver
├── utils/             # Yardımcılar
│   ├── embeds.py      # Premium embedler
│   ├── errors.py      # Hata yönetimi
│   └── logger.py      # Logging
├── views/             # Discord UI
│   └── music_controls.py  # Butonlar
├── data/              # Veritabanı dosyaları
├── main.py            # Bot entry point
├── config.py          # Konfigürasyon
└── requirements.txt   # Python dependencies
```

---

## 🛠 Gereksinimler

- Python 3.11+
- FFmpeg
- Discord.py 2.6+
- yt-dlp

Detaylar: [requirements.txt](./requirements.txt)

---

## 📝 Lisans

Bu proje **rywax** tarafından geliştirilmiştir.

---

## 🐛 Sorun Bildirimi

Herhangi bir bug veya öneri için issue açabilirsiniz!

---

## 💜 Made by rywax

**Core Music** - Premium Discord Müzik Botu Deneyimi

[GitHub](https://github.com/rywax) | [Discord](https://discord.gg/your-server)
