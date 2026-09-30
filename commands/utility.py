"""Yardımcı ve ayar komutları."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import format_duration, info_embed

if TYPE_CHECKING:
    from main import MusicBot


class UtilityCog(commands.Cog, name="Yardımcı"):
    """Ping, yardım, istatistik ve sunucu ayarları."""

    def __init__(self, bot: MusicBot) -> None:
        self.bot = bot

    ayar = app_commands.Group(
        name="ayar",
        description="Sunucu müzik ayarları",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @app_commands.command(name="ping", description="Botun gecikmesini gösterir")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=info_embed("🏓 Pong!", f"Gecikme: **{round(self.bot.latency * 1000)} ms**"))

    @app_commands.command(name="yardim", description="Komut listesini gösterir")
    async def yardim(self, interaction: discord.Interaction) -> None:
        embed = info_embed("🎵 Core Music • Komutlar")
        embed.description = "**Premium Discord müzik botu - Kesintisiz müzik deneyimi!**"
        
        embed.add_field(
            name="🎶 Müzik Komutları",
            value=(
                "`/play` - Şarkı çal\n"
                "`/search` - YouTube'da ara\n"
                "`/pause` - Duraklat\n"
                "`/resume` - Devam et\n"
                "`/nowplaying` - Çalan şarkı\n"
                "`/queue` - Kuyruk"
            ),
            inline=True,
        )
        embed.add_field(
            name="🎧 DJ Komutları",
            value=(
                "`/skip` - Şarkıyı atla\n"
                "`/stop` - Durdur\n"
                "`/clear` - Kuyruğu temizle\n"
                "`/shuffle` - Karıştır\n"
                "`/volume` - Ses seviyesi\n"
                "`/disconnect` - Botu çıkar"
            ),
            inline=True,
        )
        embed.add_field(
            name="⚙️ Ayarlar & Diğer",
            value=(
                "`/loop` - Döngü modu\n"
                "`/remove` - Kuyruktan sil\n"
                "`/ping` - Bot gecikme\n"
                "`/istatistik` - İstatistikler\n"
                "`/ayar` - Sunucu ayarları"
            ),
            inline=True,
        )
        
        embed.set_thumbnail(url="https://i.imgur.com/u3fGZjH.png")  # Core Music logo (isterseniz değiştirin)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="istatistik", description="Bu sunucunun müzik istatistiklerini gösterir")
    @app_commands.guild_only()
    async def istatistik(self, interaction: discord.Interaction) -> None:
        stats = await self.bot.database.get_stats(interaction.guild_id)  # type: ignore[arg-type]
        embed = info_embed("📊 Sunucu İstatistikleri")
        embed.add_field(name="🎶 Çalınan şarkı", value=str(stats.played_songs))
        embed.add_field(name="⏱ Toplam süre", value=format_duration(stats.total_play_time) if stats.total_play_time else "0:00")
        embed.add_field(name="⌨️ Kullanılan komut", value=str(stats.commands_used))
        await interaction.response.send_message(embed=embed)

    @ayar.command(name="goster", description="Mevcut sunucu ayarlarını gösterir")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ayar_goster(self, interaction: discord.Interaction) -> None:
        s = await self.bot.database.get_settings(interaction.guild_id)  # type: ignore[arg-type]
        embed = info_embed("⚙️ Sunucu Ayarları")
        embed.add_field(name="🎧 DJ rolü", value=f"<@&{s.dj_role_id}>" if s.dj_role_id else "Yok (herkes)")
        embed.add_field(name="🔊 Varsayılan ses", value=f"%{s.default_volume}")
        embed.add_field(name="🚪 Otomatik ayrılma", value="Açık" if s.leave_when_empty else "Kapalı")
        embed.add_field(name="⏳ Bekleme süresi", value=f"{s.leave_timeout} sn")
        embed.add_field(name="🌐 Dil / Önek", value=f"{s.language} / {s.prefix}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ayar.command(name="dj", description="DJ rolünü ayarlar (rol vermezsen kaldırır)")
    @app_commands.describe(rol="DJ rolü")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ayar_dj(self, interaction: discord.Interaction, rol: discord.Role | None = None) -> None:
        await self.bot.database.update_setting(interaction.guild_id, "dj_role_id", rol.id if rol else None)  # type: ignore[arg-type]
        text = f"DJ rolü {rol.mention} olarak ayarlandı." if rol else "DJ rolü kaldırıldı, herkes kullanabilir."
        await interaction.response.send_message(embed=info_embed("🎧 DJ rolü", text), ephemeral=True)

    @ayar.command(name="ses", description="Varsayılan ses seviyesini ayarlar")
    @app_commands.describe(seviye="0-100")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ayar_ses(self, interaction: discord.Interaction, seviye: app_commands.Range[int, 0, 100]) -> None:
        await self.bot.database.update_setting(interaction.guild_id, "default_volume", seviye)  # type: ignore[arg-type]
        await interaction.response.send_message(embed=info_embed("🔊 Varsayılan ses", f"%{seviye} olarak ayarlandı."), ephemeral=True)

    @ayar.command(name="bekleme", description="Boşta kalınca ayrılma süresini (saniye) ayarlar")
    @app_commands.describe(saniye="10-3600")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ayar_bekleme(self, interaction: discord.Interaction, saniye: app_commands.Range[int, 10, 3600]) -> None:
        await self.bot.database.update_setting(interaction.guild_id, "leave_timeout", saniye)  # type: ignore[arg-type]
        await interaction.response.send_message(embed=info_embed("⏳ Bekleme süresi", f"{saniye} sn olarak ayarlandı."), ephemeral=True)

    @ayar.command(name="otomatik_ayril", description="Boşta/boş kanalda otomatik ayrılmayı açar veya kapatır")
    @app_commands.describe(durum="Açık mı?")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ayar_ayril(self, interaction: discord.Interaction, durum: bool) -> None:
        await self.bot.database.update_setting(interaction.guild_id, "leave_when_empty", int(durum))  # type: ignore[arg-type]
        await interaction.response.send_message(
            embed=info_embed("🚪 Otomatik ayrılma", "Açık" if durum else "Kapalı"), ephemeral=True
        )


async def setup(bot: MusicBot) -> None:
    await bot.add_cog(UtilityCog(bot))