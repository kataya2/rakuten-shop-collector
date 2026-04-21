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
        referer: str = "https://github.com",
        wait_seconds: float = 1.1,
        max_retries: int = 3,
    ) -> None:
        self.app_id = app_id
        self.access_key = access_key
        self.wait_seconds = wait_seconds
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"Referer": referer})

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
        """リトライロジック付きでGETリクエストを実行し、レスポンスボディを返す。"""
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                logger.debug("送信Referer: %s", self.session.headers.get("Referer"))
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
        """HTTPレスポンスをチェックしてエラーを検出し、JSONボディを返す。"""
        if resp.status_code == 401:
            raise RakutenAPIError(
                "認証に失敗しました。"
                "RAKUTEN_APP_ID と RAKUTEN_ACCESS_KEY を両方確認してください。"
            )

        try:
            body = resp.json()
        except Exception:
            raise RakutenAPIError(
                f"APIから予期しないレスポンスが返されました (HTTP {resp.status_code}): {resp.text[:200]}"
            )

        error = body.get("error", "")
        desc = body.get("error_description", "")

        if resp.status_code == 403:
            logger.debug("403 response body: %s", resp.text[:500])
            if "REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING" in resp.text:
                raise RakutenAPIError(
                    "Refererヘッダーが不正です。"
                    "楽天デベロッパーコンソールの「許可されたWebサイト」を確認してください。"
                )
            raise RakutenAPIError(
                f"アクセスが拒否されました (HTTP 403): {resp.text[:300]}"
            )

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
