"""Bot giriş noktası."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from config import Config, load_config
from database.database import Database
from music.manager import MusicManager
from utils.errors import handle_app_command_error
from utils.logger import get_logger, setup_logging

log = get_logger("INFO")
EXTENSIONS = ("commands.music", "commands.utility")


class MusicTree(app_commands.CommandTree):
    """Komutları yalnızca sunucularda çalıştırır ve kullanım istatistiği tutar."""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.CheckFailure("Bu komut yalnızca sunucularda kullanılabilir.")
        try:
            await self.client.database.increment_commands(interaction.guild.id)  # type: ignore[attr-defined]
        except Exception:
            get_logger("DATABASE").exception("Komut sayacı güncellenemedi")
        return True


class MusicBot(commands.Bot):
    """Ana bot sınıfı."""

    def __init__(self, config: Config) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=discord.Intents.default(),  # ayrıcalıklı intent gerekmez
            tree_cls=MusicTree,
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="Core Music 🎵 | /play"
            ),
        )
        self.config = config
        self.database = Database(config.database_path, config)
        self.music = MusicManager(self, self.database, config)

    async def setup_hook(self) -> None:
        """Veritabanını kurar, cog'ları yükler, slash komutlarını sync eder."""
        await self.database.connect()
        self.tree.error(handle_app_command_error)
        for ext in EXTENSIONS:
            await self.load_extension(ext)
            log.info("Yüklendi: %s", ext)
        if self.config.dev_guild_id:
            guild = discord.Object(id=self.config.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
        else:
            synced = await self.tree.sync()
        log.info("%d slash komutu senkronize edildi.", len(synced))

    async def on_ready(self) -> None:
        log.info("Giriş yapıldı: %s (%d sunucu)", self.user, len(self.guilds))

    async def close(self) -> None:
        """Kapanırken ses bağlantılarını ve veritabanını temizler."""
        await self.music.shutdown()
        await self.database.close()
        await super().close()


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)
    bot = MusicBot(config)
    try:
        bot.run(config.token, log_handler=None)
    except discord.LoginFailure:
        log.error("Geçersiz token! .env içindeki DISCORD_TOKEN değerini kontrol et.")


if __name__ == "__main__":
    main()