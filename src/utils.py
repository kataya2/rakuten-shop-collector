import logging
from pathlib import Path


class RakutenAPIError(Exception):
    """楽天APIの呼び出しに失敗した場合に送出される例外。"""


class ConfigError(Exception):
    """設定値の不足または不正がある場合に送出される例外。"""


def get_logger(name: str) -> logging.Logger:
    """ファイルとコンソールに出力するロガーを返す。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "rakuten_collector.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
