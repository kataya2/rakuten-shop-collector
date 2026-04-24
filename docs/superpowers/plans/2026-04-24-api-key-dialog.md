# API Key Dialog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `app_gui.py` に APIキー入力ダイアログと設定画面を追加し、`.exe` 配布時に非技術者が GUI だけで楽天 API キーを設定できるようにする。

**Architecture:** 設定管理用のモジュールレベル関数群（`_settings_path` / `_load_settings` / `_save_settings` / `_load_credentials`）を追加し、`ApiKeyDialog`（初回設定）と `SettingsDialog`（変更・リセット）の 2 クラスを実装する。`_check_credentials()` は変更せず既存 27 件テストを維持。起動時の認証チェックは `self.after(200, ...)` で遅延実行しモーダルダイアログとの干渉を防ぐ。

**Tech Stack:** Python 3.10+, CustomTkinter 5.2+, tkinter（標準）, json（標準）

---

## ファイル変更一覧

| ファイル | 種別 | 内容 |
|---------|------|------|
| `config/.gitkeep` | 新規作成 | フォルダを Git 管理対象に |
| `.gitignore` | 変更 | `config/settings.json` を追加 |
| `tests/test_basic.py` | 変更 | Task 2・3 の新規テストを追記 |
| `app_gui.py` | 変更 | 全改修内容（Task 2〜6） |

`src/` 配下・`main.py`・`app.py` は一切変更しない。

---

## Task 1: Git インフラ整備

**Files:**
- Create: `config/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: `config/` フォルダと `.gitkeep` を作成**

```bash
mkdir config
touch config/.gitkeep
```

- [ ] **Step 2: `.gitignore` に `config/settings.json` を追加**

`.gitignore` の `# Rakuten Shop Collector output files` セクションの直後に追加する：

```
# Rakuten Shop Collector output files
output/*.csv
output/*.xlsx

# API key settings (contains credentials)
config/settings.json
```

- [ ] **Step 3: コミット**

```bash
git add config/.gitkeep .gitignore
git commit -m "chore: add config/ folder and ignore settings.json"
```

---

## Task 2: 設定管理関数の TDD

**Files:**
- Modify: `tests/test_basic.py`（テスト追記）
- Modify: `app_gui.py`（関数追加）

### 追加する関数シグネチャ

```python
def _settings_path() -> Path: ...
def _load_settings(path: Path | None = None) -> dict | None: ...
def _save_settings(data: dict, path: Path | None = None) -> bool: ...
```

`path` 引数はテスト時に一時ディレクトリを渡すために用意。本番コードは引数なしで呼ぶ。

- [ ] **Step 1: 失敗するテストを `tests/test_basic.py` に追記**

ファイル末尾に追加する：

```python
import json
from pathlib import Path
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_basic.py::test_settings_path_returns_path_instance -v
```

期待: `ImportError: cannot import name '_settings_path' from 'app_gui'`

- [ ] **Step 3: `app_gui.py` に関数を実装**

`app_gui.py` の先頭 import に `import json` と `import sys` を追加した上で、`_check_credentials()` 定義の直前に以下を挿入する：

```python
def _settings_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return base / "config" / "settings.json"


def _load_settings(path: Path | None = None) -> dict | None:
    p = path if path is not None else _settings_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_settings(data: dict, path: Path | None = None) -> bool:
    p = path if path is not None else _settings_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False
```

- [ ] **Step 4: テストがすべて通ることを確認**

```bash
pytest tests/test_basic.py -v
```

期待: 33 passed（既存 27 件 + 新規 6 件）

- [ ] **Step 5: コミット**

```bash
git add tests/test_basic.py app_gui.py
git commit -m "feat: add settings file management functions with TDD"
```

---

## Task 3: `_load_credentials()` の TDD

**Files:**
- Modify: `tests/test_basic.py`（テスト追記）
- Modify: `app_gui.py`（関数追加）

### 追加する関数シグネチャ

```python
def _load_credentials() -> tuple[str, str, str, str]:
    # (app_id, access_key, referer, error)
```

- [ ] **Step 1: 失敗するテストを `tests/test_basic.py` に追記**

ファイル末尾に追加する：

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_basic.py::test_load_credentials_from_settings -v
```

期待: `ImportError: cannot import name '_load_credentials' from 'app_gui'`

- [ ] **Step 3: `app_gui.py` に関数を実装**

`_save_settings()` の直後に追加する：

```python
def _load_credentials() -> tuple[str, str, str, str]:
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
```

- [ ] **Step 4: テストがすべて通ることを確認**

```bash
pytest tests/test_basic.py -v
```

期待: 37 passed（既存 33 件 + 新規 4 件）

- [ ] **Step 5: コミット**

```bash
git add tests/test_basic.py app_gui.py
git commit -m "feat: add _load_credentials with priority chain (TDD)"
```

---

## Task 4: `ApiKeyDialog` クラスの実装

**Files:**
- Modify: `app_gui.py`（クラス追加・import 追加）

- [ ] **Step 1: `import webbrowser` を `app_gui.py` の import ブロックに追加**

`app_gui.py` 先頭の import ブロック（`import os` の行の近く）に追加する：

```python
import webbrowser
```

- [ ] **Step 2: `RakutenShopCollectorApp` クラス定義の直前に `ApiKeyDialog` クラスを追加**

```python
class ApiKeyDialog(ctk.CTkToplevel):
    """楽天APIキー初回設定モーダルダイアログ。"""

    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent)
        self.title("楽天APIキーの初回設定")
        self.geometry("500x410")
        self.resizable(False, False)
        self.result: dict | None = None
        self._show_key: bool = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.grab_set()
        self.focus_set()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text=(
                "このアプリを使用するには、楽天APIキーが必要です。\n"
                "楽天Developersで無料のアプリを作成してAPIキーを取得してください。"
            ),
            wraplength=460,
            justify="left",
        ).pack(padx=20, pady=(20, 5), anchor="w")

        ctk.CTkButton(
            self,
            text="📖 楽天Developersを開く",
            width=220,
            command=lambda: webbrowser.open("https://webservice.rakuten.co.jp/"),
        ).pack(padx=20, pady=(0, 15), anchor="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=20)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Application ID:").grid(
            row=0, column=0, sticky="w", pady=6
        )
        self._app_id_entry = ctk.CTkEntry(
            form,
            placeholder_text="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            width=300,
        )
        self._app_id_entry.grid(
            row=0, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=6
        )

        ctk.CTkLabel(form, text="Access Key:").grid(
            row=1, column=0, sticky="w", pady=6
        )
        self._access_key_entry = ctk.CTkEntry(form, show="*", width=260)
        self._access_key_entry.grid(
            row=1, column=1, sticky="ew", padx=(10, 5), pady=6
        )
        ctk.CTkButton(
            form, text="👁", width=34, command=self._toggle_key_visibility
        ).grid(row=1, column=2, pady=6)

        ctk.CTkLabel(form, text="Referer:").grid(
            row=2, column=0, sticky="w", pady=6
        )
        self._referer_entry = ctk.CTkEntry(form, width=300)
        self._referer_entry.insert(0, "https://github.com/")
        self._referer_entry.grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=6
        )

        self._error_label = ctk.CTkLabel(self, text="", text_color="red", wraplength=460)
        self._error_label.pack(padx=20, pady=(10, 0), anchor="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))
        ctk.CTkButton(
            btn_frame, text="💾 保存して開始", command=self._on_save
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_frame, text="❌ キャンセル", fg_color="gray", command=self._on_cancel
        ).pack(side="left")

    def _toggle_key_visibility(self) -> None:
        self._show_key = not self._show_key
        self._access_key_entry.configure(show="" if self._show_key else "*")

    def _validate(self) -> str:
        app_id = self._app_id_entry.get().strip()
        access_key = self._access_key_entry.get().strip()
        if not app_id:
            return "Application ID を入力してください"
        if app_id.count("-") < 4:
            return (
                "Application ID はUUID形式で入力してください"
                "（例: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）"
            )
        if not access_key:
            return "Access Key を入力してください"
        return ""

    def _on_save(self) -> None:
        error = self._validate()
        if error:
            self._error_label.configure(text=error)
            return
        app_id = self._app_id_entry.get().strip()
        access_key = self._access_key_entry.get().strip()
        referer = self._referer_entry.get().strip() or "https://github.com/"
        ok = _save_settings(
            {"rakuten_app_id": app_id, "rakuten_access_key": access_key, "rakuten_referer": referer}
        )
        if ok:
            self.result = {"app_id": app_id, "access_key": access_key, "referer": referer}
            self.destroy()
        else:
            self._error_label.configure(text="設定ファイルの保存に失敗しました。フォルダの書き込み権限を確認してください。")

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()
```

- [ ] **Step 3: テストが引き続き通ることを確認**

```bash
pytest tests/test_basic.py -q
```

期待: 37 passed

- [ ] **Step 4: コミット**

```bash
git add app_gui.py
git commit -m "feat: add ApiKeyDialog for initial API key setup"
```

---

## Task 5: `SettingsDialog` クラスの実装

**Files:**
- Modify: `app_gui.py`（クラス追加）

- [ ] **Step 1: `ApiKeyDialog` クラスの直後に `SettingsDialog` クラスを追加**

```python
class SettingsDialog(ctk.CTkToplevel):
    """APIキー設定変更・リセットモーダルダイアログ。"""

    def __init__(self, parent: "RakutenShopCollectorApp") -> None:
        super().__init__(parent)
        self._parent = parent
        self.title("設定")
        self.geometry("500x360")
        self.resizable(False, False)
        self._show_key: bool = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()
        self.focus_set()

    def _build_ui(self) -> None:
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=20, pady=20)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Application ID:").grid(
            row=0, column=0, sticky="w", pady=6
        )
        self._app_id_entry = ctk.CTkEntry(form, width=300)
        self._app_id_entry.insert(0, self._parent._app_id)
        self._app_id_entry.grid(
            row=0, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=6
        )

        ctk.CTkLabel(form, text="Access Key:").grid(
            row=1, column=0, sticky="w", pady=6
        )
        self._access_key_entry = ctk.CTkEntry(form, show="*", width=260)
        self._access_key_entry.insert(0, self._parent._access_key)
        self._access_key_entry.grid(
            row=1, column=1, sticky="ew", padx=(10, 5), pady=6
        )
        ctk.CTkButton(
            form, text="👁", width=34, command=self._toggle_key_visibility
        ).grid(row=1, column=2, pady=6)

        ctk.CTkLabel(form, text="Referer:").grid(
            row=2, column=0, sticky="w", pady=6
        )
        self._referer_entry = ctk.CTkEntry(form, width=300)
        self._referer_entry.insert(0, self._parent._referer or "https://github.com/")
        self._referer_entry.grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=6
        )

        self._error_label = ctk.CTkLabel(self, text="", text_color="red", wraplength=460)
        self._error_label.pack(padx=20, pady=(0, 10), anchor="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(
            btn_frame, text="💾 保存", command=self._on_save
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_frame, text="🗑️ 設定をリセット", fg_color="#c0392b", command=self._on_reset
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_frame, text="✖ 閉じる", fg_color="gray", command=self.destroy
        ).pack(side="left")

    def _toggle_key_visibility(self) -> None:
        self._show_key = not self._show_key
        self._access_key_entry.configure(show="" if self._show_key else "*")

    def _validate(self) -> str:
        app_id = self._app_id_entry.get().strip()
        access_key = self._access_key_entry.get().strip()
        if not app_id:
            return "Application ID を入力してください"
        if app_id.count("-") < 4:
            return (
                "Application ID はUUID形式で入力してください"
                "（例: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）"
            )
        if not access_key:
            return "Access Key を入力してください"
        return ""

    def _on_save(self) -> None:
        error = self._validate()
        if error:
            self._error_label.configure(text=error)
            return
        app_id = self._app_id_entry.get().strip()
        access_key = self._access_key_entry.get().strip()
        referer = self._referer_entry.get().strip() or "https://github.com/"
        ok = _save_settings(
            {"rakuten_app_id": app_id, "rakuten_access_key": access_key, "rakuten_referer": referer}
        )
        if ok:
            self._parent._app_id = app_id
            self._parent._access_key = access_key
            self._parent._referer = referer
            self._parent._search_btn.configure(state="normal")
            messagebox.showinfo("保存しました", "設定を保存しました。")
            self.destroy()
        else:
            self._error_label.configure(text="設定ファイルの保存に失敗しました。フォルダの書き込み権限を確認してください。")

    def _on_reset(self) -> None:
        if not messagebox.askyesno(
            "確認", "設定をリセットしますか？\n現在のAPIキーは削除されます。"
        ):
            return
        settings_file = _settings_path()
        if settings_file.exists():
            settings_file.unlink()
        self._parent._app_id = ""
        self._parent._access_key = ""
        self._parent._referer = ""
        self._parent._search_btn.configure(state="disabled")
        self.destroy()
        messagebox.showinfo("リセット完了", "リセットしました。新しいAPIキーを設定してください。")
        self._parent._check_on_startup()
```

- [ ] **Step 2: テストが引き続き通ることを確認**

```bash
pytest tests/test_basic.py -q
```

期待: 37 passed

- [ ] **Step 3: コミット**

```bash
git add app_gui.py
git commit -m "feat: add SettingsDialog for API key update and reset"
```

---

## Task 6: `RakutenShopCollectorApp` の改修と全体動作確認

**Files:**
- Modify: `app_gui.py`（既存クラスの変更）

- [ ] **Step 1: `app_gui.py` の import ブロックを更新**

ファイル先頭の import 群を以下の状態にする（`import sys`, `import json`, `import webbrowser` が追加されていることを確認）：

```python
"""CustomTkinter GUI for Rakuten Shop Collector."""
from __future__ import annotations
import json
import os
import sys
import threading
import tkinter as tk
import webbrowser
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
```

- [ ] **Step 2: `__init__()` を改修**

`RakutenShopCollectorApp.__init__()` を以下に置き換える：

```python
def __init__(self) -> None:
    super().__init__()
    self.title("Rakuten Shop Collector")
    self.geometry("900x750")
    self.minsize(700, 600)

    self._shops: list[ShopInfo] = []
    self._app_id: str = ""
    self._access_key: str = ""
    self._referer: str = ""
    self._theme: str = "light"

    self._build_header()
    self._build_search_frame()
    self._build_action_frame()
    self._build_result_frame()

    self.after(200, self._check_on_startup)
```

- [ ] **Step 3: `_build_action_frame()` の検索ボタンに `state="disabled"` を追加**

`_build_action_frame()` 内の `CTkButton` 生成部分を以下に変更する：

```python
self._search_btn = ctk.CTkButton(
    frame,
    text="🔍 検索を実行",
    font=ctk.CTkFont(size=14, weight="bold"),
    height=40,
    state="disabled",
    command=self._on_search,
)
```

- [ ] **Step 4: `_build_header()` に「⚙️ 設定」ボタンを追加**

`_build_header()` を以下に置き換える：

```python
def _build_header(self) -> None:
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

    ctk.CTkButton(
        frame,
        text="⚙️ 設定",
        width=80,
        command=self._open_settings,
    ).pack(side="right", padx=(0, 10))
```

- [ ] **Step 5: `_check_on_startup()` メソッドを追加**

`_toggle_theme()` の直前に追加する：

```python
def _check_on_startup(self) -> None:
    app_id, access_key, referer, error = _load_credentials()
    if not error:
        self._app_id = app_id
        self._access_key = access_key
        self._referer = referer
        self._search_btn.configure(state="normal")
        return
    dialog = ApiKeyDialog(self)
    self.wait_window(dialog)
    if dialog.result:
        self._app_id = dialog.result["app_id"]
        self._access_key = dialog.result["access_key"]
        self._referer = dialog.result["referer"]
        self._search_btn.configure(state="normal")
    else:
        self.destroy()
```

- [ ] **Step 6: `_open_settings()` メソッドを追加**

`_check_on_startup()` の直後に追加する：

```python
def _open_settings(self) -> None:
    dialog = SettingsDialog(self)
    self.wait_window(dialog)
```

- [ ] **Step 7: `_run_search()` の referer 取得とエラーメッセージを更新**

`_run_search()` 内の該当行を変更する：

```python
# 変更前
referer = os.environ.get("RAKUTEN_REFERER", "https://github.com/")

# 変更後
referer = self._referer or os.environ.get("RAKUTEN_REFERER", "https://github.com/")
```

同メソッド内の APIキーエラーメッセージも変更する：

```python
# 変更前
user_msg = (
    "APIキーを確認してください。\n"
    ".envのRAKUTEN_APP_IDとRAKUTEN_ACCESS_KEYを見直してください。\n\n"
    f"詳細: {msg}"
)

# 変更後
user_msg = (
    "APIキーを確認してください。\n"
    "⚙️ 設定ボタンからAPIキーを確認・更新してください。\n\n"
    f"詳細: {msg}"
)
```

- [ ] **Step 8: 全テストが通ることを確認**

```bash
pytest tests/test_basic.py -v
```

期待: 37 passed、0 failed

- [ ] **Step 9: コミット**

```bash
git add app_gui.py
git commit -m "feat: integrate ApiKeyDialog and SettingsDialog into main app"
```

---

## 動作確認チェックリスト（手動）

実装完了後、以下の順で動作確認を行う：

**初回起動テスト（settings.json がない状態）**
1. `config/settings.json` が存在しないこと（または削除する）
2. `.env` も一時的にリネーム（`.env.bak` 等）する
3. `python app_gui.py` を実行
4. 「楽天APIキーの初回設定」ダイアログが表示されること
5. 空のまま「保存して開始」→ エラーメッセージが赤字で表示されること
6. 無効な App ID（ハイフンなし）→ UUID形式エラーが表示されること
7. 正しい App ID と Access Key を入力 →「保存して開始」でメイン画面が開くこと
8. `config/settings.json` が作成されていること

**2回目以降の起動テスト**
1. `python app_gui.py` を実行
2. ダイアログなしで直接メイン画面が開き、検索ボタンが有効であること

**設定変更テスト**
1. ヘッダーの「⚙️ 設定」ボタンをクリック
2. 設定ダイアログが開き、現在の値が表示されること
3. Access Key の「👁」ボタンで表示/非表示が切り替わること
4. 値を変更して「💾 保存」→ 「保存しました」ダイアログが出ること

**リセットテスト**
1. 「🗑️ 設定をリセット」→ 確認ダイアログで「はい」
2. 「リセット完了」メッセージ後、初回設定ダイアログが再表示されること
3. キャンセルするとアプリが終了すること
4. 再設定するとメイン画面に戻り検索できること

**環境変数フォールバックテスト**
1. `config/settings.json` を削除し、`.env` に正しいキーを設定
2. `python app_gui.py` を実行 → ダイアログなしで起動すること

---

## 最終コミット

```bash
git push origin feature/exe-ready
```
