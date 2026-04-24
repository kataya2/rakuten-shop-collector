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
    echo.
    echo [ERROR] アイコン生成に失敗しました
    echo         Pillow がインストールされているか確認してください: pip install Pillow
    pause
    exit /b 1
)
echo       完了

REM --- PyInstaller ビルド ---
echo [3/3] .exe をビルド中（5〜15分かかる場合があります）...
pyinstaller app_gui.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] ビルドに失敗しました。上記のエラーを確認してください。
    pause
    exit /b 1
)

echo.
echo ============================================
echo  ビルド成功！
echo  dist\RakutenShopCollector.exe を配布できます
echo ============================================
pause
