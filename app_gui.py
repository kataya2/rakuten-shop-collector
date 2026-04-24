"""CustomTkinter GUI for Rakuten Shop Collector."""
from __future__ import annotations
import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from dotenv import load_dotenv

from src.api_client import ApiClient
from src.output_writer import write_csv, write_excel
from src.shop_extractor import ShopInfo, extract_shops
from src.utils import RakutenAPIError

load_dotenv()

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def _settings_path() -> Path:
    """Return the absolute path to config/settings.json, exe-aware."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return base / "config" / "settings.json"


def _load_settings(path: Path | None = None) -> dict | None:
    """Load settings.json and return as dict, or None if missing/invalid."""
    p = path if path is not None else _settings_path()
    if not p.exists():
        return None
    try:
        result = json.loads(p.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _save_settings(data: dict, path: Path | None = None) -> bool:
    """Save data to settings.json. Returns True on success, False on failure."""
    p = path if path is not None else _settings_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except (OSError, TypeError):
        return False


def _load_credentials() -> tuple[str, str, str, str]:
    """Load credentials with priority: settings.json > env vars. Returns (app_id, access_key, referer, error)."""
    settings = _load_settings()
    if settings and settings.get("rakuten_app_id") and settings.get("rakuten_access_key"):
        return (
            settings["rakuten_app_id"],
            settings["rakuten_access_key"],
            settings.get("rakuten_referer", "https://github.com/"),
            "",
        )
    app_id, access_key, error = _check_credentials()
    if not error:
        referer = os.environ.get("RAKUTEN_REFERER", "https://github.com/")
        return app_id, access_key, referer, ""
    return "", "", "", error


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


class RakutenShopCollectorApp(ctk.CTk):
    """楽天ショップコレクター CustomTkinter GUIアプリ。"""

    def __init__(self) -> None:
        """ウィンドウ設定・クレデンシャル確認・全ウィジェット初期化。"""
        super().__init__()
        self.title("Rakuten Shop Collector")
        self.geometry("900x750")
        self.minsize(700, 600)

        self._shops: list[ShopInfo] = []
        self._app_id: str = ""
        self._access_key: str = ""
        self._theme: str = "light"

        self._build_header()
        self._build_search_frame()
        self._build_action_frame()
        self._build_result_frame()

        app_id, access_key, error = _check_credentials()
        if error:
            messagebox.showwarning("認証情報エラー", error)
            self._search_btn.configure(state="disabled")
        else:
            self._app_id = app_id
            self._access_key = access_key

    def _build_header(self) -> None:
        """ヘッダーエリア: タイトルとテーマ切替ボタン。"""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            frame,
            text="🛍️ Rakuten Shop Collector",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")

        self._theme_btn = ctk.CTkButton(
            frame,
            text="🌙 ダーク",
            width=100,
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="right")

    def _toggle_theme(self) -> None:
        """ライト/ダークテーマを切り替える。"""
        if self._theme == "light":
            ctk.set_appearance_mode("dark")
            self._theme = "dark"
            self._theme_btn.configure(text="☀️ ライト")
        else:
            ctk.set_appearance_mode("light")
            self._theme = "light"
            self._theme_btn.configure(text="🌙 ダーク")

    def _build_search_frame(self) -> None:
        """検索設定エリア: 検索方法・キーワード・カテゴリID・件数・出力形式。"""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=5)
        frame.columnconfigure(1, weight=1)

        self._search_type = tk.StringVar(value="keyword")

        ctk.CTkLabel(frame, text="検索方法:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ctk.CTkRadioButton(
            frame, text="キーワード", variable=self._search_type,
            value="keyword", command=self._on_search_type_change,
        ).grid(row=0, column=1, padx=5, pady=8, sticky="w")
        ctk.CTkRadioButton(
            frame, text="カテゴリID", variable=self._search_type,
            value="category", command=self._on_search_type_change,
        ).grid(row=0, column=2, padx=5, pady=8, sticky="w")

        ctk.CTkLabel(frame, text="キーワード:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self._keyword_entry = ctk.CTkEntry(
            frame, placeholder_text="例: ワイヤレスイヤホン", width=400,
        )
        self._keyword_entry.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=5)

        ctk.CTkLabel(frame, text="カテゴリID:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self._category_entry = ctk.CTkEntry(
            frame, placeholder_text="例: 100371", width=400, state="disabled",
        )
        self._category_entry.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=5)

        ctk.CTkLabel(frame, text="取得件数:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self._count_slider = ctk.CTkSlider(
            frame, from_=30, to=500, number_of_steps=47,
            command=self._on_count_change, width=350,
        )
        self._count_slider.set(30)
        self._count_slider.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        self._count_label = ctk.CTkLabel(frame, text="30件", width=60)
        self._count_label.grid(row=3, column=2, padx=5, pady=5, sticky="w")

        self._output_fmt = tk.StringVar(value="csv")
        ctk.CTkLabel(frame, text="出力形式:").grid(row=4, column=0, sticky="w", padx=10, pady=(5, 10))
        fmt_frame = ctk.CTkFrame(frame, fg_color="transparent")
        fmt_frame.grid(row=4, column=1, columnspan=2, sticky="w", pady=(5, 10))
        for val, label in [("csv", "CSV"), ("excel", "Excel"), ("both", "両方")]:
            ctk.CTkRadioButton(
                fmt_frame, text=label, variable=self._output_fmt, value=val,
            ).pack(side="left", padx=10)

    def _on_search_type_change(self) -> None:
        """検索方法切替時にEntry有効・無効を更新する。"""
        if self._search_type.get() == "keyword":
            self._keyword_entry.configure(state="normal")
            self._category_entry.configure(state="disabled")
        else:
            self._keyword_entry.configure(state="disabled")
            self._category_entry.configure(state="normal")

    def _on_count_change(self, value: float) -> None:
        """スライダー値変更時に10刻みに丸めて件数ラベルを更新する。"""
        rounded = max(30, min(500, round(value / 10) * 10))
        self._count_label.configure(text=f"{rounded}件")

    def _build_action_frame(self) -> None:
        """アクションエリア: 検索実行ボタン・進捗バー（初期非表示）・ステータスラベル。"""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=5)

        self._search_btn = ctk.CTkButton(
            frame,
            text="🔍 検索を実行",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self._on_search,
        )
        self._search_btn.pack(fill="x", pady=(0, 5))

        self._progress_bar = ctk.CTkProgressBar(frame, mode="indeterminate")
        # 初期状態では非表示 — _on_search() 内で pack() して表示する

        self._status_label = ctk.CTkLabel(frame, text="", text_color="gray")
        self._status_label.pack(fill="x")

    def _build_result_frame(self) -> None:
        """結果エリア: サマリーラベル・Treeview（縦横スクロール付き）・保存ボタン群。"""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        self._summary_label = ctk.CTkLabel(frame, text="", anchor="w")
        self._summary_label.pack(fill="x", padx=10, pady=(10, 5))

        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("shop_name", "item_count", "avg_review", "total_reviews", "shop_url")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse",
        )
        for col, heading, width in [
            ("shop_name", "ショップ名", 200),
            ("item_count", "商品数", 70),
            ("avg_review", "平均レビュー", 100),
            ("total_reviews", "総レビュー数", 100),
            ("shop_url", "ショップURL", 300),
        ]:
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=width, minwidth=50)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkButton(btn_frame, text="💾 CSVで保存", command=self._save_csv).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Excelで保存", command=self._save_excel).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 両方保存", command=self._save_both).pack(side="left", padx=5)

    def _on_search(self) -> None:
        """検索ボタン押下時: バリデーション → 進捗バー表示 → 検索スレッド起動。"""
        search_type = self._search_type.get()
        keyword = self._keyword_entry.get().strip() if search_type == "keyword" else None
        category_id = self._category_entry.get().strip() if search_type == "category" else None

        if not keyword and not category_id:
            messagebox.showwarning("入力エラー", "キーワードまたはカテゴリIDを入力してください。")
            return

        count = max(30, min(500, round(self._count_slider.get() / 10) * 10))

        self._search_btn.configure(state="disabled")
        self._progress_bar.pack(fill="x", pady=(0, 5), before=self._status_label)
        self._progress_bar.start()
        self._status_label.configure(text="⏳ 検索中...")

        threading.Thread(
            target=self._run_search,
            args=(keyword, category_id, count),
            daemon=True,
        ).start()

    def _run_search(self, keyword: str | None, category_id: str | None, count: int) -> None:
        """別スレッドでAPI検索を実行する（UIウィジェットに直接触れない）。"""
        try:
            referer = os.environ.get("RAKUTEN_REFERER", "https://github.com")
            client = ApiClient(self._app_id, self._access_key, referer=referer)
            items = client.search(keyword=keyword, category_id=category_id, count=count)
            shops = extract_shops(items)
            self.after(0, self._on_search_done, shops, len(items))
        except RakutenAPIError as e:
            msg = str(e)
            if "applicationId" in msg or "accessKey" in msg or "認証" in msg:
                user_msg = (
                    "APIキーを確認してください。\n"
                    ".envのRAKUTEN_APP_IDとRAKUTEN_ACCESS_KEYを見直してください。\n\n"
                    f"詳細: {msg}"
                )
            elif "Referer" in msg:
                user_msg = (
                    "Refererエラーです。\n"
                    ".envのRAKUTEN_REFERERを確認してください。\n\n"
                    f"詳細: {msg}"
                )
            else:
                user_msg = f"APIエラーが発生しました。\n\n詳細: {msg}"
            self.after(0, self._on_search_error, user_msg)
        except OSError:
            self.after(0, self._on_search_error, "ネットワーク接続を確認してください。")
        except Exception as e:
            self.after(0, self._on_search_error, f"予期しないエラーが発生しました: {e}")

    def _on_search_done(self, shops: list[ShopInfo], item_count: int) -> None:
        """検索完了時: 進捗バー非表示・Treeview更新・サマリー表示。"""
        self._progress_bar.stop()
        self._progress_bar.pack_forget()
        self._search_btn.configure(state="normal")
        self._status_label.configure(text="")
        self._shops = shops

        if not shops:
            messagebox.showinfo(
                "結果なし",
                "該当するショップが見つかりませんでした。\nキーワードを変えて試してください。",
            )
            return

        self._summary_label.configure(
            text=f"✅ {item_count}商品から {len(shops)}ショップを取得しました",
        )
        for row in self._tree.get_children():
            self._tree.delete(row)
        for s in shops:
            self._tree.insert("", "end", values=(
                s.shop_name, s.item_count, s.avg_review, s.total_reviews, s.shop_url,
            ))

    def _on_search_error(self, message: str) -> None:
        """検索エラー時: 進捗バー非表示・ボタン再有効化・エラーダイアログ表示。"""
        self._progress_bar.stop()
        self._progress_bar.pack_forget()
        self._search_btn.configure(state="normal")
        self._status_label.configure(text="")
        messagebox.showerror("エラー", message)

    def _save_csv(self) -> None:
        """CSVファイル保存ダイアログを開いて write_csv() で保存する。"""
        if not self._shops:
            messagebox.showwarning("保存エラー", "保存するデータがありません。先に検索を実行してください。")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="shops_result.csv",
        )
        if path:
            write_csv(self._shops, path)
            messagebox.showinfo("保存完了", f"CSVを保存しました:\n{path}")

    def _save_excel(self) -> None:
        """Excelファイル保存ダイアログを開いて write_excel() で保存する。"""
        if not self._shops:
            messagebox.showwarning("保存エラー", "保存するデータがありません。先に検索を実行してください。")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="shops_result.xlsx",
        )
        if path:
            write_excel(self._shops, path)
            messagebox.showinfo("保存完了", f"Excelを保存しました:\n{path}")

    def _save_both(self) -> None:
        """フォルダ選択ダイアログを開いてCSVとExcelを同フォルダに保存する。"""
        if not self._shops:
            messagebox.showwarning("保存エラー", "保存するデータがありません。先に検索を実行してください。")
            return
        folder = filedialog.askdirectory(title="保存先フォルダを選択")
        if folder:
            csv_path = str(Path(folder) / "shops_result.csv")
            xlsx_path = str(Path(folder) / "shops_result.xlsx")
            write_csv(self._shops, csv_path)
            write_excel(self._shops, xlsx_path)
            messagebox.showinfo(
                "保存完了",
                f"2ファイルを保存しました:\n{csv_path}\n{xlsx_path}",
            )


if __name__ == "__main__":
    app = RakutenShopCollectorApp()
    app.mainloop()
