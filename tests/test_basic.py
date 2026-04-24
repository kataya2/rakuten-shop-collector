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


from unittest.mock import patch, MagicMock
from src.api_client import ApiClient
from src.utils import RakutenAPIError


def _make_api_response(items: list[dict], count: int = 1) -> dict:
    return {"count": count, "Items": [{"Item": i} for i in items]}


MOCK_ITEM = {
    "shopCode": "s1", "shopName": "Shop1",
    "shopUrl": "https://www.rakuten.co.jp/s1/",
    "reviewAverage": "4.0", "reviewCount": "10",
    "genreId": "100", "itemPrice": "500", "itemName": "Item",
}


def test_api_client_sets_referer_header():
    client = ApiClient("app-id", "access-key")
    assert client.session.headers.get("Referer") == "https://github.com"


def test_api_client_search_returns_items():
    client = ApiClient("app-id", "access-key")
    fake_response = _make_api_response([MOCK_ITEM], count=1)
    with patch.object(client.session, "get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = fake_response
        items = client.search(keyword="テスト", category_id=None, count=1)
    assert len(items) == 1
    assert items[0]["Item"]["shopCode"] == "s1"


def test_api_client_raises_on_403():
    client = ApiClient("app-id", "access-key")
    with patch.object(client.session, "get") as mock_get:
        mock_get.return_value.status_code = 403
        mock_get.return_value.text = '{"errors":{"errorCode":403,"errorMessage":"REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING"}}'
        mock_get.return_value.json.return_value = {
            "error": "REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING",
            "error_description": "",
        }
        with pytest.raises(RakutenAPIError, match="Referer"):
            client.search(keyword="テスト", category_id=None, count=1)


def test_api_client_raises_on_wrong_parameter():
    client = ApiClient("app-id", "access-key")
    with patch.object(client.session, "get") as mock_get:
        mock_get.return_value.status_code = 400
        mock_get.return_value.json.return_value = {
            "error": "wrong_parameter",
            "error_description": "specify valid applicationId",
        }
        with pytest.raises(RakutenAPIError, match="applicationId"):
            client.search(keyword="テスト", category_id=None, count=1)


def test_api_client_raises_on_missing_access_key():
    client = ApiClient("app-id", "access-key")
    with patch.object(client.session, "get") as mock_get:
        mock_get.return_value.status_code = 400
        mock_get.return_value.json.return_value = {
            "error": "wrong_parameter",
            "error_description": "accessKey must be present",
        }
        with pytest.raises(RakutenAPIError, match="accessKey"):
            client.search(keyword="テスト", category_id=None, count=1)


import csv
from pathlib import Path
from src.output_writer import write_csv, write_excel
from src.shop_extractor import ShopInfo

SAMPLE_SHOPS = [
    ShopInfo("s1", "Shop One", "https://www.rakuten.co.jp/s1/", 5, 4.2, 120, 980, "100"),
    ShopInfo("s2", "Shop Two", "https://www.rakuten.co.jp/s2/", 2, 3.8, 40, 1500, "200"),
]


def test_write_csv_creates_file(tmp_path):
    filepath = str(tmp_path / "output.csv")
    write_csv(SAMPLE_SHOPS, filepath)
    assert Path(filepath).exists()


def test_write_csv_contains_correct_data(tmp_path):
    filepath = str(tmp_path / "output.csv")
    write_csv(SAMPLE_SHOPS, filepath)
    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["shop_id"] == "s1"
    assert rows[0]["shop_name"] == "Shop One"
    assert rows[0]["item_count"] == "5"


def test_write_excel_creates_file(tmp_path):
    filepath = str(tmp_path / "output.xlsx")
    write_excel(SAMPLE_SHOPS, filepath)
    assert Path(filepath).exists()


def test_write_excel_correct_row_count(tmp_path):
    import openpyxl
    filepath = str(tmp_path / "output.xlsx")
    write_excel(SAMPLE_SHOPS, filepath)
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    assert ws.max_row == 3  # 1行目ヘッダー + 2行データ


from unittest.mock import patch


def test_main_rejects_both_keyword_and_category(monkeypatch, capsys):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-key")
    with patch("sys.argv", ["main.py", "--keyword", "テスト", "--category-id", "100"]):
        with pytest.raises(SystemExit) as exc:
            import main as main_module
            main_module.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "--keyword と --category-id は同時に指定できません" in captured.err


def test_main_requires_keyword_or_category(monkeypatch, capsys):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-key")
    with patch("sys.argv", ["main.py"]):
        with pytest.raises(SystemExit) as exc:
            import main as main_module
            main_module.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "--keyword または --category-id" in captured.err


def test_main_requires_app_id(monkeypatch, capsys):
    monkeypatch.delenv("RAKUTEN_APP_ID", raising=False)
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-key")
    with patch("sys.argv", ["main.py", "--keyword", "テスト"]):
        with pytest.raises(SystemExit) as exc:
            import main as main_module
            main_module.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "RAKUTEN_APP_ID" in captured.err


from app_gui import _check_credentials


def test_check_credentials_missing_app_id(monkeypatch):
    monkeypatch.delenv("RAKUTEN_APP_ID", raising=False)
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "key")
    app_id, access_key, error = _check_credentials()
    assert app_id == ""
    assert "RAKUTEN_APP_ID" in error


def test_check_credentials_missing_access_key(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-id")
    monkeypatch.delenv("RAKUTEN_ACCESS_KEY", raising=False)
    app_id, access_key, error = _check_credentials()
    assert access_key == ""
    assert "RAKUTEN_ACCESS_KEY" in error


def test_check_credentials_both_set(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-key")
    app_id, access_key, error = _check_credentials()
    assert app_id == "test-id"
    assert access_key == "test-key"
    assert error == ""


from app_gui import _settings_path, _load_settings, _save_settings


def test_settings_path_returns_path_instance():
    assert isinstance(_settings_path(), Path)


def test_settings_path_ends_with_config_settings_json():
    p = _settings_path()
    assert p.parts[-2] == "config"
    assert p.name == "settings.json"


def test_load_settings_returns_none_when_missing(tmp_path):
    assert _load_settings(tmp_path / "missing.json") is None


def test_load_settings_returns_none_on_invalid_json(tmp_path):
    bad = tmp_path / "settings.json"
    bad.write_text("not json", encoding="utf-8")
    assert _load_settings(bad) is None


def test_save_and_load_settings_roundtrip(tmp_path):
    path = tmp_path / "config" / "settings.json"
    data = {
        "rakuten_app_id": "test-id",
        "rakuten_access_key": "test-key",
        "rakuten_referer": "https://github.com/",
    }
    assert _save_settings(data, path) is True
    assert _load_settings(path) == data


def test_save_settings_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "settings.json"
    assert _save_settings({"rakuten_app_id": "x", "rakuten_access_key": "y"}, path) is True
    assert path.exists()


def test_load_settings_returns_none_when_not_dict(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert _load_settings(path) is None


from app_gui import _load_credentials


def test_load_credentials_from_settings(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(
        '{"rakuten_app_id": "s-id", "rakuten_access_key": "s-key", "rakuten_referer": "https://github.com/"}',
        encoding="utf-8",
    )
    monkeypatch.setattr("app_gui._settings_path", lambda: path)
    monkeypatch.delenv("RAKUTEN_APP_ID", raising=False)
    monkeypatch.delenv("RAKUTEN_ACCESS_KEY", raising=False)
    app_id, access_key, referer, error = _load_credentials()
    assert app_id == "s-id"
    assert access_key == "s-key"
    assert referer == "https://github.com/"
    assert error == ""


def test_load_credentials_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setattr("app_gui._settings_path", lambda: tmp_path / "missing.json")
    monkeypatch.setenv("RAKUTEN_APP_ID", "env-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "env-key")
    app_id, access_key, referer, error = _load_credentials()
    assert app_id == "env-id"
    assert access_key == "env-key"
    assert error == ""


def test_load_credentials_settings_takes_priority_over_env(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(
        '{"rakuten_app_id": "s-id", "rakuten_access_key": "s-key", "rakuten_referer": "https://github.com/"}',
        encoding="utf-8",
    )
    monkeypatch.setattr("app_gui._settings_path", lambda: path)
    monkeypatch.setenv("RAKUTEN_APP_ID", "env-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "env-key")
    app_id, access_key, referer, error = _load_credentials()
    assert app_id == "s-id"


def test_load_credentials_returns_error_when_none(tmp_path, monkeypatch):
    monkeypatch.setattr("app_gui._settings_path", lambda: tmp_path / "missing.json")
    monkeypatch.delenv("RAKUTEN_APP_ID", raising=False)
    monkeypatch.delenv("RAKUTEN_ACCESS_KEY", raising=False)
    app_id, access_key, referer, error = _load_credentials()
    assert error != ""
    assert app_id == ""
