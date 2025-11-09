# 🤖 AutomatedAssemblyRobot

積層型3Dプリンター、ディスペンサー、XYZ直交ロボットを組み合わせた医療機器の自動組立システム

---

## 📋 プロジェクト概要

本プロジェクトは、以下のデバイスを統合制御し、医療機器の自動組立を実現するシステムです:

- **3Dプリンター** (Tronxy GEMINI S) - OctoPrint経由で制御
- **XYZ直交ロボット** (株式会社コスモスウェブ製) - 企業ライブラリで制御
- **電動グリッパー** (IAI社 RCP2-GRSS) - Modbus RTU通信
- **ディスペンサー** - Raspberry Pi GPIO制御
- **カメラ** - OpenCV + WebRTC

---

## 🎯 主要機能

### ✅ 実装済み
- [x] **WebRTCリアルタイムストリーミング** - 低遅延カメラ映像配信
- [x] **グリッパー制御** (Modbus RTU) - 位置決め、把持、サーボ制御
- [x] **ポジションテーブル管理** - 64ポジションのパラメータ設定
- [x] **カメラパラメータ調整** - 明るさ、コントラスト、露出、フォーカス等
- [x] **スナップショット撮影** - タイムスタンプ付き画像保存
- [x] **統合Web UI** - FastAPI + WebRTC対応制御画面
- [x] **非ブロッキング制御** - カメラ映像を止めないグリッパー操作

### 🚧 実装中
- [ ] 3Dプリンター制御 (OctoPrint API)
- [ ] ディスペンサー制御 (GPIO)
- [ ] 画像処理・物体検出
- [ ] ロボットアーム統合
- [ ] 自動組立シーケンス

---

## 🏗️ ディレクトリ構造

```
AutomatedAssemblyRobot/
├── camera_controller/          # カメラ・画像処理
│   ├── CameraStreamer.py      # スタンドアロン版ストリーミング
│   ├── webrtc/                # WebRTCストリーミング実装
│   ├── capture/               # カメラキャプチャ
│   └── processor/             # 画像処理アルゴリズム
├── gripper_controller/        # グリッパー制御 (IAI CON)
│   └── CONController.py       # Modbus RTU通信制御
├── web_app/                   # 統合Webアプリケーション
│   ├── main_webrtc_fixed.py   # FastAPIサーバー（メイン）
│   └── templates/             # HTMLテンプレート
│       └── index_webrtc_fixed.html  # Web UI (v1.6)
├── snapshots/                 # スナップショット保存先
├── config/                    # 設定ファイル
├── sequences/                 # 組立シーケンス定義
├── docs/                      # ドキュメント
│   ├── reports/               # 調査レポート
│   ├── requirements.md        # 要件定義
│   ├── schema.md              # データ構造定義
│   └── tasks.md               # 実装計画
├── tests/                     # テストコード
├── requirements.txt           # Python依存パッケージ
└── README.md                  # このファイル
```

---

## 💻 システム要件

### ハードウェア
- **Raspberry Pi 4 Model B** (4GB RAM以上推奨)
- **USBカメラ** (Logitech C920等のUVC対応カメラ)
- **IAI RCP2-GRSSグリッパー** + USB-RS485変換アダプタ
- **ネットワーク接続** (Wi-Fi/Ethernet)

### ソフトウェア
- **OS**: Raspberry Pi OS 11 (Bullseye) 以上
- **Python**: 3.9 以上
- **必須パッケージ**:
  - OpenCV 4.6+
  - FastAPI 0.100+
  - aiortc 1.6+ (WebRTC)
  - minimalmodbus 2.0+ (Modbus RTU)
  - uvicorn (ASGIサーバー)

---

## 🚀 インストール

### 1. システム準備
```bash
# システムパッケージの更新
sudo apt update && sudo apt upgrade -y

# 必須ツールのインストール
sudo apt install -y git python3-pip python3-venv v4l-utils
```

### 2. リポジトリのクローン
```bash
cd ~
git clone https://github.com/yamatetuto/AutomatedAssemblyRobot.git
cd AutomatedAssemblyRobot
```

### 3. Python依存パッケージのインストール
```bash
# システムワイドインストール（推奨）
pip3 install --break-system-packages -r requirements.txt

# または仮想環境を使用
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

### 4. デバイス接続確認
```bash
# カメラデバイスの確認
v4l2-ctl --list-devices

# グリッパー（USB-RS485）の確認
ls -l /dev/ttyUSB*

# カメラパラメータの確認
v4l2-ctl -L
```

---

## 🎮 使用方法

### Web UI起動（推奨）

統合Webアプリケーションでカメラとグリッパーを制御できます。

```bash
cd ~/AutomatedAssemblyRobot
python3 web_app/main_webrtc_fixed.py
```

**アクセス**: ブラウザで `http://<Raspberry_PiのIPアドレス>:8000` を開く

#### Web UI機能
- **📹 カメラ映像**: WebRTCによる低遅延ストリーミング
- **📸 スナップショット**: 画像キャプチャと一覧表示
- **🎛️ カメラ設定**: 
  - スライダー調整（明るさ、コントラスト、彩度、ゲイン等）
  - チェックボックス（オートホワイトバランス、オートフォーカス等）
  - セレクトボックス（露出モード、電源周波数等）
- **🤏 グリッパー制御**:
  - サーボON/OFF
  - 原点復帰
  - ポジション移動（0-63）
  - ポジションテーブル編集（位置、幅、速度、加減速、押当電流）
- **📊 ステータス表示**: 右上に現在位置とサーボ状態を常時表示

### バックグラウンド起動

サーバーをバックグラウンドで実行:

```bash
nohup python3 web_app/main_webrtc_fixed.py > /tmp/webrtc_running.log 2>&1 &
```

ログ確認:
```bash
tail -f /tmp/webrtc_running.log
```

停止:
```bash
pkill -f "python3.*main_webrtc_fixed.py"
```

### カメラのみテスト

```bash
cd camera_controller
python3 CameraStreamer.py --webrtc --device 0 --width 640 --height 480
```

### グリッパー制御テスト

```python
from gripper_controller.CONController import CONController

# グリッパー接続
gripper = CONController(port="/dev/ttyUSB0", slave_address=1, baudrate=38400)

# サーボON
gripper.servo_on()

# 原点復帰
gripper.home()

# ポジション移動
gripper.move_to_pos(5)

# 現在位置取得
status = gripper.get_status()
print(f"位置: {status['position_mm']}mm, サーボ: {status['servo_on']}")

# サーボOFF
gripper.servo_off()
gripper.close()
```

---

## ⚙️ 設定

### カメラデバイス変更

`web_app/main_webrtc_fixed.py` の先頭付近:
```python
CAMERA_DEVICE = 0  # /dev/video0 を使用
```

### グリッパー通信設定

`web_app/main_webrtc_fixed.py` の先頭付近:
```python
GRIPPER_PORT = "/dev/ttyUSB0"
GRIPPER_SLAVE_ADDRESS = 1
GRIPPER_BAUDRATE = 38400
```

### カメラ解像度・FPS

Web UI上で解像度を選択可能:
- 640x480 @ 30fps（デフォルト、低遅延）
- 1280x720 @ 30fps
- 1920x1080 @ 30fps
- 2304x1536 @ 2fps（高解像度、スナップショット向け）

---

## 🔧 トラブルシューティング

### カメラが認識されない
```bash
# デバイス確認
v4l2-ctl --list-devices

# 権限確認
ls -l /dev/video0
sudo usermod -a -G video $USER
# ログアウト・ログインが必要
```

### グリッパーが通信できない
```bash
# デバイス確認
ls -l /dev/ttyUSB*

# 権限設定
sudo usermod -a -G dialout $USER
# ログアウト・ログインが必要

# ボーレート確認（グリッパー本体の設定と合わせる）
# デフォルトは38400bps
```

### Web UIにアクセスできない
```bash
# サーバーが起動しているか確認
ps aux | grep main_webrtc_fixed

# ポート8000が使用されているか確認
sudo netstat -tulpn | grep 8000

# ファイアウォール確認（必要に応じて）
sudo ufw allow 8000
```

### カメラ映像がフリーズする
- **v1.4以降で修正済み**: グリッパー操作が非ブロッキング実行になりました
- ブラウザを `Ctrl+Shift+R` でハードリフレッシュ
- サーバーを再起動

---

## 📚 ドキュメント

詳細なドキュメントは `docs/` ディレクトリを参照:

- [要件定義書](docs/requirements.md) - システム要件
- [データスキーマ定義](docs/schema.md) - データ構造
- [実装計画](docs/tasks.md) - タスク管理
- [調査レポート](docs/reports/) - 技術調査結果

---

## �� テスト

### ユニットテストを実行
```bash
pytest tests/ -v
```

### カメラ動作確認
```bash
python3 tests/test_camera_check.py
```

---

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'feat: Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

### コミットメッセージ規約（Semantic Commits）
- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント
- `chore:` 雑務（依存関係更新など）
- `test:` テスト
- `refactor:` リファクタリング

---

## 📄 ライセンス

このプロジェクトは研究用途です。商用利用については別途相談してください。

---

## 📞 サポート

問題が発生した場合:
1. [トラブルシューティング](#-トラブルシューティング)を確認
2. [DesignDocument.md](DesignDocument.md)を参照
3. GitHubでIssueを作成

---

## 🙏 謝辞

- 株式会社コスモスウェブ - 自動組立装置の製作
- IAI社 - 電動グリッパー提供
- OpenCV、FastAPI、aiortcコミュニティ

---

## 📝 更新履歴

### v1.6 (2025-11-05)
- グリッパーステータス表示を右上に配置
- トーストメッセージ表示改善
- 非ブロッキンググリッパー制御実装

### v1.5 (2025-11-05)
- トースト表示時間延長と視認性向上

### v1.4 (2025-11-05)
- グリッパー操作の非ブロッキング化（カメラフリーズ解消）
- `asyncio.run_in_executor()`による並行実行

### v1.3 (2025-11-05)
- ポジションテーブル全パラメータ表示（横スクロール対応）
- カメラコントロールでbool/menu型対応
- チェックボックス・セレクトボックスUI追加

### v1.2 (2025-11-05)
- ポジションテーブルのパラメータ名修正
- UI表示の改善

### v1.1 (2025-11-05)
- WebRTC統合Web UI初版リリース

---

**開発状況**: 🟢 ベータ版（動作確認済み）  
**最終更新**: 2025-11-05  
**Repository**: https://github.com/yamatetuto/AutomatedAssemblyRobot
