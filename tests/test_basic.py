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


from src.shop_extractor import ShopInfo, extract_shops

SAMPLE_ITEMS = [
    {"Item": {
        "shopCode": "shop-a", "shopName": "Shop A",
        "shopUrl": "https://www.rakuten.co.jp/shop-a/",
        "reviewAverage": "4.5", "reviewCount": "100",
        "genreId": "123", "itemPrice": "1000", "itemName": "Item 1",
    }},
    {"Item": {
        "shopCode": "shop-a", "shopName": "Shop A",
        "shopUrl": "https://www.rakuten.co.jp/shop-a/",
        "reviewAverage": "4.0", "reviewCount": "50",
        "genreId": "123", "itemPrice": "800", "itemName": "Item 2",
    }},
    {"Item": {
        "shopCode": "shop-b", "shopName": "Shop B",
        "shopUrl": "https://www.rakuten.co.jp/shop-b/",
        "reviewAverage": "3.5", "reviewCount": "200",
        "genreId": "456", "itemPrice": "2000", "itemName": "Item 3",
    }},
]


def test_extract_shops_returns_unique_shops():
    shops = extract_shops(SAMPLE_ITEMS)
    shop_ids = [s.shop_id for s in shops]
    assert len(shop_ids) == 2
    assert shop_ids.count("shop-a") == 1


def test_extract_shops_item_count():
    shops = extract_shops(SAMPLE_ITEMS)
    shop_a = next(s for s in shops if s.shop_id == "shop-a")
    assert shop_a.item_count == 2


def test_extract_shops_avg_review():
    shops = extract_shops(SAMPLE_ITEMS)
    shop_a = next(s for s in shops if s.shop_id == "shop-a")
    assert shop_a.avg_review == pytest.approx(4.25)


def test_extract_shops_total_reviews():
    shops = extract_shops(SAMPLE_ITEMS)
    shop_a = next(s for s in shops if s.shop_id == "shop-a")
    assert shop_a.total_reviews == 150


def test_extract_shops_min_price():
    shops = extract_shops(SAMPLE_ITEMS)
    shop_a = next(s for s in shops if s.shop_id == "shop-a")
    assert shop_a.min_price == 800


def test_extract_shops_sorted_by_item_count():
    shops = extract_shops(SAMPLE_ITEMS)
    assert shops[0].item_count >= shops[-1].item_count


def test_extract_shops_empty_input():
    assert extract_shops([]) == []
