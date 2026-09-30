"""MusicManager ve PlayerManager."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from config import Config
from database.database import Database
from music.ffmpeg import FFmpegPlayer
from music.player import GuildPlayer
from music.youtube import YouTubeService
from utils.errors import (
    DifferentVoiceChannel,
    MissingBotPermissions,
    MissingDJRole,
    MusicError,
    NotInVoiceChannel,
)
from utils.logger import get_logger

if TYPE_CHECKING:
    from main import MusicBot

log = get_logger("MUSIC")

VoiceLike = discord.VoiceChannel | discord.StageChannel


class PlayerManager:
    """Sunucu ID'sine göre GuildPlayer kayıt defteri."""

    def __init__(self, manager: MusicManager) -> None:
        self._manager = manager
        self._players: dict[int, GuildPlayer] = {}

    def get(self, guild_id: int) -> GuildPlayer | None:
        return self._players.get(guild_id)

    async def get_or_create(self, guild: discord.Guild, text_channel: discord.abc.Messageable | None) -> GuildPlayer:
        player = self._players.get(guild.id)
        if player is None:
            settings = await self._manager.database.get_settings(guild.id)
            player = self._players.get(guild.id)  # await sırasında oluşmuş olabilir
            if player is None:
                player = GuildPlayer(self._manager, guild, text_channel, settings.default_volume / 100)
                self._players[guild.id] = player
                log.info("Oynatıcı oluşturuldu: %s", guild.name)
        player.text_channel = text_channel
        return player

    async def destroy(self, guild_id: int, disconnect: bool = True) -> None:
        player = self._players.pop(guild_id, None)
        if player is not None:
            await player.destroy(disconnect=disconnect)

    async def destroy_all(self) -> None:
        for guild_id in list(self._players):
            await self.destroy(guild_id)


class MusicManager:
    """Servisleri (YouTube, FFmpeg, DB) ve oynatıcıları bir arada tutar."""

    def __init__(self, bot: MusicBot, database: Database, config: Config) -> None:
        self.bot = bot
        self.database = database
        self.config = config
        self.youtube = YouTubeService()
        self.ffmpeg = FFmpegPlayer(config.ffmpeg_path)
        self.players = PlayerManager(self)

    async def shutdown(self) -> None:
        await self.players.destroy_all()

    # ---------------------------------------------------------------- kontroller
    @staticmethod
    def get_user_channel(member: discord.abc.User) -> VoiceLike:
        """Kullanıcının ses kanalını döndürür, yoksa hata fırlatır."""
        if not isinstance(member, discord.Member) or member.voice is None or member.voice.channel is None:
            raise NotInVoiceChannel()
        return member.voice.channel

    def require_player(self, member: discord.abc.User, guild: discord.Guild, same_channel: bool = True) -> GuildPlayer:
        """Aktif oynatıcıyı döndürür; kullanıcı aynı kanalda değilse hata fırlatır."""
        player = self.players.get(guild.id)
        if player is None or player.voice_client is None:
            raise MusicError("Bot şu anda bir ses kanalında değil. Önce `/play` ile müzik başlat.")
        if same_channel and self.get_user_channel(member).id != player.voice_client.channel.id:
            raise DifferentVoiceChannel()
        return player

    async def is_dj(self, member: discord.Member) -> bool:
        perms = member.guild_permissions
        if perms.administrator or perms.manage_guild:
            return True
        settings = await self.database.get_settings(member.guild.id)
        if settings.dj_role_id is None:
            return True
        return any(role.id == settings.dj_role_id for role in member.roles)

    async def require_dj(self, member: discord.abc.User) -> None:
        if not isinstance(member, discord.Member) or not await self.is_dj(member):
            raise MissingDJRole()

    @staticmethod
    def check_bot_permissions(guild: discord.Guild, voice: VoiceLike, text: object | None) -> None:
        """Botun ses ve metin kanalı izinlerini doğrular."""
        missing: list[str] = []
        perms = voice.permissions_for(guild.me)
        for attr, label in (("view_channel", "Kanalı Görüntüle"), ("connect", "Bağlan"), ("speak", "Konuş")):
            if not getattr(perms, attr):
                missing.append(f"{label} (ses kanalı)")
        permissions_for = getattr(text, "permissions_for", None)
        if permissions_for is not None:
            tperms = permissions_for(guild.me)
            for attr, label in (("send_messages", "Mesaj Gönder"), ("embed_links", "Bağlantı Yerleştir")):
                if not getattr(tperms, attr):
                    missing.append(f"{label} (metin kanalı)")
        if missing:
            raise MissingBotPermissions("Botun şu izinlere ihtiyacı var: " + ", ".join(missing))