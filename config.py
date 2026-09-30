"""Ortam değişkenlerinden yapılandırmayı yükler."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Config:
    """Bot yapılandırması."""

    token: str
    ffmpeg_path: str
    database_path: str
    dev_guild_id: int | None
    log_level: str
    default_volume: int = 50
    leave_timeout: int = 120
    max_queue_size: int = 500


def load_config() -> Config:
    """`.env` dosyasını okuyup Config üretir."""
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit("DISCORD_TOKEN bulunamadı. .env dosyasını kontrol et.")
    dev_guild = os.getenv("DEV_GUILD_ID", "").strip()
    return Config(
        token=token,
        ffmpeg_path=os.getenv("FFMPEG_PATH", "ffmpeg").strip() or "ffmpeg",
        database_path=os.getenv("DATABASE_PATH", "data/musicbot.db").strip(),
        dev_guild_id=int(dev_guild) if dev_guild.isdigit() else None,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )