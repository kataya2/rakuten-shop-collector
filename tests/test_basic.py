import logging
import pytest
from src.utils import RakutenAPIError, ConfigError, get_logger


def test_rakuten_api_error_is_exception():
    err = RakutenAPIError("テストエラー")
    assert isinstance(err, Exception)
    assert str(err) == "テストエラー"


def test_config_error_is_exception():
    err = ConfigError("設定エラー")
    assert isinstance(err, Exception)
    assert str(err) == "設定エラー"


def test_get_logger_returns_logger():
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test"


def test_get_logger_has_handlers():
    logger = get_logger("test_handlers")
    assert len(logger.handlers) > 0


def test_get_logger_is_idempotent():
    logger1 = get_logger("test_idempotent")
    handler_count = len(logger1.handlers)
    logger2 = get_logger("test_idempotent")
    assert logger1 is logger2
    assert len(logger2.handlers) == handler_count
