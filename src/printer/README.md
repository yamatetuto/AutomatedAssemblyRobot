# 3Dプリンターサービス

## 概要
`src/printer` は OctoPrint ベースの 3D プリンター制御を担当するサービス層です。クラウド/ローカル上の OctoPrint REST API と非同期通信し、造形ステータス監視・温度取得・一時停止/再開・キャンセル・マクロ実行・E-STOP などの高レベル操作を提供します。

## ディレクトリ構成
| ファイル | 役割 |
| --- | --- |
| `octoprint_client.py` | OctoPrint REST API を直接叩く非同期 HTTP クライアント。認証ヘッダー付与、タイムアウト、リクエスト組み立てを担当。 |
| `printer_manager.py` | 上記クライアントをラップし、監視ループ・状態キャッシュ・ジョブ制御 API をまとめるサービスクラス。 |
| `__init__.py` | サービス公開用のエクスポート定義。 |

## 主な依存関係
- `aiohttp` 3.9+ : OctoPrint との非同期 HTTP 通信に使用。
- Python 標準 `asyncio` : 監視ループとロック制御で利用。

※ プロジェクト全体の `requirements.txt` / `setup.py` に含まれているため個別追加は不要です。

## 環境変数 (設定)
FastAPI 側から本サービスを有効化するには以下の環境変数を設定します。

| 変数名 | 必須 | 説明 |
| --- | --- | --- |
| `OCTOPRINT_URL` | ✅ | OctoPrint ホストのベース URL (例: `http://10.0.0.5:5000`). |
| `OCTOPRINT_API_KEY` | ✅ | OctoPrint の API Key。`Settings > API` で発行。 |
| `OCTOPRINT_POLL_INTERVAL` | 任意 | 監視ループのポーリング周期(秒)。既定値は `5.0` 秒。 |

FastAPI (`app.py`) のライフサイクルでこれらが検出されると `PrinterManager` が自動起動します。未設定の場合はサービスをスキップし、UI には「OctoPrintサービスが無効」と表示されます。

## 機能サマリ
- **ステータス監視**: `/api/printer/status` から進捗・ETA・温度・状態メッセージを返却。
- **制御系エンドポイント**: `/api/printer/pause`・`/api/printer/resume` を通じてジョブの一時停止/再開をトリガー。
- **ジョブ管理**: `PrinterManager` API 経由で `start_job`, `cancel_job`, `send_command`, `estop`, `macro` 実行を提供 (必要に応じて FastAPI へ公開可能)。
- **状態キャッシュ**: 監視タスクが OctoPrint のレスポンスを `_status` に保持し、UI からの頻繁なポーリングでも API 呼び出し回数を抑制。

## 使い方
1. OctoPrint 側で API Key を発行し、Raspberry Pi から到達できることを確認します。
2. 環境変数を設定しアプリを起動:
   ```bash
   export OCTOPRINT_URL="http://10.32.77.150:5000"
   export OCTOPRINT_API_KEY="xxxxxxxxxxxxxxxx"
   # 任意: export OCTOPRINT_POLL_INTERVAL=3.0
   python app.py
   ```
3. Web UI の真ん中カラム「3Dプリンター」パネルで進捗・温度を確認し、必要に応じて一時停止/再開ボタンを使用します。

## 開発メモ
- 構文チェック: `python -m compileall src/printer`。
- 追加の制御 API を公開したい場合は `printer_manager.py` のメソッドを FastAPI ルートにバインドしてください。
- OctoPrint 接続エラー時は `_set_offline()` が呼ばれ、UI へ警告メッセージが伝播します。ログ (`PrinterManager` ロガー) を確認すると原因を追えます。
