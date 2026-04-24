# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import customtkinter

a = Analysis(
    ['app_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # customtkinter のテーマ JSON・フォントを同梱（必須）
        # 欠落すると「FileNotFoundError: theme ... not found」で起動クラッシュ
        (str(Path(customtkinter.__file__).parent), 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL._tkinter_finder',  # Pillow + Tkinter 連携に必要
        'dotenv',               # python-dotenv: import name differs from package name
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'streamlit',
        'gspread',
        'google.auth',
        'google.oauth2',
        'yaml',
        'pytest',
        '_pytest',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RakutenShopCollector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
