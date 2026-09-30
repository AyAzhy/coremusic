"""yt-dlp tabanlı YouTube servisi (event loop'u bloklamaz)."""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Any

import discord
import yt_dlp

from music.queue import Song
from utils.errors import InvalidURL, SongNotFound, YouTubeError
from utils.logger import get_logger

log = get_logger("MUSIC")

URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
STREAM_TTL = 300  # saniye; akış adresleri kısa ömürlüdür


@dataclass(slots=True)
class SearchResult:
    """/search sonucu satırı."""

    title: str
    webpage_url: str
    duration: int
    uploader: str


class YouTubeService:
    """Arama ve akış adresi çözümleme işlemleri."""

    def __init__(self) -> None:
        self._opts: dict[str, Any] = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": 15,
            "source_address": "0.0.0.0",
        }
        self._semaphore = asyncio.Semaphore(3)

    def _extract(self, target: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Bloklayan yt-dlp çağrısı; thread içinde çalıştırılır."""
        try:
            with yt_dlp.YoutubeDL({**self._opts, **(extra or {})}) as ydl:
                info = ydl.extract_info(target, download=False)
        except yt_dlp.utils.YoutubeDLError as exc:
            message = ANSI_RE.sub("", str(exc)).replace("ERROR: ", "")
            if "Unsupported URL" in message:
                raise InvalidURL() from exc
            raise YouTubeError(f"Kaynağa erişilemedi: {message[:200]}") from exc
        if info is None:
            raise SongNotFound()
        return info

    async def _fetch(self, target: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._semaphore:
            info = await asyncio.to_thread(self._extract, target, extra)
        if "entries" in info:
            entries = [e for e in info["entries"] if e]
            if not entries:
                raise SongNotFound()
            info = entries[0]
        return info

    async def resolve(self, query: str, requester: discord.Member | discord.User) -> Song:
        """URL veya arama metninden Song üretir."""
        query = query.strip()
        if query.lower().startswith(("http://", "https://")) and not URL_RE.match(query):
            raise InvalidURL()
        target = query if URL_RE.match(query) else f"ytsearch1:{query}"
        info = await self._fetch(target)
        song = self._to_song(info, requester, fallback_url=query if URL_RE.match(query) else "")
        log.info("Çözümlendi: %s", song.title)
        return song

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Hızlı (flat) arama; birden fazla sonuç döndürür."""
        async with self._semaphore:
            info = await asyncio.to_thread(self._extract, f"ytsearch{limit}:{query}", {"extract_flat": True})
        results: list[SearchResult] = []
        for entry in info.get("entries") or []:
            if not entry:
                continue
            url = entry.get("url") or (f"https://www.youtube.com/watch?v={entry['id']}" if entry.get("id") else "")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=entry.get("title") or "Bilinmeyen",
                    webpage_url=url,
                    duration=int(entry.get("duration") or 0),
                    uploader=entry.get("uploader") or entry.get("channel") or "Bilinmiyor",
                )
            )
        if not results:
            raise SongNotFound()
        return results

    async def refresh_stream(self, song: Song) -> None:
        """Akış adresi eskimişse yeniden çözer."""
        if song.url and time.monotonic() - song.resolved_at < STREAM_TTL:
            return
        info = await self._fetch(song.webpage_url)
        stream = info.get("url")
        if not stream:
            raise YouTubeError("Ses akışı adresi alınamadı.")
        song.url = stream
        song.resolved_at = time.monotonic()

    @staticmethod
    def _to_song(info: dict[str, Any], requester: discord.Member | discord.User, fallback_url: str) -> Song:
        return Song(
            title=info.get("title") or "Bilinmeyen şarkı",
            webpage_url=info.get("webpage_url") or info.get("original_url") or fallback_url,
            duration=int(info.get("duration") or 0),
            thumbnail=info.get("thumbnail"),
            requester=requester,
            uploader=info.get("uploader") or info.get("channel") or "Bilinmiyor",
            url=info.get("url") or "",
            resolved_at=time.monotonic(),
        )
