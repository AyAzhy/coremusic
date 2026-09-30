"""Renkli console logging sistemi."""
from __future__ import annotations

import logging
import os
import sys

_LEVEL_COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[41m",
}
_TAG_COLOR = "\033[35m"
_RESET = "\033[0m"


class ColorFormatter(logging.Formatter):
    """[SEVİYE] [ETİKET] mesaj biçiminde renkli çıktı üretir."""

    def format(self, record: logging.LogRecord) -> str:
        level = f"{_LEVEL_COLORS.get(record.levelname, '')}[{record.levelname}]{_RESET}"
        tag = f"{_TAG_COLOR}[{record.name.split('.')[-1]}]{_RESET}"
        line = f"{self.formatTime(record, '%H:%M:%S')} {level} {tag} {record.getMessage()}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging(level: str = "INFO") -> None:
    """Logging altyapısını kurar."""
    if os.name == "nt":
        os.system("")  # Windows terminalinde ANSI renklerini etkinleştirir
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())
    for name, lvl in (("bot", getattr(logging, level, logging.INFO)), ("discord", logging.WARNING)):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.setLevel(lvl)
        logger.addHandler(handler)
        logger.propagate = False


def get_logger(tag: str) -> logging.Logger:
    """[INFO], [MUSIC], [VOICE], [QUEUE], [DATABASE] gibi etiketli logger döndürür."""
    return logging.getLogger(f"bot.{tag}")
