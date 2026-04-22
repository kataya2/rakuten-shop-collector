"""CustomTkinter GUI for Rakuten Shop Collector."""
from __future__ import annotations
import os


def _check_credentials() -> tuple[str, str, str]:
    """
    .envからRAKUTEN_APP_IDとRAKUTEN_ACCESS_KEYを読み込む。
    Returns: (app_id, access_key, error_message)。error_messageが空の場合は正常。
    """
    app_id = os.environ.get("RAKUTEN_APP_ID", "")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "")
    if not app_id:
        return "", "", "RAKUTEN_APP_ID が設定されていません。.env を確認してください。"
    if not access_key:
        return app_id, "", "RAKUTEN_ACCESS_KEY が設定されていません。.env を確認してください。"
    return app_id, access_key, ""
