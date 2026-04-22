# app_gui.py — CustomTkinter GUI 設計仕様

**日付:** 2026-04-22  
**対象ファイル:** `app_gui.py`（新規）、`requirements.txt`（更新）、`README.md`（更新）

---

## 概要

既存のCLIツール（`main.py`）およびStreamlit版（`app.py`）はそのまま残し、
CustomTkinterベースのネイティブGUIアプリ `app_gui.py` を追加する。
既存の `src/` モジュールをそのまま再利用し、変更は加えない。

---

## アーキテクチャ

### ファイル構成（新規・変更のみ）

```
app_gui.py          ← 新規（プロジェクトルート）
requirements.txt    ← customtkinter を追加
README.md           ← GUI版セクション追加
```

### クラス設計

```
RakutenShopCollectorApp(ctk.CTk)
│
├── __init__()              ウィンドウ設定・クレデンシャル確認・全ウィジェット初期化
├── _build_header()         タイトル + テーマ切替ボタン
├── _build_search_frame()   検索設定エリア（ラジオ・Entry・スライダー）
├── _build_action_frame()   実行ボタン・進捗バー・ステータスラベル
├── _build_result_frame()   Treeview + 保存ボタン群
│
├── _on_search_type_change()  キーワード/カテゴリID切替時のEntry有効・無効化
├── _on_count_change()        スライダー値変更時の件数ラベル更新
├── _on_search()              ボタン押下 → 入力バリデーション → スレッド起動
├── _run_search()             別スレッドで ApiClient.search() → extract_shops()
├── _on_search_done()         after(0, ...) 経由でUI更新（Treeview投入）
├── _on_search_error()        after(0, ...) 経由でエラーダイアログ表示
│
├── _save_csv()               CSVファイル保存ダイアログ → write_csv()
├── _save_excel()             Excelファイル保存ダイアログ → write_excel()
├── _save_both()              フォルダ選択ダイアログ → CSV + Excel 両方保存
└── _toggle_theme()           Light ⇔ Dark トグル
```

### スレッドモデル

- `_run_search()` を `threading.Thread(daemon=True)` で起動
- 検索完了時は `self.after(0, self._on_search_done, shops, item_count)` でメインスレッドにUI更新を委ねる
- エラー時は `self.after(0, self._on_search_error, error_message)` で同様に委ねる
- CustomTkinterはスレッドセーフでないため、サブスレッドから直接ウィジェットを操作しない

---

## UIレイアウト（縦積み構成）

```
┌──────────────────────────────────────────────────────────┐
│  🛍️ Rakuten Shop Collector              [☀️ ライト]     │  ← ヘッダー
├──────────────────────────────────────────────────────────┤
│  検索方法:  ● キーワード  ○ カテゴリID                   │
│  キーワード: [__________________________________]         │
│  カテゴリID: [__________________________________] (無効)  │  ← 検索設定
│  取得件数:  ━━━●━━━━━━━━━━  30件                        │
│  出力形式:  ● CSV  ○ Excel  ○ 両方                      │
├──────────────────────────────────────────────────────────┤
│  [　　　　　🔍 検索を実行　　　　　]                      │  ← アクション
│  ████████████░░░░░  60%                                  │
│  ⏳ 2/4ページ取得中...                                    │
├──────────────────────────────────────────────────────────┤
│  ✅ 30商品から 22ショップを取得しました                   │
│  ┌ショップ名───┬商品数┬平均レビュー┬総レビュー数┬URL──┐  │
│  │ ...        │      │            │            │      │  │  ← 結果
│  └────────────┴──────┴────────────┴────────────┴──────┘  │
│  [💾 CSVで保存]  [💾 Excelで保存]  [💾 両方保存]         │
└──────────────────────────────────────────────────────────┘
```

### ウィジェット一覧

| エリア | ウィジェット | 備考 |
|--------|-------------|------|
| ヘッダー | `CTkLabel` | フォントサイズ 20、bold |
| ヘッダー | `CTkButton`（テーマ切替） | 右上配置、クリックで Light/Dark トグル |
| 検索設定 | `CTkRadioButton` × 2 | キーワード / カテゴリID |
| 検索設定 | `CTkEntry` × 2 | キーワード・カテゴリID（片方を disabled） |
| 検索設定 | `CTkSlider` | from_=30, to=500, number_of_steps=47（10刻み）、コールバックで `round(v/10)*10` に丸め |
| 検索設定 | `CTkLabel`（件数表示） | スライダー連動で更新 |
| 検索設定 | `CTkRadioButton` × 3 | CSV / Excel / 両方 |
| アクション | `CTkButton`（検索実行） | 幅いっぱい、fg_color="blue" |
| アクション | `CTkProgressBar` | 実行中のみ表示（`grid_remove` で非表示） |
| アクション | `CTkLabel`（ステータス） | 検索中の進捗・完了・エラーメッセージ表示 |
| 結果 | `CTkLabel`（サマリー） | 「XX商品からYYショップを取得」 |
| 結果 | `ttk.Treeview` | 標準tkinter（CTkに表組みなし） |
| 結果 | `CTkButton` × 3 | CSVで保存 / Excelで保存 / 両方保存 |

---

## エラーハンドリング

### 起動時チェック（`__init__` 内）

| 状態 | 動作 |
|------|------|
| `.env` が存在しない | `messagebox.showwarning` 表示、検索ボタンを `disabled` に |
| `RAKUTEN_APP_ID` が空 | 同上、「RAKUTEN_APP_ID が未設定」メッセージ |
| `RAKUTEN_ACCESS_KEY` が空 | 同上、「RAKUTEN_ACCESS_KEY が未設定」メッセージ |

### 検索実行時エラー

| エラー種別 | ダイアログメッセージ |
|-----------|-----------------|
| `RakutenAPIError`（認証系） | 「APIキーを確認してください。.envのRAKUTEN_APP_IDとRAKUTEN_ACCESS_KEYを見直してください。」 |
| `RakutenAPIError`（Referer系） | 「Refererエラーです。.envのRAKUTEN_REFERERを確認してください。」 |
| `ConnectionError` 等ネットワーク系 | 「ネットワーク接続を確認してください。」 |
| 結果0件 | 「該当するショップが見つかりませんでした。キーワードを変えて試してください。」 |
| その他 | 「予期しないエラーが発生しました: {メッセージ}」 |

**ダイアログ実装:** `tkinter.messagebox` を使用（`CTkMessagebox` は追加インストール不要の標準で統一）

---

## 保存動作

| ボタン | 動作 |
|--------|------|
| CSVで保存 | `filedialog.asksaveasfilename(defaultextension=".csv")` → `write_csv()` |
| Excelで保存 | `filedialog.asksaveasfilename(defaultextension=".xlsx")` → `write_excel()` |
| 両方保存 | `filedialog.askdirectory()` でフォルダ選択 → `shops_result.csv` と `shops_result.xlsx` を同フォルダに保存 |

---

## ウィンドウ設定

| 項目 | 値 |
|------|----|
| タイトル | `"Rakuten Shop Collector"` |
| サイズ | `900x750` |
| リサイズ | 可（`minsize(700, 600)` を設定） |
| 初期テーマ | ライトモード（`ctk.set_appearance_mode("light")`） |
| カラーテーマ | `"blue"`（CTkデフォルト） |

---

## コード品質方針

- `RakutenShopCollectorApp` クラスに全UIロジックを集約
- 各メソッドに日本語 docstring
- 型ヒント使用（`list[ShopInfo]`、`str | None` 等）
- `src/` 配下のファイルは一切変更しない
- `main.py`、`app.py` は変更しない

---

## requirements.txt 変更

```
customtkinter>=5.2.0   ← 追加
```

---

## README.md 変更

「GUIアプリとして使う（CustomTkinter版）」セクションを追加：
- 起動コマンド: `python app_gui.py`
- スクリーンショットプレースホルダー: `![screenshot](screenshots/gui.png)`
- `screenshots/` フォルダは `.gitignore` から除外（画像を後で追加するため）
