# Camera Module

OpenCV + V4L2 カメラ制御モジュール

## 概要

このモジュールは、USB Webカメラ（Logitech C922 Pro等）をOpenCV + V4L2バックエンドで制御し、WebRTCストリーミング用のフレームを提供します。

### 主な機能

- **リアルタイムキャプチャ**: 非同期バックグラウンドループによる連続フレーム取得
- **自動再接続**: カメラ切断時の自動復旧
- **解像度対応**: 320×240 〜 1920×1080（高解像度時はFPS自動調整）
- **コーデック選択**: MJPEG / YUYV 対応
- **V4L2コントロール**: 明るさ、コントラスト、露出、フォーカス等の動的調整
- **スナップショット**: タイムスタンプ付き画像保存

## ファイル構成

```
src/camera/
├── __init__.py       # モジュール初期化
├── camera_manager.py # カメラ管理クラス
└── README.md         # このファイル
```

## 使用方法

### 基本的な使い方

```python
from src.camera.camera_manager import CameraManager

# 初期化とカメラ起動
camera = CameraManager()
await camera.start()

# 現在のフレーム取得
frame = camera.get_frame()
if frame is not None:
    print(f"フレームサイズ: {frame.shape}")  # (480, 640, 3)

# スナップショット撮影
result = await camera.take_snapshot()
print(f"保存先: {result['path']}")

# カメラ停止
await camera.stop()
```

### カメラコントロールの取得と設定

```python
# 利用可能なコントロール一覧を取得
controls = camera.get_controls()
for name, info in controls.items():
    print(f"{name}: {info['value']} (min={info['min']}, max={info['max']})")

# コントロール値を設定
await camera.set_control("brightness", 128)
await camera.set_control("auto_exposure", 1)  # マニュアル露出

# デフォルト値にリセット
await camera.reset_controls()
```

### 解像度・コーデック変更

```python
# 解像度変更
await camera.set_resolution(1280, 720)

# コーデック変更 (MJPEG推奨)
await camera.set_fourcc("MJPG")
```

## 画像データ仕様

### フレームデータ

- **形式**: NumPy配列 (H, W, C)
- **解像度**: 設定による（デフォルト 640×480）
- **チャンネル**: 3 (BGR順序, OpenCV形式)
- **データ型**: uint8
- **フレームレート**: 解像度に応じて自動調整
  - 640×480: 最大30fps
  - 1280×720: 最大20fps
  - 1920×1080: 最大15fps

### 対応コーデック

| コーデック | 説明 | CPU負荷 |
|-----------|------|---------|
| MJPG | Motion JPEG | 低 (推奨) |
| YUYV | 非圧縮YUV | 高 |

## V4L2コントロール一覧

`get_controls()` で取得できる代表的なパラメータ:

| コントロール名 | 型 | 説明 |
|---------------|-----|------|
| brightness | int | 明るさ |
| contrast | int | コントラスト |
| saturation | int | 彩度 |
| sharpness | int | シャープネス |
| gain | int | ゲイン |
| exposure_auto | menu | 露出モード (1=Manual, 3=Auto) |
| exposure_absolute | int | 露出時間 (マニュアル時) |
| focus_auto | bool | オートフォーカス |
| focus_absolute | int | フォーカス距離 |
| white_balance_automatic | bool | 自動ホワイトバランス |
| white_balance_temperature | int | 色温度 |
| power_line_frequency | menu | 電源周波数 (0=Off, 1=50Hz, 2=60Hz) |

## API リファレンス

### CameraManager クラス

#### メソッド

##### `__init__()`
カメラマネージャーを初期化します。設定は `src/config/settings.py` から読み込みます。

##### `async start() -> None`
カメラキャプチャを開始します。バックグラウンドタスクでフレームを継続取得します。

##### `async stop() -> None`
カメラキャプチャを停止し、リソースを解放します。

##### `get_frame() -> Optional[np.ndarray]`
最新のフレームを取得します。フレームがない場合はNoneを返します。

##### `is_opened() -> bool`
カメラが接続されているか確認します。

##### `async take_snapshot() -> Optional[Dict]`
現在のフレームをJPEGファイルとして保存します。

##### `get_controls() -> Dict`
V4L2コントロールの一覧と現在値を取得します。

##### `async set_control(name: str, value: int) -> bool`
V4L2コントロールの値を設定します。

##### `async set_resolution(width: int, height: int) -> bool`
解像度を変更します（カメラ再起動が必要）。

##### `async set_fourcc(fourcc: str) -> bool`
コーデックを変更します（"MJPG" または "YUYV"）。

## 設定

カメラ設定は `src/config/settings.py` で環境変数から読み込みます:

```python
CAMERA_DEVICE = int(os.getenv('CAMERA_DEVICE', '0'))      # /dev/video番号
CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '640'))      # 幅
CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '480'))    # 高さ
CAMERA_FPS = int(os.getenv('CAMERA_FPS', '30'))           # フレームレート
CAMERA_FOURCC = os.getenv('CAMERA_FOURCC', 'MJPG')        # コーデック
```

## トラブルシューティング

### "カメラを開けませんでした"

**原因**: カメラが接続されていない、または権限不足

**対策**:
1. カメラ接続を確認: `v4l2-ctl --list-devices`
2. 権限を設定: `sudo usermod -a -G video $USER`
3. ログアウト・ログインして権限を反映

### フレームレートが低い

**原因**: 高解像度設定、YUYV使用、CPU負荷

**対策**:
1. MJPEGコーデックを使用
2. 解像度を下げる
3. 不要なプロセスを停止

### 画像が暗い / ホワイトバランスがおかしい

**対策**:
1. Web UIでカメラパラメータを調整
2. オート設定をON/OFFで切り替える
3. `v4l2-ctl` で直接設定を確認

## 依存関係

- **opencv-python**: カメラキャプチャと画像処理
- **v4l-utils**: V4L2コントロール操作（システムパッケージ）
- **asyncio**: 非同期処理

---

**最終更新**: 2026-01-06

### 機能

#### 動的コントロール検出
```python
controls = camera_manager.get_controls()
# {
#   "brightness": {"type": "int", "min": 0, "max": 255, "default": 128, ...},
#   "exposure_auto": {"type": "menu", "options": [{"value": 0, "name": "Auto"}, ...]}
# }
```

#### コントロール設定
```python
# 整数値
camera_manager.set_control("brightness", 200)

# メニュー（値で指定）
camera_manager.set_control("exposure_auto", 1)

# ブール値
camera_manager.set_control("auto_white_balance", 0)
```

#### バリデーション
- コントロールの存在確認
- フラグチェック（inactive/disabled/grabbed）
- 値の範囲検証（min/max）
- 読み取り専用チェック

#### リセット機能
```python
# 個別リセット
camera_manager.reset_control("brightness")

# 一括リセット（inactive/disabled/buttonは自動スキップ）
results = camera_manager.reset_all_controls()
# {"brightness": True, "contrast": True, "reset_button": False, ...}
```

### API エンドポイント
- `GET /api/camera/controls`: 全コントロール取得
- `POST /api/camera/control/{name}/{value}`: コントロール設定
- `POST /api/camera/control/reset/{name}`: 個別リセット
- `POST /api/camera/controls/reset_all`: 一括リセット

### 対応カメラ例
- Raspberry Pi Camera Module (v1/v2/v3)
- USB Webカメラ（UVC対応）
- 産業用カメラ（v4l2対応）
