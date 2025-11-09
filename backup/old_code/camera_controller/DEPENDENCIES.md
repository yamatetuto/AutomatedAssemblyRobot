# Camera Controller Dependencies

このドキュメントでは、Camera Controller WebRTCストリーマーの実行に必要なすべての依存関係をまとめています。

## システム要件

- **OS**: Raspberry Pi OS (Debian-based)
- **Python**: Python 3.11以上
- **カメラ**: V4L2互換カメラ（例：USB Webカメラ、Raspberry Piカメラモジュール）

## システムパッケージ（apt）

以下のコマンドでシステムパッケージをインストールしてください：

```bash
sudo apt update
sudo apt install -y \
    python3-pip \
    python3-dev \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    libopus-dev \
    libvpx-dev \
    libsrtp2-dev \
    pkg-config \
    v4l-utils \
    ffmpeg
```

### パッケージの説明

- **libav*** - FFmpeg/libav ライブラリ（動画エンコード/デコード）
- **libopus-dev** - Opus音声コーデックライブラリ
- **libvpx-dev** - VP8/VP9動画コーデックライブラリ
- **libsrtp2-dev** - Secure Real-time Transport Protocol
- **v4l-utils** - Video4Linux2ユーティリティ（v4l2-ctlコマンド）
- **ffmpeg** - マルチメディアフレームワーク
- **pkg-config** - ライブラリの検索/設定ツール

## Pythonパッケージ（pip）

### インストール方法

システム全体にインストール（推奨）:

```bash
sudo pip3 install --break-system-packages \
    aiortc \
    aiohttp \
    opencv-python \
    av \
    numpy
```

または仮想環境を使用:

```bash
python3 -m venv venv
source venv/bin/activate
pip install aiortc aiohttp opencv-python av numpy
```

### パッケージの説明

#### 必須パッケージ

1. **aiortc** (1.14.0以上)
   - WebRTCプロトコル実装
   - ブラウザとのリアルタイム通信

2. **aiohttp** (3.13.1以上)
   - 非同期HTTPサーバー
   - WebRTCシグナリング用

3. **opencv-python** (cv2)
   - カメラキャプチャ
   - 画像処理
   - V4L2との連携

4. **av** (PyAV 16.0.1以上)
   - FFmpegのPythonバインディング
   - 動画フレーム処理

5. **numpy**
   - 数値計算
   - 画像データ配列処理

#### 依存パッケージ（自動インストール）

- **aiosignal** - 非同期シグナル処理
- **attrs** - クラス定義ユーティリティ
- **certifi** - SSL証明書
- **cffi** - C言語外部関数インターフェース
- **cryptography** - 暗号化ライブラリ
- **aiohappyeyeballs** - 非同期DNS解決
- **aioice** - ICE（Interactive Connectivity Establishment）
- **cachetools** - キャッシュツール
- **charset-normalizer** - 文字エンコーディング検出

## インストール確認

すべてのパッケージが正しくインストールされているか確認:

```bash
python3 -c "import aiortc, av, cv2, aiohttp, numpy; print('All packages imported successfully!')"
```

V4L2ユーティリティの確認:

```bash
v4l2-ctl --version
v4l2-ctl --list-devices
```

## トラブルシューティング

### エラー: `ModuleNotFoundError: No module named 'aiortc'`

システム全体にインストールする場合:

```bash
sudo pip3 install --break-system-packages aiortc
```

### エラー: `ERROR: Could not build wheels for av`

libav開発パッケージをインストール:

```bash
sudo apt install -y libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev
```

### エラー: `/dev/video0: Device or resource busy`

カメラを使用している他のプロセスを終了:

```bash
sudo fuser -k /dev/video0
```

または、他のプロセスを確認:

```bash
sudo lsof /dev/video0
```

### エラー: `ImportError: libopus.so.0: cannot open shared object file`

Opusライブラリをインストール:

```bash
sudo apt install -y libopus-dev libopus0
```

## 実行方法

### 基本的な起動

```bash
cd /home/pi/assembly/assembly/src/camera_controller
python3 CameraStreamer.py --webrtc --device 0
```

### オプション指定

```bash
python3 CameraStreamer.py --webrtc --device 0 --width 1280 --height 720 --webrtc-port 8080
```

### ブラウザでアクセス

```
http://<Raspberry PiのIPアドレス>:8080
```

## 機能

### 実装済み機能

1. **WebRTCストリーミング**
   - リアルタイム動画配信
   - ブラウザから視聴可能

2. **カメラ設定の変更**
   - 解像度、FPS、コーデック（MJPG/YUYV）
   - V4L2コントロール（brightness、contrast、saturation、hue、gain、exposure、等）
   - メニュー型コントロール（auto_exposure、power_line_frequencyなど）
   - ブール型コントロール（white_balance_automatic、focus_automatic_continuousなど）

3. **スナップショット撮影**
   - Raspberry Piのカメラから直接高品質画像を取得
   - `snapshots/`フォルダに保存

4. **Ctrl+C対応**
   - グレースフルシャットダウン
   - リソースの適切な解放

5. **オンデマンドカメラオープン**
   - クライアント接続時のみカメラを使用
   - アイドル時はリソースを解放

## ファイル構成

```
assembly/src/camera_controller/
├── CameraStreamer.py          # メインエントリーポイント
├── webrtc_index.html          # ブラウザUI
├── webrtc/
│   ├── __init__.py
│   └── streamer.py            # WebRTCサーバー実装
├── capture/
│   ├── __init__.py
│   └── opencv.py
├── processor/
│   ├── __init__.py
│   └── processors.py
├── snapshots/                 # スナップショット保存先（自動作成）
├── INSTALL.md                 # インストール手順
├── README_UPDATES.md          # 更新履歴
└── DEPENDENCIES.md            # このファイル
```

## 参考情報

- **aiortc公式ドキュメント**: https://aiortc.readthedocs.io/
- **aiohttp公式ドキュメント**: https://docs.aiohttp.org/
- **OpenCV公式ドキュメント**: https://docs.opencv.org/
- **V4L2仕様**: https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html
- **WebRTC仕様**: https://www.w3.org/TR/webrtc/

## 更新履歴

- **2025-10-29**: 
  - メニューコントロールの選択肢表示対応（v4l2-ctl -L使用）
  - Ctrl+C対応（グレースフルシャットダウン）
  - 全カメラパラメータの動的表示＆変更対応
  - スナップショット機能（高品質画像保存）
  - オンデマンドカメラオープン対応

## ライセンス

このプロジェクトは、使用しているライブラリのライセンスに従います。
