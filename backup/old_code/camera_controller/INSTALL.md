# カメラストリーマー WebRTC - インストール手順書

このドキュメントでは、Raspberry Pi（Debian/Raspbian系）でカメラストリーマーを動作させるために必要な**すべてのパッケージのインストール手順**を説明します。

---

## 前提条件

- **OS**: Raspberry Pi OS (Debian Bookworm 12 ベース)
- **ハードウェア**: Raspberry Pi 4/5 等、カメラモジュールまたはUSBカメラ接続
- **ユーザー**: `pi` ユーザー（または sudo 権限を持つユーザー）
- **ネットワーク**: インターネット接続が必要（apt/pip でパッケージをダウンロード）

---

## 1. システムパッケージのインストール（apt）

カメラ制御、動画処理、WebRTC 通信に必要なシステムライブラリをインストールします。

### 1.1 パッケージリストの更新

```bash
sudo apt-get update
```

### 1.2 必須パッケージのインストール

以下のコマンドで一括インストールします：

```bash
sudo apt-get install -y \
  build-essential \
  python3-dev \
  python3-venv \
  python3-pip \
  pkg-config \
  cmake \
  git \
  libssl-dev \
  libffi-dev \
  libavcodec-dev \
  libavformat-dev \
  libavdevice-dev \
  libavutil-dev \
  libavfilter-dev \
  libswscale-dev \
  libopus-dev \
  libvpx-dev \
  libsrtp2-dev \
  libasound2-dev \
  libpulse-dev \
  v4l-utils \
  ffmpeg
```

**パッケージの役割説明**:
- `build-essential`, `python3-dev`, `cmake`, `pkg-config`: C/C++ ビルドツール、Python拡張モジュールのコンパイルに必要
- `python3-venv`, `python3-pip`: Python 仮想環境とパッケージマネージャ
- `libssl-dev`, `libffi-dev`: 暗号化・SSL通信
- `libavcodec-dev`, `libavformat-dev`, `libavdevice-dev`, `libavutil-dev`, `libavfilter-dev`, `libswscale-dev`: FFmpeg ライブラリ（動画コーデック、フォーマット変換）
- `libopus-dev`, `libvpx-dev`, `libsrtp2-dev`: WebRTC で使われる音声・映像コーデックと暗号化
- `libasound2-dev`, `libpulse-dev`: 音声入出力（マイク・スピーカー制御、今回は主にビルド依存）
- `v4l-utils`: Video4Linux デバイス制御ツール（カメラ設定確認に使用）
- `ffmpeg`: FFmpeg コマンドラインツール（動画処理・変換）

### 1.3 インストール確認

```bash
# バージョン確認（例）
ffmpeg -version | head -n 1
v4l2-ctl --version
python3 --version
cmake --version
```

---

## 2. Python 仮想環境のセットアップ

プロジェクト用の独立したPython環境を作成します。

### 2.1 プロジェクトディレクトリに移動

```bash
cd /home/pi/assembly/assembly
```

### 2.2 仮想環境の作成（既に存在する場合はスキップ）

```bash
python3 -m venv assembly_env
```

### 2.3 仮想環境の有効化

```bash
source assembly_env/bin/activate
```

有効化後、プロンプトに `(assembly_env)` と表示されます。

---

## 3. Python パッケージのインストール（pip）

仮想環境内で必要な Python ライブラリをインストールします。

### 3.1 pip のアップグレード（推奨）

```bash
pip install --upgrade pip setuptools wheel
```

### 3.2 requirements.txt からインストール

プロジェクトルートの `requirements.txt` を使います：

```bash
pip install -r requirements.txt
```

**requirements.txt の内容（参考）**:
```
opencv-python-headless
aiortc
av
aiohttp
numpy
```

### 3.3 個別インストール（requirements.txt がない場合）

```bash
pip install opencv-python-headless aiortc av aiohttp numpy
```

**各パッケージの役割**:
- `opencv-python-headless`: OpenCV（画像処理・カメラ制御）GUI なし版
- `aiortc`: WebRTC 実装（Python）
- `av`: PyAV（FFmpeg の Python バインディング）
- `aiohttp`: 非同期 HTTP サーバー（WebRTC シグナリング用）
- `numpy`: 数値計算ライブラリ（画像データ処理）

### 3.4 インストール確認

```bash
python3 -c "
import importlib
modules = ['aiohttp', 'aiortc', 'av', 'cv2', 'numpy']
for m in modules:
    mod = importlib.import_module(m)
    ver = getattr(mod, '__version__', 'N/A')
    print(f'{m}: {ver}')
"
```

**期待される出力例**:
```
aiohttp: 3.13.1
aiortc: 1.14.0
av: 16.0.1
cv2: 4.12.0
numpy: 2.2.6
```

---

## 4. カメラデバイスの確認

USB カメラまたは Raspberry Pi カメラモジュールが認識されているか確認します。

### 4.1 デバイス一覧の確認

```bash
ls -la /dev/video*
```

**期待される出力例**:
```
crw-rw-rw-+ 1 root video 81, 14 Oct 29 09:08 /dev/video0
crw-rw-rw-+ 1 root video 81, 15 Oct 29 09:08 /dev/video1
...
```

通常は `/dev/video0` がメインカメラです。

### 4.2 カメラ情報・設定の確認

```bash
v4l2-ctl -d /dev/video0 --all
```

解像度・フォーマット・コントロール可能なパラメータが表示されます。

### 4.3 カメラ設定パラメータの確認

```bash
v4l2-ctl -d /dev/video0 -L
```

Brightness, Contrast, Saturation, Hue などの設定可能範囲が表示されます。

---

## 5. 動作確認

### 5.1 プロジェクトディレクトリに移動

```bash
cd /home/pi/assembly/assembly/src/camera_controller
```

### 5.2 サーバーの起動（フォアグラウンド、テスト実行）

```bash
/home/pi/assembly/assembly/assembly_env/bin/python3 CameraStreamer.py \
  --webrtc \
  --device 0 \
  --width 640 \
  --height 480 \
  --webrtc-port 8080
```

**期待される出力**:
```
Starting WebRTC server on http://0.0.0.0:8080 — open this URL in a browser to view the stream
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

### 5.3 HTTP エンドポイントの確認

別のターミナルで実行：

```bash
curl -s http://localhost:8080/settings | head -c 200
```

JSON レスポンス（カメラ情報）が返ってくれば成功です。

### 5.4 ブラウザでアクセス

Raspberry Pi の IP アドレスを確認：

```bash
hostname -I | awk '{print $1}'
```

ブラウザで以下にアクセス：
```
http://<RaspberryPiのIPアドレス>:8080
```

例: `http://10.32.77.150:8080`

**▶ Start Stream** ボタンをクリックして映像が表示されれば成功です。

### 5.5 サーバーの停止

フォアグラウンド実行の場合は `Ctrl+C` で停止。

バックグラウンド実行の場合：

```bash
pkill -f CameraStreamer.py
```

---

## 6. トラブルシューティング

### 6.1 `ModuleNotFoundError: No module named 'aiohttp'` などのエラー

→ 仮想環境が有効化されていない、または pip install が失敗しています。

**対処**:
```bash
source /home/pi/assembly/assembly/assembly_env/bin/activate
pip install -r requirements.txt
```

### 6.2 `cv2.error: ...: Can't open camera by index`

→ カメラデバイスが認識されていない、または別のプロセスが使用中です。

**対処**:
```bash
# デバイス確認
ls -la /dev/video*
v4l2-ctl -d /dev/video0 --all

# 他のプロセスがカメラを使っていないか確認
lsof /dev/video0
```

### 6.3 `ERROR: Failed building wheel for av` などビルドエラー

→ システムライブラリが不足しています。

**対処**:
```bash
sudo apt-get install -y libavcodec-dev libavformat-dev libavdevice-dev libavutil-dev
pip install --upgrade pip setuptools wheel
pip install av --no-cache-dir
```

### 6.4 WebRTC 接続がタイムアウト・映像が表示されない

→ ファイアウォール、ネットワーク設定、または STUN/TURN サーバー設定の問題です。

**対処**:
- ポート 8080 が開いているか確認（ファイアウォール設定）
- ローカルネットワーク内から接続しているか確認
- ブラウザの開発者ツール（F12）でエラーログを確認

---

## 7. 本番環境での運用（systemd サービス化）

常時起動・自動再起動させる場合は systemd サービスとして登録します。

### 7.1 サービスユニットファイルの作成

```bash
sudo nano /etc/systemd/system/camera_streamer.service
```

以下の内容を貼り付け：

```ini
[Unit]
Description=CameraStreamer WebRTC service
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/assembly/assembly/src/camera_controller
ExecStart=/home/pi/assembly/assembly/assembly_env/bin/python3 CameraStreamer.py --webrtc --device 0 --width 640 --height 480 --webrtc-port 8080
Restart=on-failure
RestartSec=3
StandardOutput=file:/home/pi/assembly/assembly/src/camera_controller/server.log
StandardError=file:/home/pi/assembly/assembly/src/camera_controller/server.err

[Install]
WantedBy=multi-user.target
```

### 7.2 サービスの有効化・起動

```bash
sudo systemctl daemon-reload
sudo systemctl enable camera_streamer
sudo systemctl start camera_streamer
sudo systemctl status camera_streamer
```

### 7.3 ログ確認

```bash
sudo journalctl -u camera_streamer -f
```

または：

```bash
tail -f /home/pi/assembly/assembly/src/camera_controller/server.log
```

---

## 8. まとめ

インストール手順の全体フロー：

1. **システムパッケージのインストール** (`apt-get install`)
2. **Python 仮想環境の作成** (`python3 -m venv`)
3. **Python パッケージのインストール** (`pip install`)
4. **カメラデバイスの確認** (`ls /dev/video*`, `v4l2-ctl`)
5. **動作確認** (サーバー起動 → ブラウザアクセス)
6. **本番運用** (systemd サービス化)

これで Raspberry Pi 上で WebRTC カメラストリーマーが動作します。

---

**作成日**: 2025-10-29  
**対象環境**: Raspberry Pi OS (Debian Bookworm 12)  
**プロジェクト**: /home/pi/assembly/assembly/src/camera_controller
