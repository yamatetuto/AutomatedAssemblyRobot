# 自動組み立てロボット制御システム

IAI製グリッパーとWebカメラを使った自動組み立てロボットの制御システムです。

## 特徴

- 📹 **WebRTC対応**: リアルタイムカメラ映像配信
- 🤏 **グリッパー制御**: IAI製グリッパーのModbus RTU制御
- 🔧 **モジュール化設計**: 再利用可能なモジュール構造
- 🌐 **Webベース操作**: ブラウザから直感的に操作可能

## ディレクトリ構造

```
AutomatedAssemblyRobot/
├── src/                        # 再利用可能なモジュール
│   ├── camera/                 # カメラ制御モジュール
│   ├── gripper/                # グリッパー制御モジュール
│   ├── webrtc/                 # WebRTC通信モジュール
│   └── config/                 # 設定管理
├── web_app/                    # Webアプリケーション
│   ├── main_webrtc_fixed.py    # メインアプリケーション
│   ├── templates/              # HTMLテンプレート
│   └── static/                 # 静的ファイル
├── gripper_controller/         # グリッパーコントローラー
├── docs/                       # ドキュメント
│   ├── modules.md              # モジュール仕様書
│   └── ...
├── backup/                     # バックアップ
│   ├── services_backup/        # マイクロサービス実装（旧）
│   └── shared_backup/          # 共有ライブラリ（旧）
└── snapshots/                  # スナップショット保存先
```

## セットアップ

### 必要な環境

- Raspberry Pi 4 (推奨)
- Python 3.9+
- Webカメラ (C922 Pro Stream Webcam推奨)
- IAI製グリッパー

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/AutomatedAssemblyRobot.git
cd AutomatedAssemblyRobot

# 依存パッケージのインストール
pip install -r requirements.txt

# (オプション) 環境変数の設定
export CAMERA_DEVICE=0
export GRIPPER_PORT=/dev/ttyUSB0
```

## 使い方

### モジュールを使った開発

```python
import asyncio
from src import CameraManager, GripperManager, WebRTCManager

async def main():
    # カメラ初期化
    camera = CameraManager()
    await camera.start()
    
    # グリッパー初期化
    gripper = GripperManager()
    await gripper.connect()
    
    # グリッパー操作
    await gripper.servo_on()
    await gripper.home()
    await gripper.move_to_position(0)
    
    # 終了処理
    await gripper.disconnect()
    await camera.stop()

asyncio.run(main())
```

### Webアプリケーションの起動

```bash
cd web_app
python3 main_webrtc_fixed.py
```

ブラウザで `http://<Raspberry PiのIPアドレス>:8080` にアクセス

## モジュール詳細

詳細は [docs/modules.md](docs/modules.md) を参照してください。

### CameraManager

- カメラキャプチャ
- スナップショット撮影
- カメラパラメータ制御

### GripperManager

- サーボON/OFF
- 原点復帰
- ポジション移動
- ポジションテーブル管理

### WebRTCManager

- リアルタイム映像配信
- 複数クライアント対応

## ドキュメント

- [モジュール仕様書](docs/modules.md)
- [設計ドキュメント](DesignDocument.md)

## ライセンス

MIT License

## 貢献

プルリクエスト歓迎！

## 作者

Your Name
