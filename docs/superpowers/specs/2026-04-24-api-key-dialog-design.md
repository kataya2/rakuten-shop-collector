# Design Spec: APIキー入力画面（.exe配布対応）

**Date:** 2026-04-24  
**Branch:** feature/exe-ready  
**Scope:** `app_gui.py` のみ変更（`src/`, `main.py`, `app.py` は変更しない）

---

## 背景・目的

`.exe` 配布時に非技術者ユーザーが `.env` ファイルを手動作成するのは敷居が高い。
GUI 内で楽天 API キーを入力・保存できる仕組みを追加し、初回起動から迷わず使えるようにする。

---

## アーキテクチャ概要

**アプローチ A を採用：既存関数を保持して新関数を追加**

- `_check_credentials()` は変更しない（既存 27 件テスト維持）
- 設定管理用の新関数群を `app_gui.py` に追加
- `ApiKeyDialog` / `SettingsDialog` を新クラスとして追加

---

## 新規モジュールレベル関数

| 関数 | シグネチャ | 役割 |
|------|-----------|------|
| `_settings_path` | `() → Path` | `.exe`/通常 Python 両対応で `config/settings.json` のパスを返す |
| `_load_settings` | `() → dict \| None` | settings.json 読み込み。ファイルなし・破損時は `None` |
| `_save_settings` | `(data: dict) → bool` | settings.json 書き込み。成功で `True`、失敗で `False` |
| `_load_credentials` | `() → tuple[str,str,str,str]` | `(app_id, access_key, referer, error)` を優先順で返す |

### `_settings_path()` の .exe 判定

```python
if getattr(sys, 'frozen', False):   # PyInstaller .exe
    base = Path(sys.executable).parent
else:
    base = Path(__file__).parent    # 通常の Python 実行
return base / "config" / "settings.json"
```

### `_load_credentials()` の優先順位

1. `settings.json` に `rakuten_app_id` と `rakuten_access_key` が両方存在 → それを使う
2. 環境変数 `RAKUTEN_APP_ID` / `RAKUTEN_ACCESS_KEY` が存在 → `_check_credentials()` に委譲
3. どちらもない → `error` 文字列を返す（→ `ApiKeyDialog` を表示）

---

## 設定ファイル仕様

**保存先：** `config/settings.json`（`.exe` と同じフォルダ基準）

```json
{
  "rakuten_app_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "rakuten_access_key": "your_access_key_here",
  "rakuten_referer": "https://github.com/"
}
```

---

## `RakutenShopCollectorApp` の変更点

### `__init__()` の変更

- 全ウィジェット構築後、検索ボタンは最初から `disabled`
- `_check_credentials()` の呼び出しを削除
- `self._referer: str = ""` を新インスタンス変数として追加
- `self.after(200, self._check_on_startup)` でメインループ開始後に認証チェック

### `_check_on_startup()` フロー

```
_load_credentials() を呼ぶ
  ├─ error なし → self._app_id, _access_key, _referer に代入 → 検索ボタン有効化
  └─ error あり → ApiKeyDialog を表示（wait_window でブロック）
                   ├─ dialog.result あり → 認証情報代入・ボタン有効化
                   └─ dialog.result なし（キャンセル） → self.destroy()
```

### `_build_header()` の変更

ヘッダーに「⚙️ 設定」ボタンを追加：

```
[🛍️ Rakuten Shop Collector]  ......  [⚙️ 設定]  [🌙 ダーク]
```

### `_run_search()` の変更

```python
# 変更前
referer = os.environ.get("RAKUTEN_REFERER", "https://github.com/")
# 変更後
referer = self._referer or os.environ.get("RAKUTEN_REFERER", "https://github.com/")
```

APIキーエラー時のメッセージを `.env` 参照から設定画面への案内に変更：

```
# 変更前: ".envのRAKUTEN_APP_IDとRAKUTEN_ACCESS_KEYを見直してください"
# 変更後: "⚙️ 設定ボタンからAPIキーを確認・更新してください"
```

---

## `ApiKeyDialog` クラス

```python
class ApiKeyDialog(ctk.CTkToplevel):
    result: dict | None
    # {"app_id": ..., "access_key": ..., "referer": ...} or None
```

### レイアウト

```
┌─────────────────────────────────────────────┐
│  楽天APIキーの初回設定                        │
├─────────────────────────────────────────────┤
│  説明文（2行）                               │
│  [📖 楽天Developersを開く]                   │
├─────────────────────────────────────────────┤
│  Application ID  [________________]         │
│  Access Key      [**************] [👁]      │
│  Referer         [https://github.com/]      │
├─────────────────────────────────────────────┤
│  ⚠️ エラーメッセージ（バリデーション失敗時）  │
├─────────────────────────────────────────────┤
│  [💾 保存して開始]        [❌ キャンセル]    │
└─────────────────────────────────────────────┘
```

### バリデーション（「保存して開始」クリック時）

| チェック | エラーメッセージ |
|---------|----------------|
| App ID が空 | `Application ID を入力してください` |
| App ID がUUID形式でない（ハイフン4つ未満） | `Application ID はUUID形式で入力してください（例: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）` |
| Access Key が空 | `Access Key を入力してください` |

エラーはダイアログ内の `CTkLabel`（赤文字）に表示。`messagebox` は使わない。

### 保存フロー

```
バリデーション通過
→ _save_settings({"rakuten_app_id": ..., "rakuten_access_key": ..., "rakuten_referer": ...})
  ├─ 成功 → self.result = {...} → self.destroy()
  └─ 失敗 → エラーラベルに「設定ファイルの保存に失敗しました: {理由}」
```

### キャンセル・×ボタン

```python
self.result = None
self.destroy()
```

`protocol("WM_DELETE_WINDOW", self._on_cancel)` で×ボタンも同様に処理。

---

## `SettingsDialog` クラス

```python
class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent: RakutenShopCollectorApp) -> None:
```

### レイアウト

```
┌─────────────────────────────────────────────┐
│  設定                                        │
├─────────────────────────────────────────────┤
│  Application ID  [________________]         │
│  Access Key      [**************] [👁]      │
│  Referer         [https://github.com/]      │
├─────────────────────────────────────────────┤
│  ⚠️ エラーメッセージ（バリデーション失敗時）  │
├─────────────────────────────────────────────┤
│  [💾 保存]   [🗑️ 設定をリセット]  [✖ 閉じる] │
└─────────────────────────────────────────────┘
```

### 「💾 保存」フロー

```
ApiKeyDialog と同じバリデーション
→ _save_settings(...)
  ├─ 成功 → parent._app_id, _access_key, _referer を更新
  │        → 検索ボタンを有効化
  │        → messagebox.showinfo("保存しました")
  │        → self.destroy()
  └─ 失敗 → エラーラベルに表示
```

### 「🗑️ 設定をリセット」フロー（即時反映）

```
messagebox.askyesno("確認", "設定をリセットしますか？\n現在のAPIキーは削除されます。")
├─ No  → 何もしない
└─ Yes → settings.json を削除
        → parent._app_id = parent._access_key = parent._referer = ""
        → parent._search_btn.configure(state="disabled")
        → self.destroy()
        → messagebox.showinfo("リセットしました。新しいAPIキーを設定してください。")
        → parent._check_on_startup()
           ├─ 入力・保存 → 検索ボタン有効化
           └─ キャンセル → parent.destroy()
```

### 「✖ 閉じる」・×ボタン

何も変更せずに `self.destroy()`。

---

## エラーハンドリング一覧

| 状況 | 対応 |
|------|------|
| `config/` フォルダが存在しない | `_save_settings()` 内で `mkdir(parents=True, exist_ok=True)` |
| JSON 破損 | `_load_settings()` が `None` を返す → 初回設定フローへ |
| 書き込み権限なし | `_save_settings()` が `False` を返す → ダイアログ内エラーラベル |
| settings.json が存在しない | `_load_settings()` が `None` を返す（正常ケース） |

---

## ファイル変更一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `app_gui.py` | 変更 | 全改修内容 |
| `config/.gitkeep` | 新規作成 | フォルダを Git 管理対象に |
| `.gitignore` | 変更 | `config/settings.json` を追加 |
| `tests/test_basic.py` | 変更なし | 27 件すべてそのまま通過 |
| `src/` 配下 | 変更なし | 一切触れない |
| `main.py`, `app.py` | 変更なし | 一切触れない |
