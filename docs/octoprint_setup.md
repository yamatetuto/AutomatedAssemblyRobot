# OctoPrint セットアップガイド

## 1. 必要なパッケージのインストール

```bash
sudo apt update
sudo apt install -y python3-pip python3-dev python3-setuptools python3-venv \
    git libyaml-dev build-essential libffi-dev libssl-dev
```

## 2. OctoPrint用の仮想環境作成

```bash
cd ~
python3 -m venv octoprint_venv
source octoprint_venv/bin/activate
pip install --upgrade pip
```

## 3. OctoPrintのインストール

```bash
pip install OctoPrint
```

## 4. OctoPrintの起動

```bash
~/octoprint_venv/bin/octoprint serve
```

初回起動時、以下にアクセス:
- URL: `http://10.32.77.150:5000`
- セットアップウィザードに従って初期設定

## 5. systemdサービスとして登録（自動起動）

```bash
sudo nano /etc/systemd/system/octoprint.service
```

以下を記述:

```ini
[Unit]
Description=OctoPrint 3D Printer Host
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/home/pi/octoprint_venv/bin/octoprint serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

サービスを有効化:

```bash
sudo systemctl daemon-reload
sudo systemctl enable octoprint.service
sudo systemctl start octoprint.service
sudo systemctl status octoprint.service
```

## 6. 3Dプリンター接続

1. プリンターをUSBで接続
2. デバイス確認: `ls -l /dev/ttyUSB* /dev/ttyACM*`
3. OctoPrint Web UIから接続設定

## 7. API設定

1. OctoPrint Web UI → Settings → API
2. API Keyを生成・コピー
3. `/home/pi/assembly/AutomatedAssemblyRobot/src/config/settings.py` に設定:

```python
OCTOPRINT_URL = "http://localhost:5000"
OCTOPRINT_API_KEY = "YOUR_API_KEY_HERE"
```

## トラブルシューティング

### ポート競合
- OctoPrint: ポート5000
- ロボット制御UI: ポート8000
- 競合しないので両方同時起動可能

### USB権限エラー
```bash
sudo usermod -a -G dialout pi
sudo usermod -a -G tty pi
# 再ログイン必要
```

### ログ確認
```bash
journalctl -u octoprint.service -f
```
