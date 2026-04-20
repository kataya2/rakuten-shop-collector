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
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ConfigError(f"設定ファイルはYAML辞書形式である必要があります: {path}")
    return cfg


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
            path = _output_path(filename, fmt)
            write_csv(shops, path)
            print(f"出力完了: {path}")
        elif fmt == "excel":
            path = _output_path(filename, fmt)
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
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
