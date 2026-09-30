"""Embed üreticileri."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from music.queue import LoopMode, PlaybackState, Song

if TYPE_CHECKING:
    from music.player import GuildPlayer

# Core Music Branding
MAIN_COLOR = discord.Color.from_rgb(255, 73, 130)  # Premium pembe
SUCCESS_COLOR = discord.Color.from_rgb(87, 242, 135)  # Neon yeşil
ERROR_COLOR = discord.Color.from_rgb(237, 66, 69)  # Kırmızı
FOOTER_TEXT = "Made by rywax"
FOOTER_ICON = "https://i.hizliresim.com/zkcni0ij.png"  # İsterseniz kendi logonuzu ekleyin
LOOP_LABELS = {LoopMode.OFF: "Kapalı", LoopMode.SONG: "Şarkı", LoopMode.QUEUE: "Kuyruk"}


def format_duration(seconds: int) -> str:
    """Saniyeyi h:mm:ss / m:ss biçimine çevirir."""
    if seconds <= 0:
        return "🔴 Canlı"
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def clean(text: str, limit: int = 60) -> str:
    """Markdown'ı bozan karakterleri temizler ve metni kısaltır."""
    text = text.replace("[", "(").replace("]", ")").replace("`", "'")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def info_embed(title: str, description: str = "", color: discord.Color = MAIN_COLOR) -> discord.Embed:
    """Genel bilgi embedi."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed


def now_playing_embed(player: GuildPlayer) -> discord.Embed:
    """Şu an çalan şarkının premium embedi."""
    song = player.current
    if song is None:
        return info_embed("⏹ Çalma durdu", "Kuyruk bitti. Yeni şarkı için `/play` kullan.")
    title = "⏸ Duraklatıldı" if player.state is PlaybackState.PAUSED else "🎵 Şu an çalıyor"
    link = song.webpage_url or song.url
    embed = discord.Embed(
        title=title,
        description=f"**[{clean(song.title, 90)}]({link})**",
        color=MAIN_COLOR
    )
    embed.add_field(name="👤 İsteyen", value=song.requester.mention, inline=True)
    embed.add_field(name="⏱ Süre", value=format_duration(song.duration), inline=True)
    embed.add_field(name="🎤 Sanatçı", value=clean(song.uploader, 40), inline=True)
    embed.add_field(name="🔗 Link", value=f"[Kaynağı aç]({link})", inline=False)
    
    if song.thumbnail:
        embed.set_image(url=song.thumbnail)  # Thumbnail yerine büyük image
    
    # Premium footer
    footer_text = f"🔊 %{round(player.volume * 100)}  •  🔁 {LOOP_LABELS[player.loop_mode]}  •  📜 Sırada: {len(player.queue)}  •  {FOOTER_TEXT}"
    embed.set_footer(text=footer_text, icon_url=FOOTER_ICON)
    
    return embed


def added_embed(song: Song, position: int, started: bool) -> discord.Embed:
    """Kuyruğa ekleme bildirimi."""
    link = song.webpage_url or song.url
    heading = "▶️ Çalmaya başlıyor" if started else f"✅ Kuyruğa eklendi (#{position})"
    embed = discord.Embed(
        title=heading,
        description=f"**[{clean(song.title, 90)}]({link})**",
        color=SUCCESS_COLOR
    )
    embed.add_field(name="⏱ Süre", value=format_duration(song.duration), inline=True)
    embed.add_field(name="🎤 Sanatçı", value=clean(song.uploader, 40), inline=True)
    embed.add_field(name="👤 İsteyen", value=song.requester.mention, inline=True)
    
    if song.thumbnail:
        embed.set_thumbnail(url=song.thumbnail)
    
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed


def queue_embed(player: GuildPlayer, page: int, per_page: int = 10) -> discord.Embed:
    """Sayfalı kuyruk embedi."""
    items = player.queue.snapshot()
    pages = max(1, -(-len(items) // per_page))
    page = min(max(page, 1), pages)
    embed = discord.Embed(title="📜 Şarkı Kuyruğu", color=MAIN_COLOR)
    
    if player.current:
        embed.add_field(
            name="🎵 Şu an çalıyor",
            value=f"[{clean(player.current.title)}]({player.current.webpage_url}) • {format_duration(player.current.duration)}",
            inline=False,
        )
    
    start = (page - 1) * per_page
    lines = [
        f"`{start + i}.` [{clean(s.title, 50)}]({s.webpage_url}) • {format_duration(s.duration)} • {s.requester.display_name}"
        for i, s in enumerate(items[start : start + per_page], 1)
    ]
    embed.add_field(name="⏭ Sırada", value="\n".join(lines) or "Kuyruk boş.", inline=False)
    
    footer_text = f"Sayfa {page}/{pages} • {len(items)} şarkı • Toplam {format_duration(player.queue.total_duration)} • 🔁 {LOOP_LABELS[player.loop_mode]} • {FOOTER_TEXT}"
    embed.set_footer(text=footer_text, icon_url=FOOTER_ICON)
    
    return embed