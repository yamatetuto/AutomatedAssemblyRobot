# パッケージ管理ドキュメント

本ドキュメントは、自動組立ロボットシステムで使用する全てのパッケージを管理します。

---

## 📦 インストール方針

1. **apt優先**: システムパッケージとして提供されているものは`apt install`を使用
2. **pipは最小限**: aptで提供されていないものや最新版が必要な場合のみ`pip3`使用
3. **--break-system-packages**: Raspberry Pi OS (Debian 11+)ではPEP 668により、システムPythonへのpip installが制限されるため、必要に応じてこのフラグを使用

---

## 🐧 システムパッケージ (apt install)

### 必須パッケージ

#### Python関連
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

| パッケージ | バージョン | 用途 |
|-----------|----------|------|
| python3 | 3.11.x | Python本体 |
| python3-pip | 23.x | Pythonパッケージマネージャー |
| python3-venv | 3.11.x | 仮想環境作成 (オプション) |

#### カメラ・OpenCV関連
```bash
sudo apt install -y python3-opencv v4l-utils
```

| パッケージ | バージョン | 用途 |
|-----------|----------|------|
| python3-opencv | 4.6.0+dfsg-12 | OpenCV Pythonバインディング |
| libopencv-core406 | 4.6.0+dfsg-12 | OpenCVコアライブラリ |
| libopencv-highgui406 | 4.6.0+dfsg-12 | OpenCV GUIライブラリ |
| libopencv-imgproc406 | 4.6.0+dfsg-12 | 画像処理ライブラリ |
| libopencv-videoio406 | 4.6.0+dfsg-12 | ビデオI/Oライブラリ |
| v4l-utils | 1.22.1-5+b2 | Video4Linux2ユーティリティ (v4l2-ctl等) |

#### シリアル通信関連
```bash
sudo apt install -y python3-serial
```

| パッケージ | バージョン | 用途 |
|-----------|----------|------|
| python3-serial | 3.5-1.1 | PySerial (Modbus通信基盤) |

#### WebRTC関連 (オプション - 現在未インストール)
```bash
sudo apt install -y libavformat-dev libavcodec-dev libavdevice-dev \
                    libavutil-dev libswscale-dev libswresample-dev \
                    libavfilter-dev libopus-dev libvpx-dev libsrtp2-dev
```

| パッケージ | 用途 |
|-----------|------|
| libavformat-dev | FFmpeg フォーマット処理 |
| libavcodec-dev | FFmpeg コーデック |
| libopus-dev | Opus音声コーデック |
| libvpx-dev | VP8/VP9ビデオコーデック |
| libsrtp2-dev | SRTP (Secure RTP) |

#### 開発ツール
```bash
sudo apt install -y git build-essential
```

| パッケージ | 用途 |
|-----------|------|
| git | バージョン管理 |
| build-essential | C/C++コンパイラ、make等 |

---

## 🐍 Pythonパッケージ (pip3 install)

### インストールコマンド一覧

#### 必須パッケージ
```bash
# Modbus通信
pip3 install --break-system-packages minimalmodbus==2.1.1

# Web UI
pip3 install --break-system-packages fastapi==0.121.0 uvicorn==0.38.0 jinja2

# WebRTC (将来的に必要)
# pip3 install --break-system-packages aiortc==1.6.0
```

### パッケージリスト

#### 1. デバイス制御

| パッケージ | バージョン | インストール済 | 用途 |
|-----------|----------|--------------|------|
| minimalmodbus | 2.1.1 | ✅ | Modbus RTU通信 (グリッパー制御) |
| pyserial | 3.5 | ✅ (apt経由) | シリアル通信基盤 |

**インストールコマンド**:
```bash
pip3 install --break-system-packages minimalmodbus==2.1.1
```

#### 2. Web UI / API

| パッケージ | バージョン | インストール済 | 用途 |
|-----------|----------|--------------|------|
| fastapi | 0.121.0 | ✅ | Web APIフレームワーク |
| uvicorn | 0.38.0 | ✅ | ASGI Webサーバー |
| pydantic | 2.12.3 | ✅ | データバリデーション (FastAPI依存) |
| jinja2 | 3.1.2 | ✅ (apt経由) | HTMLテンプレート |
| starlette | 0.49.3 | ✅ (FastAPI依存) | ASGIフレームワーク |
| python-multipart | (未) | ❌ | ファイルアップロード処理 |

**インストールコマンド**:
```bash
pip3 install --break-system-packages fastapi==0.121.0 uvicorn==0.38.0
# オプション: ファイルアップロード機能追加時
# pip3 install --break-system-packages python-multipart
```

#### 3. WebRTC (低遅延ストリーミング)

| パッケージ | バージョン | インストール済 | 用途 |
|-----------|----------|--------------|------|
| aiortc | 1.6.0 | ❌ | WebRTC実装 |
| av | 10.x | ❌ | FFmpeg Pythonバインディング (aiortc依存) |
| aiohttp | 3.x | ❌ | 非同期HTTP (WebRTCシグナリング) |

**インストールコマンド**:
```bash
# システムライブラリを先にインストール
sudo apt install -y libavformat-dev libavcodec-dev libavdevice-dev \
                    libavutil-dev libswscale-dev libswresample-dev \
                    libavfilter-dev libopus-dev libvpx-dev libsrtp2-dev

# Pythonパッケージ
pip3 install --break-system-packages aiortc==1.6.0 aiohttp
```

#### 4. 画像処理

| パッケージ | バージョン | インストール済 | 用途 |
|-----------|----------|--------------|------|
| opencv-python | 4.6.0 | ✅ (apt経由) | OpenCV Python |
| numpy | 1.24.x | ✅ (apt経由) | 数値計算ライブラリ |
| pillow | (オプション) | ❌ | 画像処理ライブラリ |
| scikit-image | (オプション) | ❌ | 高度な画像処理 |

**インストールコマンド** (必要に応じて):
```bash
pip3 install --break-system-packages pillow scikit-image
```

#### 5. 3Dプリンター制御

| パッケージ | バージョン | インストール済 | 用途 |
|-----------|----------|--------------|------|
| requests | 2.x | ✅ (apt経由) | HTTP通信 (OctoPrint API) |

**インストールコマンド**:
```bash
sudo apt install -y python3-requests
```

#### 6. GPIO制御

| パッケージ | バージョン | インストール済 | 用途 |
|-----------|----------|--------------|------|
| RPi.GPIO | 0.7.x | ✅ (apt経由) | Raspberry Pi GPIO制御 |
| gpiozero | 2.x | ✅ (apt経由) | 高レベルGPIOライブラリ |

**インストールコマンド**:
```bash
sudo apt install -y python3-rpi.gpio python3-gpiozero
```

#### 7. データ処理・ユーティリティ

| パッケージ | バージョン | インストール済 | 用途 |
|-----------|----------|--------------|------|
| pyyaml | 6.x | ✅ (apt経由) | YAML設定ファイル読み込み |
| python-dotenv | (オプション) | ❌ | .env環境変数管理 |

**インストールコマンド**:
```bash
sudo apt install -y python3-yaml
# オプション
pip3 install --break-system-packages python-dotenv
```

---

## 📋 requirements.txt

プロジェクトルートの`requirements.txt`には以下が記載されています:

```txt
# カメラ・画像処理
opencv-python>=4.8.0
numpy>=1.24.0

# WebRTC
aiortc>=1.6.0
aiohttp>=3.9.0

# シリアル通信・Modbus
pyserial>=3.5
minimalmodbus>=2.1.1

# Web UI
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
jinja2>=3.1.0
python-multipart>=0.0.6

# 3Dプリンター制御
requests>=2.31.0

# GPIO制御
RPi.GPIO>=0.7.1
gpiozero>=2.0

# ユーティリティ
pyyaml>=6.0
python-dotenv>=1.0.0
```

**注意**: requirements.txtは全パッケージを列挙していますが、実際のインストールでは以下を優先してください:
1. apt経由でインストール可能なものは先にaptでインストール
2. aptで提供されていないもののみpipでインストール

---

## 🚀 セットアップ手順

### 1. システムパッケージのインストール (推奨)
```bash
# 基本ツール
sudo apt update
sudo apt install -y python3 python3-pip git build-essential

# OpenCV・カメラ
sudo apt install -y python3-opencv v4l-utils

# シリアル通信
sudo apt install -y python3-serial

# GPIO
sudo apt install -y python3-rpi.gpio python3-gpiozero

# その他
sudo apt install -y python3-yaml python3-requests python3-numpy
```

### 2. Pythonパッケージのインストール
```bash
# プロジェクトディレクトリに移動
cd /home/pi/assembly/AutomatedAssemblyRobot

# 必須パッケージ
pip3 install --break-system-packages minimalmodbus==2.1.1
pip3 install --break-system-packages fastapi==0.121.0 uvicorn==0.38.0

# WebRTC対応 (オプション - 低遅延ストリーミング必要時)
# sudo apt install -y libavformat-dev libavcodec-dev libavdevice-dev \
#                     libavutil-dev libswscale-dev libopus-dev libvpx-dev libsrtp2-dev
# pip3 install --break-system-packages aiortc==1.6.0 aiohttp
```

### 3. デバイス権限設定
```bash
# ユーザーをdialoutグループに追加 (シリアルポートアクセス)
sudo usermod -a -G dialout $USER

# ユーザーをvideoグループに追加 (カメラアクセス)
sudo usermod -a -G video $USER

# 再ログインまたは再起動して反映
```

---

## 🔍 インストール確認

### システムパッケージ確認
```bash
dpkg -l | grep -E 'python3-opencv|python3-serial|v4l-utils'
```

### Pythonパッケージ確認
```bash
pip3 list --user
```

### カメラ確認
```bash
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

### シリアルポート確認
```bash
ls -l /dev/ttyUSB*
```

### Pythonでのインポート確認
```bash
python3 -c "import cv2; print('OpenCV:', cv2.__version__)"
python3 -c "import serial; print('PySerial:', serial.__version__)"
python3 -c "import minimalmodbus; print('minimalmodbus:', minimalmodbus.__version__)"
python3 -c "import fastapi; print('FastAPI:', fastapi.__version__)"
```

---

## �� パッケージ追加時のルール

新しいパッケージを追加する際は、以下の手順に従ってください:

1. **aptで検索**:
   ```bash
   apt-cache search python3-<パッケージ名>
   ```

2. **aptで利用可能なら優先**:
   ```bash
   sudo apt install python3-<パッケージ名>
   ```

3. **aptで提供されていない場合**:
   ```bash
   pip3 install --break-system-packages <パッケージ名>
   ```

4. **このドキュメントを更新**:
   - パッケージ情報を該当セクションに追加
   - インストールコマンドを記載
   - requirements.txtにも追加

5. **Git commit**:
   ```bash
   git add docs/packages.md requirements.txt
   git commit -m "docs: <パッケージ名>を追加"
   ```

---

## 🔄 アップデート管理

### システムパッケージの更新
```bash
sudo apt update
sudo apt upgrade
```

### Pythonパッケージの更新
```bash
# 特定パッケージ
pip3 install --break-system-packages --upgrade <パッケージ名>

# 全パッケージ (注意: 非推奨)
# pip3 list --user --outdated | awk '{print $1}' | xargs pip3 install --break-system-packages --upgrade
```

---

## ⚠️ トラブルシューティング

### PEP 668エラー (externally-managed-environment)
```
error: externally-managed-environment
```
**対処法**:
- `--break-system-packages`フラグを使用
- または仮想環境を使用: `python3 -m venv venv && source venv/bin/activate`

### カメラアクセスエラー
```
VIDEOIO ERROR: V4L2: device is busy
```
**対処法**:
```bash
# 使用中のプロセスを確認
lsof /dev/video0
# プロセスを終了
kill <PID>
```

### シリアルポート権限エラー
```
Permission denied: '/dev/ttyUSB0'
```
**対処法**:
```bash
sudo usermod -a -G dialout $USER
# 再ログイン
```

---

## 改訂履歴
| 日付 | バージョン | 内容 | 作成者 |
|------|-----------|------|--------|
| 2025-11-05 | 1.0 | 初版作成 | GitHub Copilot |
| 2025-11-05 | 1.1 | aiortc/aiohttp未インストール状態を明記 | GitHub Copilot |

