"""Müzik slash komutları."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from music.queue import LoopMode
from utils.embeds import LOOP_LABELS, added_embed, clean, format_duration, info_embed, now_playing_embed, queue_embed
from utils.errors import DifferentVoiceChannel, NothingPlaying
from utils.logger import get_logger
from views.music_controls import MusicControls, SearchSelectView

if TYPE_CHECKING:
    from main import MusicBot

log = get_logger("MUSIC")


class MusicCog(commands.Cog, name="Müzik"):
    """Müzik komutları."""

    def __init__(self, bot: MusicBot) -> None:
        self.bot = bot
        self.manager = bot.music

    # --------------------------------------------------------------- yardımcılar
    async def _enqueue(self, interaction: discord.Interaction, query: str) -> discord.Embed:
        """Ortak ekleme akışı: kontroller → çözümleme → bağlanma → kuyruğa ekleme."""
        guild = interaction.guild
        assert guild is not None
        channel = self.manager.get_user_channel(interaction.user)
        self.manager.check_bot_permissions(guild, channel, interaction.channel)
        vc = guild.voice_client
        if isinstance(vc, discord.VoiceClient) and vc.is_connected() and vc.channel.id != channel.id:
            if any(not m.bot for m in vc.channel.members):
                raise DifferentVoiceChannel()
        song = await self.manager.youtube.resolve(query, interaction.user)
        player = await self.manager.players.get_or_create(guild, interaction.channel)
        try:
            await player.connect(channel)
        except Exception:
            if player.voice_client is None:
                await self.manager.players.destroy(guild.id)
            raise
        position, started = await player.add(song)
        return added_embed(song, position, started)

    # ------------------------------------------------------------------ komutlar
    @app_commands.command(name="play", description="Şarkı adı veya YouTube URL'si ile müzik çalar")
    @app_commands.describe(sorgu="Şarkı adı veya bağlantı")
    async def play(self, interaction: discord.Interaction, sorgu: str) -> None:
        await interaction.response.defer()
        await interaction.followup.send(embed=await self._enqueue(interaction, sorgu))

    @app_commands.command(name="search", description="YouTube'da arar ve sonuçlardan seçmeni sağlar")
    @app_commands.describe(sorgu="Aranacak şarkı adı")
    async def search(self, interaction: discord.Interaction, sorgu: str) -> None:
        self.manager.get_user_channel(interaction.user)
        await interaction.response.defer()
        results = await self.manager.youtube.search(sorgu, 5)
        embed = info_embed(
            f"🔍 Sonuçlar: {clean(sorgu, 50)}",
            "\n".join(
                f"`{i}.` [{clean(r.title, 60)}]({r.webpage_url}) • {format_duration(r.duration)}"
                for i, r in enumerate(results, 1)
            ),
        )
        view = SearchSelectView(interaction.user.id, results, self._search_pick)
        await interaction.followup.send(embed=embed, view=view)

    async def _search_pick(self, interaction: discord.Interaction, url: str) -> discord.Embed:
        return await self._enqueue(interaction, url)

    @app_commands.command(name="pause", description="Çalan şarkıyı duraklatır")
    async def pause(self, interaction: discord.Interaction) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild)
        player.pause()
        await interaction.response.send_message(embed=info_embed("⏸ Duraklatıldı"))
        await player.refresh_controls()

    @app_commands.command(name="resume", description="Duraklatılan şarkıyı devam ettirir")
    async def resume(self, interaction: discord.Interaction) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild)
        player.resume()
        await interaction.response.send_message(embed=info_embed("▶️ Devam ediyor"))
        await player.refresh_controls()

    @app_commands.command(name="skip", description="Çalan şarkıyı atlar (DJ)")
    async def skip(self, interaction: discord.Interaction) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild)
        await self.manager.require_dj(interaction.user)
        song = player.skip()
        await interaction.response.send_message(embed=info_embed("⏭ Atlandı", f"**{clean(song.title, 80)}**"))

    @app_commands.command(name="stop", description="Müziği durdurur ve kuyruğu temizler (DJ)")
    async def stop(self, interaction: discord.Interaction) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild)
        await self.manager.require_dj(interaction.user)
        player.stop()
        await interaction.response.send_message(embed=info_embed("⏹ Durduruldu", "Kuyruk temizlendi."))

    @app_commands.command(name="queue", description="Şarkı kuyruğunu gösterir")
    @app_commands.describe(sayfa="Sayfa numarası")
    async def queue(self, interaction: discord.Interaction, sayfa: app_commands.Range[int, 1, 1000] = 1) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild, same_channel=False)
        if player.current is None and player.queue.is_empty:
            raise NothingPlaying("Kuyruk boş ve çalan şarkı yok.")
        await interaction.response.send_message(embed=queue_embed(player, sayfa))

    @app_commands.command(name="nowplaying", description="Şu an çalan şarkıyı gösterir")
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild, same_channel=False)
        if player.current is None:
            raise NothingPlaying()
        await interaction.response.send_message(embed=now_playing_embed(player), view=MusicControls(player))

    @app_commands.command(name="remove", description="Kuyruktan sıra numarasına göre şarkı kaldırır (DJ)")
    @app_commands.describe(sira="Kaldırılacak şarkının sırası")
    async def remove(self, interaction: discord.Interaction, sira: app_commands.Range[int, 1, 1000]) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild)
        await self.manager.require_dj(interaction.user)
        song = player.queue.remove(sira)
        await interaction.response.send_message(embed=info_embed("🗑 Kaldırıldı", f"**{clean(song.title, 80)}**"))

    @app_commands.command(name="clear", description="Kuyruğu temizler (DJ)")
    async def clear(self, interaction: discord.Interaction) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild)
        await self.manager.require_dj(interaction.user)
        count = player.queue.clear()
        await interaction.response.send_message(embed=info_embed("🧹 Kuyruk temizlendi", f"{count} şarkı silindi."))

    @app_commands.command(name="shuffle", description="Kuyruğu karıştırır (DJ)")
    async def shuffle(self, interaction: discord.Interaction) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild)
        await self.manager.require_dj(interaction.user)
        player.shuffle()
        await interaction.response.send_message(embed=info_embed("🔀 Kuyruk karıştırıldı"))

    @app_commands.command(name="loop", description="Döngü modunu ayarlar (kapalı / şarkı / kuyruk)")
    @app_commands.describe(mod="Döngü modu")
    @app_commands.choices(
        mod=[
            app_commands.Choice(name="Kapalı", value="off"),
            app_commands.Choice(name="Şarkı", value="song"),
            app_commands.Choice(name="Kuyruk", value="queue"),
        ]
    )
    async def loop(self, interaction: discord.Interaction, mod: app_commands.Choice[str]) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild)
        player.loop_mode = LoopMode(mod.value)
        await interaction.response.send_message(embed=info_embed("🔁 Döngü modu", f"Yeni mod: **{LOOP_LABELS[player.loop_mode]}**"))
        await player.refresh_controls()

    @app_commands.command(name="volume", description="Ses seviyesini ayarlar (0-100) (DJ)")
    @app_commands.describe(seviye="0 ile 100 arasında ses seviyesi")
    async def volume(self, interaction: discord.Interaction, seviye: app_commands.Range[int, 0, 100]) -> None:
        player = self.manager.require_player(interaction.user, interaction.guild)
        await self.manager.require_dj(interaction.user)
        player.set_volume(seviye)
        await interaction.response.send_message(embed=info_embed("🔊 Ses seviyesi", f"**%{seviye}** olarak ayarlandı."))
        await player.refresh_controls()

    @app_commands.command(name="disconnect", description="Botu ses kanalından çıkarır (DJ)")
    async def disconnect(self, interaction: discord.Interaction) -> None:
        self.manager.require_player(interaction.user, interaction.guild)
        await self.manager.require_dj(interaction.user)
        await self.manager.players.destroy(interaction.guild.id)  # type: ignore[union-attr]
        await interaction.response.send_message(embed=info_embed("👋 Görüşürüz", "Ses kanalından ayrıldım."))

    # ------------------------------------------------------------------ dinleyici
    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        """Bot atılırsa temizlik yapar; kanal boşalırsa ayrılmayı planlar."""
        guild = member.guild
        player = self.manager.players.get(guild.id)
        if player is None:
            return
        if member.id == self.bot.user.id:  # type: ignore[union-attr]
            if after.channel is None:
                log.info("Bot ses kanalından ayrıldı/atıldı: %s", guild.name)
                await self.manager.players.destroy(guild.id, disconnect=False)
            return
        if player.channel_is_empty():
            player.schedule_leave()


async def setup(bot: MusicBot) -> None:
    await bot.add_cog(MusicCog(bot))
