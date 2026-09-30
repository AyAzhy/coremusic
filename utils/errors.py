"""Özel hata sınıfları ve Türkçe hata embedleri."""
from __future__ import annotations

import discord
from discord import app_commands

from utils.logger import get_logger

log = get_logger("BOT")

# Core Music Branding
ERROR_COLOR = discord.Color.from_rgb(237, 66, 69)
FOOTER_TEXT = "Made by rywax"
FOOTER_ICON = "https://i.hizliresim.com/zkcni0ij.png"


class MusicError(Exception):
    """Kullanıcıya gösterilebilir müzik hatalarının tabanı."""

    title = "❌ Hata"
    default_message = "Bir hata oluştu."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class NotInVoiceChannel(MusicError):
    title = "🔇 Ses kanalında değilsin"
    default_message = "Bu komutu kullanmak için önce bir ses kanalına katılmalısın."


class DifferentVoiceChannel(MusicError):
    title = "🔊 Farklı ses kanalı"
    default_message = "Bot şu anda başka bir ses kanalında. Onunla aynı kanalda olmalısın."


class SongNotFound(MusicError):
    title = "🔍 Şarkı bulunamadı"
    default_message = "Aramanla eşleşen bir sonuç bulunamadı."


class InvalidURL(MusicError):
    title = "🔗 Geçersiz URL"
    default_message = "Verdiğin bağlantı geçersiz veya desteklenmiyor."


class YouTubeError(MusicError):
    title = "📡 YouTube erişim hatası"
    default_message = "YouTube'a erişilemedi. Biraz sonra tekrar dene."


class FFmpegNotFound(MusicError):
    title = "🛠 FFmpeg bulunamadı"
    default_message = "FFmpeg kurulu değil veya FFMPEG_PATH yanlış. Bot sahibi kurulumu kontrol etmeli."


class VoiceConnectionError(MusicError):
    title = "🔌 Ses bağlantısı hatası"
    default_message = "Ses kanalına bağlanılamadı."


class PlaybackError(MusicError):
    title = "⚠️ Oynatma hatası"
    default_message = "Şarkı oynatılırken bir hata oluştu."


class EmptyQueue(MusicError):
    title = "📭 Kuyruk boş"
    default_message = "Kuyrukta şarkı yok."


class NothingPlaying(MusicError):
    title = "⏹ Çalan şarkı yok"
    default_message = "Şu anda çalan bir şarkı yok."


class QueueFull(MusicError):
    title = "📦 Kuyruk dolu"
    default_message = "Kuyruk maksimum kapasiteye ulaştı."


class MissingDJRole(MusicError):
    title = "🎧 DJ yetkisi gerekli"
    default_message = "Bu komut için DJ rolüne (veya Sunucuyu Yönet yetkisine) sahip olmalısın."


class MissingBotPermissions(MusicError):
    title = "🚫 Botun izinleri eksik"
    default_message = "Botun gerekli Discord izinleri yok."


def error_embed(message: str, title: str = "❌ Hata") -> discord.Embed:
    """Kırmızı hata embedi üretir."""
    embed = discord.Embed(title=title, description=message, color=ERROR_COLOR)
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed


async def handle_app_command_error(interaction: discord.Interaction, error: Exception) -> None:
    """Slash komut ve buton hatalarını Türkçe embed olarak gösterir."""
    original = getattr(error, "original", error)
    if isinstance(original, MusicError):
        embed = error_embed(original.message, original.title)
    elif isinstance(original, discord.Forbidden):
        embed = error_embed("Discord bu işleme izin vermedi. Botun kanal izinlerini kontrol et.", "🚫 Yetersiz izin")
    elif isinstance(error, app_commands.MissingPermissions):
        embed = error_embed("Bu komutu kullanmak için yetkin yok.", "🚫 Yetki yok")
    elif isinstance(error, app_commands.BotMissingPermissions):
        embed = error_embed("Botun bu işlem için gerekli izinleri yok.", "🚫 Botun izinleri eksik")
    elif isinstance(error, app_commands.CommandOnCooldown):
        embed = error_embed(f"Lütfen {error.retry_after:.0f} sn sonra tekrar dene.", "⏳ Bekle")
    elif isinstance(error, app_commands.CheckFailure):
        embed = error_embed(str(error) or "Bu komutu kullanamazsın.", "🚫 Yetki yok")
    else:
        log.error("Beklenmeyen hata: %s", original, exc_info=original)
        embed = error_embed("Beklenmeyen bir hata oluştu. Lütfen tekrar dene.")
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException as exc:
        log.error("Hata mesajı gönderilemedi: %s", exc)