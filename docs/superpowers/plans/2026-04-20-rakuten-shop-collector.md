# Rakuten Shop Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 楽天市場新API（openapi.rakuten.co.jp）を使ってショップ情報を収集し、CSV/Excel/Google Sheetsに出力するCLIツールを実装する。

**Architecture:** ApiClientクラスがHTTP通信・ページネーション・リトライを担い、shop_extractorが生データをShopInfo dataclassに変換・集約し、output_writerが3形式に書き出す。main.pyがCLI引数とconfig.yamlを統合してオーケストレートする。

**Tech Stack:** Python 3.10+, requests, openpyxl, gspread, google-auth, pyyaml, python-dotenv, pytest

---

## ファイル構成

| ファイル | 役割 |
|---------|------|
| `requirements.txt` | 依存パッケージ一覧 |
| `.env.example` | 環境変数テンプレート |
| `config.yaml.example` | 設定ファイルテンプレート |
| `src/__init__.py` | パッケージ宣言 |
| `src/utils.py` | カスタム例外・ロガー生成 |
| `src/api_client.py` | 楽天API通信（ApiClientクラス） |
| `src/shop_extractor.py` | ShopInfo dataclass・集約ロジック |
| `src/output_writer.py` | CSV/Excel/Sheets書き出し |
| `main.py` | CLIエントリーポイント |
| `tests/__init__.py` | テストパッケージ宣言 |
| `tests/test_basic.py` | ユニットテスト（全モジュール） |

---

### Task 1: プロジェクトスキャフォールド

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `config.yaml.example`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `output/.gitkeep`
- Create: `logs/.gitkeep`

- [ ] **Step 1: requirements.txt を作成**

```
requests>=2.31.0
openpyxl>=3.1.0
gspread>=6.0.0
google-auth>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 2: .env.example を作成**

```dotenv
RAKUTEN_APP_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
RAKUTEN_ACCESS_KEY=your_access_key_here
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/credentials.json
```

- [ ] **Step 3: config.yaml.example を作成**

```yaml
search:
  keyword: "ワイヤレスイヤホン"
  category_id: null
  count: 200

output:
  format: excel
  filename: shops_result
  sheet_id: null

api:
  wait_seconds: 1.1
  max_retries: 3

logging:
  level: INFO
  file: logs/rakuten_collector.log
```

- [ ] **Step 4: ディレクトリと空ファイルを作成**

```bash
mkdir -p src tests output logs
touch src/__init__.py tests/__init__.py output/.gitkeep logs/.gitkeep
```

- [ ] **Step 5: 依存パッケージをインストール**

```bash
pip install -r requirements.txt
```

Expected: 全パッケージが正常インストールされる（エラーなし）

- [ ] **Step 6: コミット**

```bash
git add requirements.txt .env.example config.yaml.example src/__init__.py tests/__init__.py output/.gitkeep logs/.gitkeep
git commit -m "chore: scaffold project structure"
```

---

### Task 2: src/utils.py（カスタム例外・ロガー）

**Files:**
- Create: `src/utils.py`
- Create: `tests/test_basic.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_basic.py` を新規作成:

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_basic.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.utils'`

- [ ] **Step 3: src/utils.py を実装**

```python
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
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_basic.py -v
```

Expected: `3 passed`

- [ ] **Step 5: コミット**

```bash
git add src/utils.py tests/test_basic.py
git commit -m "feat: add utils module with custom exceptions and logger"
```

---

### Task 3: src/shop_extractor.py（ShopInfo dataclass・集約）

**Files:**
- Create: `src/shop_extractor.py`
- Modify: `tests/test_basic.py`

- [ ] **Step 1: 失敗するテストを追記**

`tests/test_basic.py` の末尾に追加:

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_basic.py -v -k "extract_shops"
```

Expected: `ImportError: cannot import name 'ShopInfo' from 'src.shop_extractor'`

- [ ] **Step 3: src/shop_extractor.py を実装**

```python
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class ShopInfo:
    shop_id: str
    shop_name: str
    shop_url: str
    item_count: int
    avg_review: float
    total_reviews: int
    min_price: int
    genre_id: str


def extract_shops(items: list[dict]) -> list[ShopInfo]:
    """APIレスポンスのアイテムリストをショップ単位に集約し、item_count降順で返す。"""
    groups: dict[str, list[dict]] = defaultdict(list)
    for entry in items:
        item = entry["Item"]
        groups[item["shopCode"]].append(item)

    shops: list[ShopInfo] = []
    for shop_id, item_list in groups.items():
        first = item_list[0]
        reviews = [float(i.get("reviewAverage") or 0) for i in item_list]
        review_counts = [int(i.get("reviewCount") or 0) for i in item_list]
        prices = [int(i.get("itemPrice") or 0) for i in item_list]

        shops.append(ShopInfo(
            shop_id=shop_id,
            shop_name=first["shopName"],
            shop_url=first["shopUrl"],
            item_count=len(item_list),
            avg_review=round(sum(reviews) / len(reviews), 2),
            total_reviews=sum(review_counts),
            min_price=min(prices),
            genre_id=str(first.get("genreId", "")),
        ))

    return sorted(shops, key=lambda s: s.item_count, reverse=True)
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_basic.py -v -k "extract_shops"
```

Expected: `7 passed`

- [ ] **Step 5: コミット**

```bash
git add src/shop_extractor.py tests/test_basic.py
git commit -m "feat: add ShopInfo dataclass and extract_shops aggregation"
```

---

### Task 4: src/api_client.py（楽天API通信）

**Files:**
- Create: `src/api_client.py`
- Modify: `tests/test_basic.py`

- [ ] **Step 1: 失敗するテストを追記**

`tests/test_basic.py` の末尾に追加:

```python
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
    assert client.session.headers.get("Referer") == "https://github.com/"


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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_basic.py -v -k "api_client"
```

Expected: `ImportError: cannot import name 'ApiClient' from 'src.api_client'`

- [ ] **Step 3: src/api_client.py を実装**

```python
from __future__ import annotations
import time
import requests
from src.utils import RakutenAPIError, get_logger

logger = get_logger(__name__)

API_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"


class ApiClient:
    """楽天市場新API（openapi.rakuten.co.jp）のラッパークラス。"""

    def __init__(
        self,
        app_id: str,
        access_key: str,
        wait_seconds: float = 1.1,
        max_retries: int = 3,
    ) -> None:
        self.app_id = app_id
        self.access_key = access_key
        self.wait_seconds = wait_seconds
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"Referer": "https://github.com/"})

    def search(
        self,
        keyword: str | None,
        category_id: str | None,
        count: int,
    ) -> list[dict]:
        """指定条件で新APIを検索し、アイテムのリストを返す。"""
        items: list[dict] = []
        page = 1

        while len(items) < count and page <= 100:
            hits = min(count - len(items), 30)
            params: dict = {
                "applicationId": self.app_id,
                "accessKey": self.access_key,
                "format": "json",
                "hits": hits,
                "page": page,
            }
            if keyword:
                params["keyword"] = keyword
            if category_id:
                params["genreId"] = category_id

            raw = self._get_with_retry(params)
            fetched = raw.get("Items", [])
            if not fetched:
                break
            items.extend(fetched)
            page += 1
            if len(items) < count and page <= 100:
                time.sleep(self.wait_seconds)

        return items[:count]

    def _get_with_retry(self, params: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(API_ENDPOINT, params=params, timeout=10)
                return self._handle_response(resp)
            except RakutenAPIError:
                raise
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning("接続エラー（試行 %d/%d）: %s", attempt + 1, self.max_retries, e)
                time.sleep(2 ** attempt)
        raise RakutenAPIError(f"APIへの接続に失敗しました: {last_error}")

    def _handle_response(self, resp: requests.Response) -> dict:
        if resp.status_code == 403:
            raise RakutenAPIError(
                "Refererヘッダーが不正です。"
                "楽天デベロッパーコンソールの「許可されたWebサイト」を確認してください。"
            )
        if resp.status_code == 401:
            raise RakutenAPIError(
                "認証に失敗しました。"
                "RAKUTEN_APP_ID と RAKUTEN_ACCESS_KEY を両方確認してください。"
            )

        body = resp.json()
        error = body.get("error", "")
        desc = body.get("error_description", "")

        if "accessKey must be present" in desc:
            raise RakutenAPIError(
                "accessKeyが設定されていません。"
                ".env の RAKUTEN_ACCESS_KEY を確認してください。"
            )
        if "wrong_parameter" in error or "specify valid applicationId" in desc:
            raise RakutenAPIError(
                "applicationIdが無効です。"
                ".env の RAKUTEN_APP_ID と楽天デベロッパーコンソールを確認してください。"
            )
        if error:
            raise RakutenAPIError(f"APIエラー: {error} / {desc}")

        return body
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_basic.py -v -k "api_client"
```

Expected: `5 passed`

- [ ] **Step 5: コミット**

```bash
git add src/api_client.py tests/test_basic.py
git commit -m "feat: add ApiClient with pagination, retry, and error handling"
```

---

### Task 5: src/output_writer.py（CSV・Excel・Google Sheets出力）

**Files:**
- Create: `src/output_writer.py`
- Modify: `tests/test_basic.py`

- [ ] **Step 1: 失敗するテストを追記**

`tests/test_basic.py` の末尾に追加:

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_basic.py -v -k "write_csv or write_excel"
```

Expected: `ImportError: cannot import name 'write_csv' from 'src.output_writer'`

- [ ] **Step 3: src/output_writer.py を実装**

```python
from __future__ import annotations
import csv
from pathlib import Path
from typing import TYPE_CHECKING

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from src.utils import get_logger

if TYPE_CHECKING:
    from src.shop_extractor import ShopInfo

logger = get_logger(__name__)

HEADERS = [
    "shop_id", "shop_name", "shop_url", "item_count",
    "avg_review", "total_reviews", "min_price", "genre_id",
]


def write_csv(shops: list[ShopInfo], filepath: str) -> None:
    """ショップリストをUTF-8 BOM付きCSVに書き出す（Excel対応）。"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for s in shops:
            writer.writerow({
                "shop_id": s.shop_id,
                "shop_name": s.shop_name,
                "shop_url": s.shop_url,
                "item_count": s.item_count,
                "avg_review": s.avg_review,
                "total_reviews": s.total_reviews,
                "min_price": s.min_price,
                "genre_id": s.genre_id,
            })
    logger.info("CSV出力完了: %s", filepath)


def write_excel(shops: list[ShopInfo], filepath: str) -> None:
    """ショップリストを書式付きExcelファイルに書き出す。"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "shops"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(fill_type="solid", fgColor="4472C4")
    header_align = Alignment(horizontal="center")

    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    for s in shops:
        ws.append([
            s.shop_id, s.shop_name, s.shop_url, s.item_count,
            s.avg_review, s.total_reviews, s.min_price, s.genre_id,
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    wb.save(filepath)
    logger.info("Excel出力完了: %s", filepath)


def write_gsheet(shops: list[ShopInfo], sheet_id: str, credentials_path: str) -> None:
    """ショップリストをGoogle Spreadsheetsの'shops'シートに上書き出力する。"""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(sheet_id)

    try:
        ws = spreadsheet.worksheet("shops")
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title="shops", rows=1000, cols=len(HEADERS))

    ws.clear()
    rows = [HEADERS] + [
        [s.shop_id, s.shop_name, s.shop_url, s.item_count,
         s.avg_review, s.total_reviews, s.min_price, s.genre_id]
        for s in shops
    ]
    ws.update(rows)
    logger.info("Googleスプレッドシート出力完了: %s", sheet_id)
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_basic.py -v -k "write_csv or write_excel"
```

Expected: `4 passed`

- [ ] **Step 5: コミット**

```bash
git add src/output_writer.py tests/test_basic.py
git commit -m "feat: add output_writer for CSV, Excel, and Google Sheets"
```

---

### Task 6: main.py（CLIエントリーポイント）

**Files:**
- Create: `main.py`
- Modify: `tests/test_basic.py`

- [ ] **Step 1: 失敗するテストを追記**

`tests/test_basic.py` の末尾に追加:

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_basic.py -v -k "test_main"
```

Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: main.py を実装**

```python
"""楽天ショップコレクター — エントリーポイント。"""
from __future__ import annotations
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.api_client import ApiClient
from src.output_writer import write_csv, write_excel, write_gsheet
from src.shop_extractor import extract_shops
from src.utils import ConfigError, RakutenAPIError, get_logger

load_dotenv()
logger = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="楽天市場からショップ情報を収集します")
    parser.add_argument("--keyword", help="検索キーワード")
    parser.add_argument("--category-id", help="楽天カテゴリID（genreId）")
    parser.add_argument("--count", type=int, default=100, help="取得する商品数（デフォルト: 100）")
    parser.add_argument("--output", choices=["csv", "excel", "gsheet"], default="csv")
    parser.add_argument("--filename", default="shops_result", help="出力ファイル名（拡張子不要）")
    parser.add_argument("--sheet-id", help="GoogleスプレッドシートID（gsheet使用時）")
    parser.add_argument("--config", help="設定ファイルのパス（config.yaml）")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def _load_config(path: str | None) -> dict:
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _output_path(filename: str, fmt: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = "csv" if fmt == "csv" else "xlsx"
    Path("output").mkdir(exist_ok=True)
    return str(Path("output") / f"{filename}_{timestamp}.{ext}")


def main() -> None:
    args = _parse_args()
    cfg = _load_config(args.config)

    keyword = args.keyword or cfg.get("search", {}).get("keyword")
    category_id = args.category_id or cfg.get("search", {}).get("category_id")
    count = args.count or cfg.get("search", {}).get("count", 100)
    fmt = args.output or cfg.get("output", {}).get("format", "csv")
    filename = args.filename or cfg.get("output", {}).get("filename", "shops_result")
    sheet_id = args.sheet_id or cfg.get("output", {}).get("sheet_id")

    if keyword and category_id:
        print("エラー: --keyword と --category-id は同時に指定できません。", file=sys.stderr)
        sys.exit(1)
    if not keyword and not category_id:
        print("エラー: --keyword または --category-id のいずれかを指定してください。", file=sys.stderr)
        sys.exit(1)

    app_id = os.environ.get("RAKUTEN_APP_ID", "")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "")
    if not app_id:
        print("エラー: RAKUTEN_APP_ID が設定されていません。.env を確認してください。", file=sys.stderr)
        sys.exit(1)
    if not access_key:
        print("エラー: RAKUTEN_ACCESS_KEY が設定されていません。.env を確認してください。", file=sys.stderr)
        sys.exit(1)

    wait_seconds = float(cfg.get("api", {}).get("wait_seconds", 1.1))
    max_retries = int(cfg.get("api", {}).get("max_retries", 3))

    try:
        client = ApiClient(app_id, access_key, wait_seconds=wait_seconds, max_retries=max_retries)
        logger.info("検索開始: keyword=%s, category_id=%s, count=%d", keyword, category_id, count)
        items = client.search(keyword=keyword, category_id=category_id, count=count)
        logger.info("取得アイテム数: %d", len(items))

        shops = extract_shops(items)
        logger.info("ユニークショップ数: %d", len(shops))

        if fmt == "csv":
            path = _output_path(filename, "csv")
            write_csv(shops, path)
            print(f"出力完了: {path}")
        elif fmt == "excel":
            path = _output_path(filename, "excel")
            write_excel(shops, path)
            print(f"出力完了: {path}")
        elif fmt == "gsheet":
            if not sheet_id:
                print("エラー: --sheet-id を指定してください。", file=sys.stderr)
                sys.exit(1)
            credentials_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
            if not credentials_path:
                print(
                    "エラー: GOOGLE_SERVICE_ACCOUNT_JSON が設定されていません。",
                    file=sys.stderr,
                )
                sys.exit(1)
            write_gsheet(shops, sheet_id, credentials_path)
            print("Googleスプレッドシートへの出力完了")

    except (RakutenAPIError, ConfigError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_basic.py -v -k "test_main"
```

Expected: `3 passed`

- [ ] **Step 5: 全テストが通ることを確認**

```bash
pytest tests/test_basic.py -v
```

Expected: 全テストが passed（22テスト以上）

- [ ] **Step 6: コミット**

```bash
git add main.py tests/test_basic.py
git commit -m "feat: add main.py CLI entry point with config merging and error handling"
```

---

### Task 7: 最終確認

**Files:** なし（確認のみ）

- [ ] **Step 1: 全テストを実行**

```bash
pytest tests/ -v
```

Expected: 全テスト passed、0 failed

- [ ] **Step 2: ヘルプを確認**

```bash
python main.py --help
```

Expected:
```
usage: main.py [-h] [--keyword KEYWORD] [--category-id CATEGORY_ID] ...
楽天市場からショップ情報を収集します
```

- [ ] **Step 3: バリデーションエラーの確認**

```bash
python main.py
```

Expected: `エラー: --keyword または --category-id のいずれかを指定してください。`

- [ ] **Step 4: プロジェクト全体をコミット**

```bash
git status  # 未追跡ファイルがないことを確認
git add -A
git commit -m "chore: finalize all files and verify tests pass"
```

---

## 動作確認用サンプルコマンド（.env 設定後）

```bash
# キーワード検索 → CSV出力
python main.py --keyword "ワイヤレスイヤホン" --count 30 --output csv

# カテゴリID検索 → Excel出力
python main.py --category-id 100371 --count 60 --output excel

# config.yaml を使った実行
cp config.yaml.example config.yaml
python main.py --config config.yaml

# Google Sheets 出力
python main.py --keyword "コーヒー豆" --count 30 --output gsheet --sheet-id YOUR_SHEET_ID
```
