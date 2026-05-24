from __future__ import annotations

import json
import logging
import sys
import traceback
from typing import Any


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        return f"{color}{super().format(record)}{self.RESET}"


def get_logger(name: str = "jogayjoga.chat") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            ColorFormatter(
                "%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger


logger = get_logger()


def log_event(tag: str, message: str, **data: Any) -> None:
    payload = f" {json.dumps(data, ensure_ascii=False, default=str)}" if data else ""
    logger.info(f"[{tag}] {message}{payload}")


def log_error(tag: str, message: str, exc: Exception | None = None, **data: Any) -> None:
    if exc:
        data["error_type"] = type(exc).__name__
        data["error"] = str(exc)
        data["stacktrace"] = traceback.format_exc()
    payload = f" {json.dumps(data, ensure_ascii=False, default=str)}" if data else ""
    logger.error(f"[{tag}] {message}{payload}")


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"

