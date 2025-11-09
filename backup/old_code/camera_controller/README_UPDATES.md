# Camera Controller Updates

## 新機能

### 1. カメラ設定値の自動取得
ブラウザでWebRTCストリームに接続すると、以下のカメラ情報が自動的に表示されます：

- **解像度** (width x height)
- **FPS** (フレームレート)
- **コーデック** (FOURCC形式)
- **Brightness** (明るさ)
- **Contrast** (コントラスト)
- **Saturation** (彩度)
- **Hue** (色相)

### 2. ブラウザ上での撮影・保存機能
- 📷 **Take Snapshot** ボタンをクリックすると、現在のフレームをJPG形式で保存
- 保存先: `snapshots/snapshot_YYYYMMDD_HHMMSS.jpg`
- 撮影成功時にファイル名が表示される

### 3. 改善されたUI
- モダンでレスポンシブなデザイン
- リアルタイムでスライダー値を表示
- ステータスメッセージ表示（成功/エラー）
- カメラ情報の自動更新（5秒ごと）

## 使い方

### WebRTCストリーミングの起動

```bash
cd /home/pi/assembly/assembly/src/camera_controller
python3 CameraStreamer.py --webrtc --device 0 --width 640 --height 480
```

### ブラウザでアクセス

1. ブラウザで `http://<RaspberryPiのIPアドレス>:8080` を開く
2. **▶ Start Stream** ボタンをクリック
3. カメラ情報が自動的に表示される
4. カメラ設定を変更したい場合はスライダーを調整して **Apply Settings** をクリック
5. **📷 Take Snapshot** ボタンで現在のフレームを撮影・保存

## 技術的な変更点

### `webrtc/streamer.py`の主な追加機能

1. **`get_camera_properties(cap)`** - OpenCV経由でカメラプロパティを取得
2. **`_snapshot(request)`** - スナップショット撮影APIエンドポイント
3. **`_get_settings(request)`** - カメラ情報をJSONで返すように拡張

### `webrtc_index.html`の主な変更点

1. カメラ情報表示セクションの追加
2. スナップショットボタンの追加
3. スライダー値のリアルタイム表示
4. ステータスメッセージ機能
5. 改善されたスタイリング（モダンなUI）

## ファイル構成

```
camera_controller/
├── CameraStreamer.py          # メインエントリーポイント
├── webrtc_index.html          # 新しいWebRTC UI (更新済み)
├── webrtc/
│   ├── streamer.py            # WebRTCサーバー (更新済み)
│   ├── streamer_new.py        # 新バージョン（streamer.pyにコピー済み）
│   └── streamer_backup.py     # 旧バージョンのバックアップ
└── snapshots/                 # 撮影した画像の保存先 (自動作成)
```

## トラブルシューティング

### カメラ情報が表示されない
- カメラが正しく接続されているか確認
- `v4l2-ctl -d /dev/video0 --all` でカメラ情報を確認

### スナップショットが保存されない
- `snapshots/` ディレクトリの書き込み権限を確認
- ディスクの空き容量を確認

### ストリームが接続できない
- ファイアウォールでポート8080が開いているか確認
- Raspberry PiのIPアドレスが正しいか確認
- `--webrtc-port` オプションでポート番号を変更可能

### サーバーの停止
```
pkill -f "python3 CameraStreamer.py"
```

## 今後の拡張候補

- [ ] スナップショットのダウンロード機能
- [ ] 複数フォーマット対応（PNG, RAWなど）
- [ ] 連続撮影（タイムラプス）機能
- [ ] 動画録画機能
- [ ] カメラ設定のプリセット保存/読み込み機能
