# Rakuten Shop Collector

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Development-orange)

楽天市場から指定条件に合致するショップ情報を収集し、CSV / Excel / Googleスプレッドシート形式で出力するPythonツールです。  
**ブラウザGUI版**（Streamlit）と**CLIコマンド版**の両方に対応しています。

---

## 概要

**Rakuten Shop Collector** は、楽天市場の公式商品検索APIを利用して、カテゴリIDまたはキーワードで絞り込んだ商品群からショップ情報を抽出するツールです。

マーケティングリサーチや競合調査、出品ショップのリスト作成など、楽天市場に関する業務を効率化することを目的としています。取得した情報は CSV・Excel・Googleスプレッドシートのいずれかの形式で出力でき、後続の分析ツールにそのまま連携できます。

---

## 特徴

- **2026年2月リニューアル後の新API対応**  
  2026年2月リニューアル後の新API（openapi.rakuten.co.jp）に対応。旧エンドポイント（app.rakuten.co.jp）は2026年5月13日で完全停止のため、本ツールは新APIのみを使用します。

- **公式APIを使用した安定した収集**  
  楽天市場の公式商品検索APIを使用するため、スクレイピングと異なり利用規約の範囲内で安定してデータを取得できます。

- **重複排除によるクリーンなショップリスト**  
  同一ショップの複数商品が検索結果に含まれる場合でも、ショップ単位に集約して重複のないリストを生成します。

- **3種類の出力形式に対応**  
  CSV・Excel（.xlsx）・Googleスプレッドシートから用途に応じて出力先を選択できます。Excel出力ではシートの書式設定も自動で行います。

- **APIレート制限への配慮**  
  楽天APIの利用制限（1秒1リクエスト程度）に合わせたウェイト処理を実装しており、制限超過によるエラーを回避します。

- **設定ファイルとCLI引数の両対応**  
  `config.yaml` による設定管理とコマンドライン引数の両方をサポートし、定期バッチ実行から都度実行まで柔軟に対応します。

---

## 必要な準備

### 1. Python 3.10以上のインストール

[Python公式サイト](https://www.python.org/downloads/) からインストールしてください。

```bash
python --version  # 3.10.x 以上であることを確認
```

### 2. 楽天APIキーの取得

1. [楽天デベロッパー](https://webservice.rakuten.co.jp/) に楽天会員でログイン
2. 「**+アプリID発行**」をクリック
3. アプリ名・アプリURL（GitHubリポジトリURL等）を入力
4. アプリケーションタイプ：**Webアプリケーション** を選択
5. 許可されたWebサイト：**`github.com`** を登録（Refererとして使用するドメイン）
6. データ利用目的・予想QPS（**1 推奨**）を入力
7. APIアクセススコープ：**楽天市場API** にチェック
8. 画像認証を入力 → 「規約に同意して新規アプリを作成」をクリック
9. アプリ一覧から **applicationId**（UUID形式）と **accessKey**（目のアイコンで表示）の**両方**を控えておく

> **注意：** 楽天APIの利用には楽天会員登録が必要です。新APIでは `applicationId` と `accessKey` の**両方**が必須です。[楽天ウェブサービス利用規約](https://webservice.rakuten.co.jp/terms/) を必ず確認してください。

### 3. Googleスプレッドシート出力を使用する場合（任意）

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. Google Sheets API と Google Drive API を有効化
3. サービスアカウントを作成し、JSONキーファイルをダウンロード
4. 出力先スプレッドシートにサービスアカウントのメールアドレスを編集者として共有

---

## インストール手順

```bash
# リポジトリをクローン
git clone https://github.com/your-username/rakuten-shop-collector.git
cd rakuten-shop-collector

# 仮想環境を作成・有効化（推奨）
python -m venv .venv
source .venv/bin/activate        # Linux / Mac
.venv\Scripts\activate           # Windows

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数ファイルを設定
cp .env.example .env
```

`.env` ファイルを開き、取得した楽天APIキーを設定してください：

```dotenv
RAKUTEN_APP_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx    # applicationId（UUID形式）
RAKUTEN_ACCESS_KEY=your_access_key_here                 # accessKey
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/credentials.json   # スプレッドシート使用時のみ
```

> **Refererヘッダーについて：** 新APIはリクエスト時に `Referer` ヘッダーが必須です。本ツールは自動的に `Referer: https://github.com/` を送信します。楽天デベロッパーコンソールで「許可されたWebサイト」に登録したドメインと一致している必要があります。

---

## 使用方法

### GUIアプリとして使う（CustomTkinter版）

ブラウザ不要のネイティブデスクトップGUIアプリです。

```bash
python app_gui.py
```

![screenshot](screenshots/gui.png)

**画面構成：**
- キーワードまたはカテゴリIDで検索
- 取得件数スライダー（30〜500件、10刻み）
- 結果テーブルでショップ一覧を確認（ショップ名・商品数・レビュー等）
- CSV / Excel / 両方をワンクリックで保存
- ライト/ダークテーマ切替対応

**初回起動時の注意：**
- `.env` に `RAKUTEN_APP_ID` と `RAKUTEN_ACCESS_KEY` が設定されていない場合、起動時に警告ダイアログが表示され検索ボタンが無効になります。
- `.env.example` をコピーして `.env` を作成し、APIキーを設定してから起動してください。

---

### GUI版（Streamlit）

ブラウザ上で設定・実行・ダウンロードをすべて行えるGUIモードです。

```bash
streamlit run app.py
```

ブラウザが自動で開き `http://localhost:8501` にアクセスします。

**画面構成：**

```
┌─────────────────────────────────────────────────────────────┐
│  サイドバー           │  メインエリア                        │
│  ─────────────────   │  ─────────────────────────────────── │
│  検索方法ラジオ       │  [🔍 検索実行] ボタン                │
│  キーワード入力       │  プログレスバー                      │
│  取得件数スライダー   │  結果テーブル（st.dataframe）         │
│                      │  [📥 CSV] [📥 Excel] ダウンロード     │
│                      │  分析グラフ（レビュー分布/商品数）    │
└─────────────────────────────────────────────────────────────┘
```

> **スクリーンショット：** `docs/screenshots/` に配置予定（起動後にキャプチャしてください）

---

### CLIコマンド版

### 基本コマンド

```bash
# キーワードで検索（CSV出力）
python main.py --keyword "ワイヤレスイヤホン" --count 100 --output csv

# カテゴリIDで検索（Excel出力）
python main.py --category-id 100371 --count 200 --output excel

# Googleスプレッドシートに出力
python main.py --keyword "コーヒー豆" --count 50 --output gsheet --sheet-id YOUR_SPREADSHEET_ID

# 出力ファイル名を指定
python main.py --keyword "財布" --count 100 --output csv --filename shops_wallet
```

### コマンドライン引数一覧

| 引数 | 説明 | 例 |
|------|------|-----|
| `--keyword` | 検索キーワード | `"ワイヤレスイヤホン"` |
| `--category-id` | 楽天カテゴリID | `100371` |
| `--count` | 取得する商品数（最大1000） | `100` |
| `--output` | 出力形式 `csv` / `excel` / `gsheet` | `csv` |
| `--filename` | 出力ファイル名（拡張子不要） | `shops_result` |
| `--sheet-id` | GoogleスプレッドシートID | `1BxiMV...` |
| `--config` | 設定ファイルのパス | `config.yaml` |
| `--log-level` | ログレベル `DEBUG` / `INFO` / `WARNING` | `INFO` |

### config.yaml による設定

`config.yaml.example` をコピーして使用します：

```bash
cp config.yaml.example config.yaml
```

```yaml
# config.yaml
search:
  keyword: "ワイヤレスイヤホン"
  category_id: null          # keyword と category_id はどちらか一方を指定
  count: 200

output:
  format: excel              # csv / excel / gsheet
  filename: shops_result
  sheet_id: null             # gsheet 使用時はスプレッドシートIDを指定

api:
  wait_seconds: 1.0          # APIリクエスト間隔（秒）
  max_retries: 3             # 失敗時のリトライ回数

logging:
  level: INFO
  file: logs/rakuten_collector.log
```

設定ファイルを使用した実行：

```bash
python main.py --config config.yaml
```

---

## 出力サンプル

### CSV / Excel 出力カラム構成

| ショップID | ショップ名 | ショップURL | 運営会社名 | 取扱カテゴリ | 商品数 |
|-----------|-----------|-----------|-----------|------------|--------|
| example-shop | サンプルショップ | https://www.rakuten.co.jp/example-shop/ | 株式会社サンプル | 家電、スマホ | 342 |
| audio-store | オーディオストア | https://www.rakuten.co.jp/audio-store/ | オーディオ株式会社 | 音響機器 | 128 |
| gadget-land | ガジェットランド | https://www.rakuten.co.jp/gadget-land/ | ガジェット合同会社 | 家電、PC周辺 | 891 |

### ファイル出力先

| 出力形式 | 保存先 |
|---------|--------|
| CSV | `output/shops_YYYYMMDD_HHMMSS.csv` |
| Excel | `output/shops_YYYYMMDD_HHMMSS.xlsx` |
| Googleスプレッドシート | 指定のスプレッドシートの `shops` シート |

---

## プロジェクト構成

```
rakuten-shop-collector/
├── README.md
├── requirements.txt          # 依存パッケージ一覧
├── .env.example              # 環境変数テンプレート
├── .gitignore
├── config.yaml.example       # 設定ファイルテンプレート
├── app_gui.py                # CustomTkinter GUIエントリーポイント
├── app.py                    # Streamlit GUIエントリーポイント
├── main.py                   # CLIエントリーポイント
├── src/
│   ├── __init__.py
│   ├── api_client.py         # 楽天API通信処理
│   ├── shop_extractor.py     # 商品データからショップ情報を抽出
│   ├── output_writer.py      # CSV / Excel / Gsheet への書き出し
│   └── utils.py              # ロギング・共通ユーティリティ
└── tests/
    └── test_basic.py         # 基本動作テスト
```

---

## 動作確認済み環境

| 項目 | バージョン |
|------|-----------|
| Python | 3.10 / 3.11 / 3.12 |
| OS | Windows 10/11、macOS 13+、Ubuntu 22.04 |

---

## トラブルシューティング

新APIで発生しやすいエラーと対処法をまとめます。

| エラー | 原因 | 対処法 |
|--------|------|--------|
| `REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING` (403) | Refererヘッダーが未設定 | `Referer: https://github.com/` をリクエストヘッダーに含める |
| `specify valid applicationId` / `wrong_parameter` | 旧APIエンドポイントを使用している | エンドポイントを `openapi.rakuten.co.jp` に変更する |
| `accessKey must be present` | `.env` に `RAKUTEN_ACCESS_KEY` が未設定 | `.env` に `RAKUTEN_ACCESS_KEY=...` を追加する |
| `401 Unauthorized` | `applicationId` または `accessKey` が間違っている | 楽天デベロッパーコンソールで両方の値を再確認する |

---

## ライセンス

本プロジェクトは [MIT License](LICENSE) のもとで公開されています。

楽天APIの利用に際しては、[楽天ウェブサービス利用規約](https://webservice.rakuten.co.jp/terms/) に従ってください。

---

## 今後の拡張予定

- [ ] **ショップレビュー情報の収集**  
  ショップ評価スコアやレビュー件数を取得してリストに追加
- [ ] **定期実行・差分更新機能**  
  前回取得結果との差分のみを更新し、変更履歴を記録
- [ ] **複数キーワードの一括処理**  
  キーワードリストを読み込んで一度に複数検索を実行
- [x] **GUIモード**  
  StreamlitによるブラウザGUIを追加済み（`streamlit run app.py`）
- [ ] **他モールへの対応**  
  Yahoo!ショッピング・Amazon等への収集対象の拡張
