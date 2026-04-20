# Rakuten Shop Collector — 設計仕様書

Date: 2026-04-20

---

## 概要

楽天市場の新API（openapi.rakuten.co.jp）を使用して、キーワードまたはカテゴリIDで検索し、ショップ情報をCSV・Excel・Google Spreadsheetsに出力するPythonツール。

---

## アーキテクチャ

```
main.py
  ├── src/api_client.py      ApiClient クラス（HTTP通信）
  ├── src/shop_extractor.py  関数群（レスポンス→ShopInfo変換・集約）
  ├── src/output_writer.py   関数群（CSV/Excel/Sheets書き出し）
  └── src/utils.py           ロガー生成・カスタム例外
```

データフロー：

```
CLIArgs / config.yaml
  → main.py
    → ApiClient.search() — ページネーションループ
      → list[dict] (raw items)
    → shop_extractor.extract_shops()
      → list[ShopInfo]（shopCodeで重複排除・集約済み）
    → output_writer.write_csv() / write_excel() / write_gsheet()
```

設定の優先順位（高→低）: CLI引数 > config.yaml > .env > デフォルト値

---

## モジュール詳細

### src/utils.py

**カスタム例外:**
- `RakutenAPIError(Exception)` — API呼び出し失敗全般
- `ConfigError(Exception)` — 設定値の不足・不正

**関数:**
- `get_logger(name: str) -> logging.Logger` — ファイル＋コンソール出力のロガーを返す

---

### src/api_client.py

**クラス: `ApiClient`**

```python
API_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"
# 旧URL (app.rakuten.co.jp) は使用しない
```

`__init__(app_id, access_key, wait_seconds=1.1, max_retries=3)`:
- `requests.Session` を生成
- デフォルトヘッダーに `Referer: https://github.com/` を設定
- 認証情報をインスタンス変数に保持

`search(keyword, category_id, count) -> list[dict]`:
- `applicationId` と `accessKey` をクエリパラメータに含める（両方必須）
- `hits=30`、`page` を1からインクリメントしてページネーション
- 最大100ページ（最大3000件）、`count` 件に達したら終了
- リクエスト間隔: `time.sleep(1.1)`
- 失敗時: 指数バックオフ（1s, 2s, 4s）で最大 `max_retries` 回リトライ後 `RakutenAPIError` をraise

**レスポンス構造（参照パス）:**
```
response["Items"][i]["Item"]["shopCode"]
response["Items"][i]["Item"]["shopName"]
response["Items"][i]["Item"]["shopUrl"]
response["Items"][i]["Item"]["reviewAverage"]
response["Items"][i]["Item"]["reviewCount"]
response["Items"][i]["Item"]["genreId"]
response["Items"][i]["Item"]["itemPrice"]
response["Items"][i]["Item"]["itemName"]
```

**エラーハンドリング:**

| 条件 | メッセージ（日本語） |
|------|---------------------|
| HTTP 403 / `REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING` | `Refererヘッダーが不正です。登録済みドメインを確認してください。` |
| レスポンスに `wrong_parameter` または `specify valid applicationId` | `applicationIdが無効です。.envのRAKUTEN_APP_IDと楽天デベロッパーコンソールを確認してください。` |
| レスポンスに `accessKey must be present` | `accessKeyが設定されていません。.envのRAKUTEN_ACCESS_KEYを確認してください。` |
| HTTP 401 | `認証に失敗しました。RAKUTEN_APP_IDとRAKUTEN_ACCESS_KEYを両方確認してください。` |
| ネットワークエラー（`requests.exceptions.RequestException`） | リトライ後に `APIへの接続に失敗しました: {detail}` |

---

### src/shop_extractor.py

**dataclass: `ShopInfo`**

```python
@dataclass
class ShopInfo:
    shop_id: str       # shopCode
    shop_name: str     # shopName
    shop_url: str      # shopUrl
    item_count: int    # 検索結果内での出現アイテム数
    avg_review: float  # 出現アイテムのreviewAverageの平均
    total_reviews: int # reviewCountの合計
    min_price: int     # itemPriceの最小値
    genre_id: str      # 最初のアイテムのgenreId（代表値）
```

**関数:**

`extract_shops(items: list[dict]) -> list[ShopInfo]`:
- `shopCode` でグループ化し重複排除
- 各ShopInfoを集約ロジックで生成
- `item_count` 降順でソートして返す

---

### src/output_writer.py

**関数:**

`write_csv(shops: list[ShopInfo], filepath: str) -> None`
- `csv.DictWriter` を使用、UTF-8 BOM付き（Excel対応）

`write_excel(shops: list[ShopInfo], filepath: str) -> None`
- `openpyxl` でヘッダー行を太字・背景色付きで装飾
- 列幅を自動調整

`write_gsheet(shops: list[ShopInfo], sheet_id: str, credentials_path: str) -> None`
- `gspread` + サービスアカウントJSONで認証
- `shops` シートを上書き（既存データはクリア）

出力カラム順: `shop_id, shop_name, shop_url, item_count, avg_review, total_reviews, min_price, genre_id`

---

### main.py

責務:
1. `.env` ロード（`python-dotenv`）
2. `config.yaml` パース（`pyyaml`）
3. `argparse` でCLI引数をパース
4. 設定をマージ（CLI > yaml > .env > デフォルト）
5. `keyword` と `category_id` が両方指定された場合はエラーを表示してexit(1)
6. `ApiClient` / `extract_shops` / `output_writer` を順に呼び出す
6. 出力ファイルパスを `output/shops_YYYYMMDD_HHMMSS.{ext}` で生成
7. 例外をキャッチして日本語エラーメッセージを表示しexit(1)

---

## 設定ファイル

### .env.example
```dotenv
RAKUTEN_APP_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
RAKUTEN_ACCESS_KEY=your_access_key_here
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/credentials.json
```

### config.yaml.example
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

---

## テスト方針（tests/test_basic.py）

| テスト | 手法 |
|--------|------|
| `extract_shops` の重複排除・集約 | 固定dictリストを入力、ShopInfoを検証 |
| `ApiClient` のリクエスト構築 | `unittest.mock.patch` でSessionをモック |
| CSV出力ファイル生成 | `tmp_path`（pytest）で一時ファイルに書き出し |
| `main.py` CLI引数パース | `--keyword` 等を与えてargparseを検証 |

---

## requirements.txt

```
requests>=2.31.0
openpyxl>=3.1.0
gspread>=6.0.0
google-auth>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
pytest>=8.0.0
```
