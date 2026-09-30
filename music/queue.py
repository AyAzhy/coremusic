"""Şarkı modeli, enum'lar ve sunucu başına kuyruk."""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from enum import Enum

import discord

from utils.errors import MusicError, QueueFull


class LoopMode(Enum):
    """Döngü modları."""

    OFF = "off"
    SONG = "song"
    QUEUE = "queue"


class PlaybackState(Enum):
    """Oynatma durumu."""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass(slots=True)
class Song:
    """Kuyruktaki bir şarkı. `url` geçici ses akış adresidir, çalmadan önce yenilenir."""

    title: str
    webpage_url: str
    duration: int
    thumbnail: str | None
    requester: discord.Member | discord.User
    uploader: str
    url: str = ""
    resolved_at: float = 0.0
    retries: int = 0


class GuildQueue:
    """Tek bir sunucuya ait şarkı kuyruğu ve geçmişi."""

    def __init__(self, max_size: int = 500) -> None:
        self._items: deque[Song] = deque()
        self.history: deque[Song] = deque(maxlen=50)
        self._max_size = max_size

    def __len__(self) -> int:
        return len(self._items)

    @property
    def is_empty(self) -> bool:
        return not self._items

    @property
    def total_duration(self) -> int:
        return sum(s.duration for s in self._items)

    def add(self, song: Song) -> int:
        """Şarkıyı sona ekler ve 1 tabanlı sırasını döndürür."""
        if len(self._items) >= self._max_size:
            raise QueueFull()
        self._items.append(song)
        return len(self._items)

    def add_front(self, song: Song) -> None:
        """Şarkıyı başa ekler."""
        self._items.appendleft(song)

    def pop_next(self) -> Song | None:
        """Sıradaki şarkıyı çıkarır."""
        return self._items.popleft() if self._items else None

    def remove(self, index: int) -> Song:
        """1 tabanlı sıradaki şarkıyı kaldırır."""
        if not 1 <= index <= len(self._items):
            raise MusicError(f"Geçersiz sıra numarası. Kuyrukta {len(self._items)} şarkı var.")
        song = self._items[index - 1]
        del self._items[index - 1]
        return song

    def clear(self) -> int:
        """Kuyruğu temizler, silinen şarkı sayısını döndürür."""
        count = len(self._items)
        self._items.clear()
        return count

    def shuffle(self) -> None:
        """Kuyruğu karıştırır."""
        items = list(self._items)
        random.shuffle(items)
        self._items = deque(items)

    def snapshot(self) -> list[Song]:
        """Kuyruğun kopyasını döndürür."""
        return list(self._items)