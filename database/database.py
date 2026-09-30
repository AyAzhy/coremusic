"""SQLite veritabanı katmanı (bloklamayan)."""
from __future__ import annotations

import asyncio
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import Config
from utils.logger import get_logger

log = get_logger("DATABASE")

_SETTING_FIELDS = {"dj_role_id", "default_volume", "leave_when_empty", "leave_timeout", "prefix", "language"}


@dataclass(slots=True)
class GuildSettings:
    """Sunucu ayarları."""

    guild_id: int
    dj_role_id: int | None
    default_volume: int
    leave_when_empty: bool
    leave_timeout: int
    prefix: str
    language: str


@dataclass(slots=True)
class GuildStats:
    """Sunucu istatistikleri."""

    guild_id: int
    played_songs: int
    total_play_time: int
    commands_used: int


class Database:
    """sqlite3 üzerinde asyncio.to_thread ile çalışan veritabanı sarmalayıcısı."""

    def __init__(self, path: str, config: Config) -> None:
        self._path = path
        self._config = config
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

    async def connect(self) -> None:
        """Bağlantıyı açar ve tabloları oluşturur."""
        await asyncio.to_thread(self._connect_sync)
        log.info("Veritabanı hazır: %s", self._path)

    def _connect_sync(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                dj_role_id INTEGER,
                default_volume INTEGER NOT NULL DEFAULT 50,
                leave_when_empty INTEGER NOT NULL DEFAULT 1,
                leave_timeout INTEGER NOT NULL DEFAULT 120,
                prefix TEXT NOT NULL DEFAULT '!',
                language TEXT NOT NULL DEFAULT 'tr'
            );
            CREATE TABLE IF NOT EXISTS guild_stats (
                guild_id INTEGER PRIMARY KEY,
                played_songs INTEGER NOT NULL DEFAULT 0,
                total_play_time INTEGER NOT NULL DEFAULT 0,
                commands_used INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        self._conn.commit()

    def _execute_sync(self, sql: str, params: tuple[Any, ...], fetch: str) -> Any:
        assert self._conn is not None, "Veritabanı bağlı değil"
        with self._lock:
            cur = self._conn.execute(sql, params)
            result = cur.fetchone() if fetch == "one" else cur.fetchall() if fetch == "all" else None
            self._conn.commit()
            return result

    async def _execute(self, sql: str, params: tuple[Any, ...] = (), fetch: str = "none") -> Any:
        return await asyncio.to_thread(self._execute_sync, sql, params, fetch)

    async def get_settings(self, guild_id: int) -> GuildSettings:
        """Sunucu ayarlarını döndürür (yoksa varsayılanlarla oluşturur)."""
        row = await self._execute("SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,), "one")
        if row is None:
            await self._execute(
                "INSERT OR IGNORE INTO guild_settings (guild_id, default_volume, leave_timeout) VALUES (?,?,?)",
                (guild_id, self._config.default_volume, self._config.leave_timeout),
            )
            row = await self._execute("SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,), "one")
        return GuildSettings(
            guild_id=row["guild_id"],
            dj_role_id=row["dj_role_id"],
            default_volume=row["default_volume"],
            leave_when_empty=bool(row["leave_when_empty"]),
            leave_timeout=row["leave_timeout"],
            prefix=row["prefix"],
            language=row["language"],
        )

    async def update_setting(self, guild_id: int, field: str, value: Any) -> None:
        """Tek bir ayarı günceller (alan adı beyaz listeden doğrulanır)."""
        if field not in _SETTING_FIELDS:
            raise ValueError(f"Geçersiz ayar alanı: {field}")
        await self.get_settings(guild_id)
        await self._execute(f"UPDATE guild_settings SET {field}=? WHERE guild_id=?", (value, guild_id))
        log.info("Ayar güncellendi: guild=%s %s=%s", guild_id, field, value)

    async def record_play(self, guild_id: int, seconds: int) -> None:
        """Çalınan şarkı sayısını ve süreyi artırır."""
        await self._execute(
            "INSERT INTO guild_stats (guild_id, played_songs, total_play_time) VALUES (?,1,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET played_songs=played_songs+1, "
            "total_play_time=total_play_time+excluded.total_play_time",
            (guild_id, max(0, seconds)),
        )

    async def increment_commands(self, guild_id: int) -> None:
        """Kullanılan komut sayısını artırır."""
        await self._execute(
            "INSERT INTO guild_stats (guild_id, commands_used) VALUES (?,1) "
            "ON CONFLICT(guild_id) DO UPDATE SET commands_used=commands_used+1",
            (guild_id,),
        )

    async def get_stats(self, guild_id: int) -> GuildStats:
        """Sunucu istatistiklerini döndürür."""
        row = await self._execute("SELECT * FROM guild_stats WHERE guild_id=?", (guild_id,), "one")
        if row is None:
            return GuildStats(guild_id, 0, 0, 0)
        return GuildStats(row["guild_id"], row["played_songs"], row["total_play_time"], row["commands_used"])

    async def close(self) -> None:
        """Bağlantıyı kapatır."""
        if self._conn is not None:
            await asyncio.to_thread(self._conn.close)
            self._conn = None
            log.info("Veritabanı kapatıldı.")
