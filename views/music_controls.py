"""Now Playing kontrol butonları ve arama seçim menüsü."""
from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable, Callable

import discord

from music.queue import LoopMode, PlaybackState
from utils.embeds import clean, format_duration, info_embed, now_playing_embed
from utils.errors import MusicError, NothingPlaying, error_embed, handle_app_command_error

if TYPE_CHECKING:
    from music.player import GuildPlayer
    from music.youtube import SearchResult

LOOP_TEXT = {LoopMode.OFF: "Kapalı", LoopMode.SONG: "Şarkı", LoopMode.QUEUE: "Kuyruk"}


class MusicControls(discord.ui.View):
    """Now Playing embedinin altındaki butonlar."""

    def __init__(self, player: GuildPlayer) -> None:
        super().__init__(timeout=None)
        self.player = player
        self.sync()

    def sync(self) -> None:
        """Buton etiketlerini oynatıcı durumuna göre günceller."""
        paused = self.player.state is PlaybackState.PAUSED
        self.btn_pause.label = "▶️" if paused else "⏸"
        self.btn_loop.label = "🔁"
        self.btn_loop.style = (
            discord.ButtonStyle.secondary if self.player.loop_mode is LoopMode.OFF else discord.ButtonStyle.success
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Yalnızca oynatıcının sunucusunda ve aynı ses kanalındaki kullanıcılar için çalışır."""
        problem: str | None = None
        manager = self.player.manager
        if interaction.guild is None or interaction.guild.id != self.player.guild.id:
            problem = "Bu butonlar yalnızca ait oldukları sunucuda çalışır."
        elif manager.players.get(self.player.guild.id) is not self.player:
            problem = "Bu kontrol paneli artık geçerli değil."
        else:
            try:
                manager.require_player(interaction.user, interaction.guild)
            except MusicError as exc:
                problem = exc.message
        if problem:
            await interaction.response.send_message(embed=error_embed(problem), ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await handle_app_command_error(interaction, error)

    async def _refresh(self, interaction: discord.Interaction) -> None:
        self.sync()
        await interaction.response.edit_message(embed=now_playing_embed(self.player), view=self)

    @discord.ui.button(label="⏮", style=discord.ButtonStyle.secondary, row=0)
    async def btn_previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self.player.previous()

    @discord.ui.button(label="⏸", style=discord.ButtonStyle.primary, row=0)
    async def btn_pause(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.player.state is PlaybackState.PLAYING:
            self.player.pause()
        elif self.player.state is PlaybackState.PAUSED:
            self.player.resume()
        else:
            raise NothingPlaying()
        await self._refresh(interaction)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.secondary, row=0)
    async def btn_skip(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.player.manager.require_dj(interaction.user)
        await interaction.response.defer()
        self.player.skip()

    @discord.ui.button(label="⏹", style=discord.ButtonStyle.danger, row=0)
    async def btn_stop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.player.manager.require_dj(interaction.user)
        await interaction.response.defer()
        self.player.stop()

    @discord.ui.button(label="🔀", style=discord.ButtonStyle.secondary, row=1)
    async def btn_shuffle(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.player.manager.require_dj(interaction.user)
        self.player.shuffle()
        await self._refresh(interaction)

    @discord.ui.button(label="🔁", style=discord.ButtonStyle.secondary, row=1)
    async def btn_loop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.player.cycle_loop()
        await self._refresh(interaction)


class SearchSelectView(discord.ui.View):
    """/search sonuçlarından seçim yapılan menü."""

    def __init__(
        self,
        author_id: int,
        results: list[SearchResult],
        on_select: Callable[[discord.Interaction, str], Awaitable[discord.Embed]],
    ) -> None:
        super().__init__(timeout=60)
        self.author_id = author_id
        self.results = results
        self.on_select = on_select
        select = discord.ui.Select(
            placeholder="Çalmak istediğin şarkıyı seç…",
            options=[
                discord.SelectOption(
                    label=clean(r.title, 100),
                    description=f"{clean(r.uploader, 50)} • {format_duration(r.duration)}"[:100],
                    value=str(i),
                    emoji="🎵",
                )
                for i, r in enumerate(results)
            ],
        )
        select.callback = self._picked  # type: ignore[assignment]
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                embed=error_embed("Bu menüyü yalnızca komutu kullanan kişi kullanabilir."), ephemeral=True
            )
            return False
        return True

    async def _picked(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        index = int(interaction.data["values"][0])  # type: ignore[index]
        self.stop()
        embed = await self.on_select(interaction, self.results[index].webpage_url)
        await interaction.edit_original_response(embed=embed, view=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await handle_app_command_error(interaction, error)

    async def on_timeout(self) -> None:
        self.stop()
