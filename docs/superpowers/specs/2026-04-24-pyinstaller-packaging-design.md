# Design Spec: PyInstaller パッケージング（Windows 単体配布用 .exe）

**Date:** 2026-04-24  
**Branch:** feature/exe-ready  
**Scope:** `assets/`・`app_gui.spec`・`build.bat`・`.gitignore`・`README.md` のみ変更（`src/`・`main.py`・`app.py`・テストは変更しない）

---

## 背景・目的

`feature/exe-ready` ブランチで APIキー入力画面を追加し、非技術者ユーザーが `.env` 不要で
アプリを使えるようになった。次のステップとして、Python 環境を持たないユーザーへ
単一 `.exe` ファイルとして配布できるようにする。

---

## アーキテクチャ概要

**アプローチ A（手書き `.spec` + `build.bat`）を採用**

- PyInstaller の手書き `.spec` で `customtkinter` テーマ JSON を明示的に同梱
- `build.bat` が クリーン → アイコン生成 → ビルド の 3 ステップを自動化
- 出力: `dist\RakutenShopCollector.exe`（単一ファイル、`--onefile`）

---

## ファイル変更一覧

| ファイル | 種別 | 内容 |
|---------|------|------|
| `assets/generate_icon.py` | 新規 | Pillow で `assets/icon.ico` を生成するスクリプト |
| `assets/icon.ico` | 新規（生成物） | 複数サイズ内包の .ico（Git 管理対象） |
| `app_gui.spec` | 新規 | PyInstaller spec ファイル |
| `build.bat` | 新規 | ビルド自動化バッチスクリプト |
| `README.md` | 変更 | 「配布用 .exe の作り方」セクション追加 |
| `.gitignore` | 変更 | `*.spec` 行をコメントアウトして `app_gui.spec` を管理対象に |
| `src/`・`main.py`・`app.py`・テスト | 変更なし | 一切触れない |

---

## アイコン生成（`assets/generate_icon.py`）

Pillow で 256×256 のビットマップを生成し、複数サイズ（16, 32, 48, 64, 128, 256px）を
内包した `.ico` ファイルとして `assets/icon.ico` に保存する。

**デザイン:**
- 背景: 楽天カラー（`#BF0000`）の角丸矩形
- 中央: 白い「R」文字（太字）

スクリプトは `build.bat` から自動実行されるが、`python assets\generate_icon.py` で
単独実行・再生成も可能。既存の `assets/icon.ico` がある場合は上書き。

---

## `app_gui.spec` の構成

```python
import sys
from pathlib import Path
import customtkinter

a = Analysis(
    ['app_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        # customtkinter のテーマ JSON・フォントを同梱（必須）
        (str(Path(customtkinter.__file__).parent), 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL._tkinter_finder',
    ],
    excludes=[
        'streamlit', 'gspread', 'google.auth',
        'yaml', 'pytest',
    ],
    ...
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RakutenShopCollector',
    icon='assets/icon.ico',
    onefile=True,
    console=False,
    ...
)
```

**重要ポイント:**
- `console=False`: GUI アプリなのでコンソールウィンドウを非表示
- `onefile=True`: 単一 .exe として出力
- `excludes`: streamlit・gspread・google-auth・pyyaml・pytest を除外してサイズ削減
- `customtkinter` の `datas`: テーマ JSON ファイルを同梱しないと起動時クラッシュする

---

## `build.bat` の内容

```bat
@echo off
chcp 65001 > nul
echo ============================================
echo  Rakuten Shop Collector - ビルドスクリプト
echo ============================================
echo.

REM --- クリーンアップ ---
echo [1/3] 既存のビルドフォルダを削除中...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
echo       完了

REM --- アイコン生成 ---
echo [2/3] アイコンを生成中...
python assets\generate_icon.py
if errorlevel 1 (
    echo [ERROR] アイコン生成に失敗しました
    pause & exit /b 1
)
echo       完了

REM --- PyInstaller ビルド ---
echo [3/3] .exe をビルド中（5〜15分かかる場合があります）...
pyinstaller app_gui.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] ビルドに失敗しました。上記のエラーを確認してください。
    pause & exit /b 1
)

echo.
echo ============================================
echo  ビルド成功！
echo  dist\RakutenShopCollector.exe を配布できます
echo ============================================
pause
```

---

## README 追加セクション

「配布用 .exe の作り方（Windows）」セクションを追加：

- 必要環境（Python 3.11+・PyInstaller・Pillow）
- ビルド手順（build.bat の実行 → dist\ に .exe 生成）
- 配布方法（.exe 1ファイルのみ）
- 注意事項テーブル：

| 項目 | 内容 |
|------|------|
| ビルド時間 | 初回は 5〜15分かかる場合がある |
| ファイルサイズ | 約 30〜50 MB |
| Windows SmartScreen | 「詳細情報」→「実行」で起動可能 |
| customtkinter テーマ | .spec の datas で明示的に同梱済み |

---

## エラーハンドリング

| 状況 | 対応 |
|------|------|
| Pillow 未インストール | generate_icon.py がエラー → build.bat が `[ERROR]` 表示して停止 |
| PyInstaller 未インストール | pyinstaller コマンドがエラー → build.bat が `[ERROR]` 表示して停止 |
| customtkinter テーマ欠落 | .spec の datas で明示的に解決済み |
| AV 誤検知（SmartScreen） | README に手順を記載 |
