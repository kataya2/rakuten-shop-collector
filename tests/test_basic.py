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
