"""Sunucu başına bağımsız oynatıcı (GuildPlayer)."""
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import discord

from music.queue import GuildQueue, LoopMode, PlaybackState, Song
from utils.embeds import info_embed, now_playing_embed
from utils.errors import (
    EmptyQueue,
    MusicError,
    NothingPlaying,
    PlaybackError,
    VoiceConnectionError,
    error_embed,
)
from utils.logger import get_logger
from views.music_controls import MusicControls

if TYPE_CHECKING:
    from music.manager import MusicManager

log = get_logger("MUSIC")
voice_log = get_logger("VOICE")
queue_log = get_logger("QUEUE")

MAX_RETRIES = 2


class GuildPlayer:
    """Bir sunucunun kuyruğunu, ses bağlantısını ve oynatma durumunu yönetir."""

    def __init__(self, manager: MusicManager, guild: discord.Guild, text_channel: discord.abc.Messageable | None, volume: float) -> None:
        self.manager = manager
        self.bot = manager.bot
        self.guild = guild
        self.text_channel = text_channel
        self.queue = GuildQueue(manager.config.max_queue_size)
        self.current: Song | None = None
        self.volume = volume
        self.loop_mode = LoopMode.OFF
        self.state = PlaybackState.IDLE
        self.controls_message: discord.Message | None = None
        self._view: MusicControls | None = None
        self._source: discord.PCMVolumeTransformer | None = None
        self._lock = asyncio.Lock()
        self._gen = 0
        self._closed = False
        self._skip_requested = False
        self._suppress_history = False
        self._forced_next: Song | None = None
        self._started_at = 0.0
        self._last_channel_id: int | None = None
        self._leave_task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------ ses
    @property
    def voice_client(self) -> discord.VoiceClient | None:
        vc = self.guild.voice_client
        return vc if isinstance(vc, discord.VoiceClient) else None

    def channel_is_empty(self) -> bool:
        """Botun kanalında insan kalmadıysa True."""
        vc = self.voice_client
        if vc is None or vc.channel is None:
            return True
        return not any(not m.bot for m in vc.channel.members)

    async def connect(self, channel: discord.VoiceChannel | discord.StageChannel) -> None:
        """Ses kanalına bağlanır veya taşınır."""
        vc = self.voice_client
        try:
            if vc is not None and vc.is_connected():
                if vc.channel.id != channel.id:
                    await vc.move_to(channel)
                    voice_log.info("Kanal taşındı: %s (%s)", channel.name, self.guild.name)
            else:
                if vc is not None:
                    await vc.disconnect(force=True)
                await channel.connect(timeout=20.0, reconnect=True, self_deaf=True)
                voice_log.info("Bağlanıldı: %s (%s)", channel.name, self.guild.name)
        except (asyncio.TimeoutError, discord.ClientException, discord.HTTPException, RuntimeError) as exc:
            voice_log.error("Bağlantı hatası: %s", exc)
            raise VoiceConnectionError(f"Ses kanalına bağlanılamadı: {exc}") from exc
        self._last_channel_id = channel.id

    async def _ensure_voice(self) -> bool:
        """Bağlantı koptuysa son kanala yeniden bağlanmayı dener."""
        vc = self.voice_client
        if vc is not None and vc.is_connected():
            return True
        channel = self.guild.get_channel(self._last_channel_id) if self._last_channel_id else None
        if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            return False
        try:
            await self.connect(channel)
            return True
        except MusicError:
            return False

    # ------------------------------------------------------------- kuyruk/oynatma
    async def add(self, song: Song) -> tuple[int, bool]:
        """Şarkıyı ekler; boşta ise çalmaya başlar. (sıra, başladı_mı) döndürür."""
        async with self._lock:
            if self._closed:
                raise VoiceConnectionError("Oynatıcı kapatıldı, lütfen tekrar dene.")
            position = self.queue.add(song)
            queue_log.info("Eklendi: %s (#%d, %s)", song.title, position, self.guild.name)
            if self.state is PlaybackState.IDLE:
                await self._advance(strict=True)
                return 0, True
            return position, False

    async def _advance(self, finished: Song | None = None, skipped: bool = False, *, strict: bool = False) -> None:
        """Sıradaki çalınabilir şarkıyı başlatır (kilit tutulurken çağrılır)."""
        forced, self._forced_next = self._forced_next, None
        while True:
            if forced is not None:
                nxt, forced = forced, None
            elif finished is not None and self.loop_mode is LoopMode.SONG and not skipped:
                nxt = finished
            else:
                if finished is not None and self.loop_mode is LoopMode.QUEUE:
                    self.queue.add(finished)
                nxt = self.queue.pop_next()
            finished, skipped = None, False
            if nxt is None:
                self.current = None
                self.state = PlaybackState.IDLE
                await self._on_idle()
                return
            try:
                await self._play(nxt)
                return
            except MusicError as exc:
                log.error("Oynatılamadı '%s': %s", nxt.title, exc.message)
                if strict:
                    self.current, self.state = None, PlaybackState.IDLE
                    self.schedule_leave()
                    raise
                await self._send(embed=error_embed(f"**{nxt.title}** oynatılamadı: {exc.message}", exc.title))

    async def _play(self, song: Song) -> None:
        vc = self.voice_client
        if vc is None or not vc.is_connected():
            raise VoiceConnectionError("Ses bağlantısı yok.")
        await self.manager.youtube.refresh_stream(song)
        source = self.manager.ffmpeg.create_source(song.url, self.volume)
        self._gen += 1
        gen = self._gen

        def after(error: Exception | None) -> None:
            fut = asyncio.run_coroutine_threadsafe(self._on_finished(gen, error), self.bot.loop)
            fut.add_done_callback(self._log_future)

        try:
            vc.play(source, after=after)
        except discord.ClientException as exc:
            source.cleanup()
            raise PlaybackError(str(exc)) from exc
        self._source = source
        self.current = song
        self.state = PlaybackState.PLAYING
        self._started_at = time.monotonic()
        self._cancel_leave()
        log.info("Çalıyor: %s (%s)", song.title, self.guild.name)
        await self._send_now_playing()

    @staticmethod
    def _log_future(fut: "asyncio.Future[None]") -> None:
        if not fut.cancelled() and fut.exception() is not None:
            log.error("after callback hatası", exc_info=fut.exception())

    async def _on_finished(self, gen: int, error: Exception | None) -> None:
        """Şarkı bitince/kopunca (after callback'ten güvenle) çağrılır."""
        async with self._lock:
            if self._closed or gen != self._gen:
                return
            finished, self.current = self.current, None
            self._source = None
            self.state = PlaybackState.IDLE
            skipped, self._skip_requested = self._skip_requested, False
            suppress, self._suppress_history = self._suppress_history, False
            repeating = self.loop_mode is LoopMode.SONG and not skipped and error is None

            if finished is not None:
                elapsed = int(time.monotonic() - self._started_at)
                try:
                    await self.manager.database.record_play(self.guild.id, min(elapsed, finished.duration or elapsed))
                except Exception:
                    log.exception("İstatistik kaydedilemedi")

            if error is not None and finished is not None:
                log.error("Oynatma hatası '%s': %s", finished.title, error)
                near_end = finished.duration > 0 and elapsed >= finished.duration - 5
                if not near_end and finished.retries < MAX_RETRIES:
                    finished.retries += 1
                    finished.url = ""
                    await asyncio.sleep(1.5)
                    if await self._ensure_voice():
                        voice_log.info("Şarkı yeniden deneniyor (%d)", finished.retries)
                        self._forced_next, finished = finished, None
                    else:
                        await self._send(embed=error_embed("Ses bağlantısı koptu ve yeniden kurulamadı."))
                        await self.manager.players.destroy(self.guild.id)
                        return
                elif not near_end:
                    await self._send(embed=error_embed(f"**{finished.title}** oynatılırken hata oluştu, sıradakine geçiliyor.", "⚠️ Oynatma hatası"))
            elif finished is not None and not suppress and not repeating:
                self.queue.history.append(finished)

            if suppress:
                finished = None  # "önceki" komutunda mevcut şarkı zaten kuyruğa geri kondu
            await self._advance(finished, skipped)

    async def _on_idle(self) -> None:
        await self._clear_controls(delete=False)
        self.schedule_leave()

    # ---------------------------------------------------------------- kontroller
    def pause(self) -> None:
        vc = self.voice_client
        if self.state is not PlaybackState.PLAYING or vc is None:
            raise MusicError("Şu anda duraklatılabilecek bir şarkı yok.")
        vc.pause()
        self.state = PlaybackState.PAUSED

    def resume(self) -> None:
        vc = self.voice_client
        if self.state is not PlaybackState.PAUSED or vc is None:
            raise MusicError("Şarkı zaten çalıyor veya çalan şarkı yok.")
        vc.resume()
        self.state = PlaybackState.PLAYING

    def skip(self) -> Song:
        """Mevcut şarkıyı atlar ve atlanan şarkıyı döndürür."""
        vc = self.voice_client
        if self.current is None or vc is None:
            raise NothingPlaying()
        skipped = self.current
        self._skip_requested = True
        vc.stop()
        return skipped

    def stop(self) -> None:
        """Kuyruğu temizler, döngüyü kapatır ve çalmayı durdurur."""
        if self.current is None and self.queue.is_empty:
            raise NothingPlaying()
        self.loop_mode = LoopMode.OFF
        self.queue.clear()
        self._forced_next = None
        vc = self.voice_client
        if self.current is not None and vc is not None:
            self._skip_requested = True
            vc.stop()

    async def previous(self) -> Song:
        """Bir önceki şarkıya döner."""
        async with self._lock:
            if not self.queue.history:
                raise MusicError("Geçmişte önceki şarkı yok.")
            prev = self.queue.history.pop()
            self._forced_next = prev
            vc = self.voice_client
            if self.current is not None and vc is not None:
                self.queue.add_front(self.current)
                self._suppress_history = True
                self._skip_requested = True
                vc.stop()
            else:
                await self._advance(strict=True)
            return prev

    def shuffle(self) -> None:
        if len(self.queue) < 2:
            raise EmptyQueue("Karıştırmak için kuyrukta en az 2 şarkı olmalı.")
        self.queue.shuffle()

    def set_volume(self, percent: int) -> None:
        self.volume = percent / 100
        if self._source is not None:
            self._source.volume = self.volume

    def cycle_loop(self) -> LoopMode:
        order = [LoopMode.OFF, LoopMode.SONG, LoopMode.QUEUE]
        self.loop_mode = order[(order.index(self.loop_mode) + 1) % 3]
        return self.loop_mode

    # -------------------------------------------------------------- mesajlaşma
    async def _send(self, **kwargs: object) -> discord.Message | None:
        if self.text_channel is None:
            return None
        try:
            return await self.text_channel.send(**kwargs)  # type: ignore[arg-type]
        except discord.HTTPException as exc:
            log.warning("Mesaj gönderilemedi: %s", exc)
            return None

    async def _send_now_playing(self) -> None:
        await self._clear_controls(delete=True)
        self._view = MusicControls(self)
        self.controls_message = await self._send(embed=now_playing_embed(self), view=self._view)

    async def _clear_controls(self, delete: bool) -> None:
        msg, self.controls_message = self.controls_message, None
        if msg is None:
            return
        try:
            if delete:
                await msg.delete()
            else:
                await msg.edit(embed=now_playing_embed(self), view=None)
        except discord.HTTPException as exc:
            log.debug("Kontrol mesajı temizlenemedi: %s", exc)

    async def refresh_controls(self) -> None:
        """Komutlarla değişen durumu kontrol panelinde günceller."""
        if self.controls_message is None or self._view is None or self.current is None:
            return
        self._view.sync()
        try:
            await self.controls_message.edit(embed=now_playing_embed(self), view=self._view)
        except discord.HTTPException as exc:
            log.debug("Panel güncellenemedi: %s", exc)

    # ------------------------------------------------------------ ayrılma/temizlik
    def schedule_leave(self) -> None:
        """Boşta/boş kanalda zaman aşımı sonrası ayrılmayı planlar."""
        if self._closed or (self._leave_task and not self._leave_task.done()):
            return
        self._leave_task = asyncio.create_task(self._leave_after_timeout())

    def _cancel_leave(self) -> None:
        task, self._leave_task = self._leave_task, None
        if task and not task.done() and task is not asyncio.current_task():
            task.cancel()

    async def _leave_after_timeout(self) -> None:
        try:
            settings = await self.manager.database.get_settings(self.guild.id)
            if not settings.leave_when_empty:
                return
            await asyncio.sleep(settings.leave_timeout)
            if self._closed:
                return
            if self.state is PlaybackState.IDLE or self.channel_is_empty():
                voice_log.info("Zaman aşımı, kanaldan ayrılınıyor (%s)", self.guild.name)
                await self._send(embed=info_embed("👋 Ayrılıyorum", "Uzun süre kullanılmadığı için ses kanalından ayrıldım."))
                await self.manager.players.destroy(self.guild.id)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Ayrılma görevi hatası")

    async def destroy(self, disconnect: bool = True) -> None:
        """Oynatıcıyı kapatır; FFmpeg ve ses bağlantısını temizler."""
        if self._closed:
            return
        self._closed = True
        self._gen += 1
        self._cancel_leave()
        self.queue.clear()
        self.queue.history.clear()
        self.current, self.state, self._forced_next = None, PlaybackState.IDLE, None
        vc = self.voice_client
        if vc is not None:
            if vc.is_playing() or vc.is_paused():
                vc.stop()  # FFmpeg process'i cleanup ile kapatılır
            if disconnect:
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    voice_log.exception("Bağlantı kapatılırken hata")
        await self._clear_controls(delete=False)
        voice_log.info("Oynatıcı temizlendi (%s)", self.guild.name)