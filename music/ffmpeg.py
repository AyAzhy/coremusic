"""FFmpeg ses kaynağı üretici."""
from __future__ import annotations

import shutil

import discord

from utils.errors import FFmpegNotFound
from utils.logger import get_logger

log = get_logger("MUSIC")


class FFmpegPlayer:
    """FFmpeg yürütülebilir dosyasını bulur ve Discord ses kaynakları üretir."""

    # Akış kopunca yeniden bağlan; stdin'i kapat.
    # Not: FFmpeg'de "-lowest_delay" seçeneği yoktur, gerçek karşılığı "-flags low_delay"dir.
    BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin -flags low_delay"
    OPTIONS = "-vn -loglevel warning"

    def __init__(self, ffmpeg_path: str) -> None:
        self.executable: str | None = shutil.which(ffmpeg_path)
        if self.executable:
            log.info("FFmpeg bulundu: %s", self.executable)
        else:
            log.error("FFmpeg bulunamadı (FFMPEG_PATH=%s). Müzik çalınamaz!", ffmpeg_path)

    @property
    def available(self) -> bool:
        return self.executable is not None

    def create_source(self, stream_url: str, volume: float) -> discord.PCMVolumeTransformer:
        """Akış adresinden ses seviyesi ayarlanabilir bir kaynak oluşturur."""
        if not self.executable:
            raise FFmpegNotFound()
        try:
            source = discord.FFmpegPCMAudio(
                stream_url,
                executable=self.executable,
                before_options=self.BEFORE_OPTIONS,
                options=self.OPTIONS,
            )
        except (discord.ClientException, OSError) as exc:
            raise FFmpegNotFound(f"FFmpeg başlatılamadı: {exc}") from exc
        return discord.PCMVolumeTransformer(source, volume=volume)