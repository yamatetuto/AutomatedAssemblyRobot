# Camera Module

Intel RealSense D435カメラ制御モジュール

## 概要

このモジュールは、Intel RealSense D435深度カメラのRGB画像とDepth画像を取得する機能を提供します。

### 主な機能

- **RGB画像取得**: 1920×1080、30FPS
- **Depth画像取得**: 640×480、30FPS（視差マップ）
- **非同期処理**: asyncioによる非ブロッキング画像取得
- **自動リソース管理**: コンテキストマネージャー対応

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

# RGB画像取得
rgb_image = await camera.get_color_frame()
print(f"RGB画像サイズ: {rgb_image.shape}")  # (1080, 1920, 3)

# Depth画像取得
depth_image = await camera.get_depth_frame()
print(f"Depth画像サイズ: {depth_image.shape}")  # (480, 640)

# カメラ停止
await camera.stop()
```

### コンテキストマネージャーを使った使い方

```python
async with CameraManager() as camera:
    rgb = await camera.get_color_frame()
    depth = await camera.get_depth_frame()
    # 自動的にstop()が呼ばれる
```

### 複数フレーム取得

```python
camera = CameraManager()
await camera.start()

for i in range(10):
    rgb = await camera.get_color_frame()
    depth = await camera.get_depth_frame()
    # 画像処理...
    await asyncio.sleep(0.1)  # 100ms間隔

await camera.stop()
```

## 画像データ仕様

### RGB画像

- **形式**: NumPy配列 (H, W, C)
- **解像度**: 1920×1080
- **チャンネル**: 3 (BGR順序)
- **データ型**: uint8
- **フレームレート**: 30 FPS

### Depth画像

- **形式**: NumPy配列 (H, W)
- **解像度**: 640×480
- **単位**: ミリメートル (mm)
- **データ型**: uint16
- **測定範囲**: 約0.3m〜3.0m
- **フレームレート**: 30 FPS

## API リファレンス

### CameraManager クラス

#### メソッド

##### `__init__()`
カメラマネージャーを初期化します。

##### `async start() -> None`
カメラを起動し、ストリーミングを開始します。

**例外**:
- `RuntimeError`: カメラの起動に失敗した場合

##### `async stop() -> None`
カメラを停止し、リソースを解放します。

##### `async get_color_frame() -> np.ndarray`
RGB画像を取得します。

**戻り値**: 
- `np.ndarray`: shape=(1080, 1920, 3), dtype=uint8

**例外**:
- `RuntimeError`: カメラが起動していない場合
- `TimeoutError`: フレーム取得タイムアウト（5秒）

##### `async get_depth_frame() -> np.ndarray`
Depth画像を取得します。

**戻り値**:
- `np.ndarray`: shape=(480, 640), dtype=uint16

**例外**:
- `RuntimeError`: カメラが起動していない場合
- `TimeoutError`: フレーム取得タイムアウト（5秒）

##### `async __aenter__() -> CameraManager`
コンテキストマネージャーのエントリーポイント。

##### `async __aexit__(*args) -> None`
コンテキストマネージャーの終了処理。

## 設定

### RealSense設定

カメラの解像度とフレームレートは`camera_manager.py`内で設定されています:

```python
# RGB設定
config.enable_stream(
    rs.stream.color,
    1920, 1080,  # 解像度
    rs.format.bgr8,
    30  # FPS
)

# Depth設定
config.enable_stream(
    rs.stream.depth,
    640, 480,  # 解像度
    rs.format.z16,
    30  # FPS
)
```

変更する場合は、`camera_manager.py`の該当箇所を編集してください。

## トラブルシューティング

### "No RealSense devices detected"

**原因**: カメラが接続されていない、またはドライバー未インストール

**対策**:
1. USBケーブルの接続を確認
2. `lsusb`でデバイスを確認（Intel Corp. が表示されるべき）
3. librealsenseのインストール確認:
   ```bash
   python3 -c "import pyrealsense2; print(pyrealsense2.__version__)"
   ```

### "Failed to wait for frames"

**原因**: フレーム取得タイムアウト

**対策**:
1. カメラのUSB3.0接続を確認（USB2.0では不安定な場合あり）
2. カメラを再接続
3. Raspberry Piを再起動

### 画像が真っ暗 / ノイズが多い

**原因**: 照明不足、レンズ汚れ、設定問題

**対策**:
1. 環境照明を確認
2. レンズをクリーニング
3. カメラの露出設定を調整（RealSense Viewerで確認可能）

## 依存関係

- **pyrealsense2**: Intel RealSense SDK Python wrapper
- **numpy**: 画像データ配列処理
- **asyncio**: 非同期処理

インストール:
```bash
pip install pyrealsense2 numpy
```

## パフォーマンス

### Raspberry Pi 4での実測値

- RGB取得: 約30ms/フレーム
- Depth取得: 約30ms/フレーム
- 両方取得: 約33ms/フレーム（30FPS達成可能）

### メモリ使用量

- RGB画像1フレーム: 約6MB (1920×1080×3)
- Depth画像1フレーム: 約0.6MB (640×480×2)

## 開発者向け情報

### 内部処理フロー

1. `start()`: パイプライン設定 → ストリーミング開始
2. `get_color_frame()` / `get_depth_frame()`:
   - `wait_for_frames(timeout_ms=5000)` でフレーム待機
   - `asyncio.to_thread()` で非同期実行
   - NumPy配列に変換
3. `stop()`: ストリーミング停止

### スレッドセーフティ

- RealSenseパイプラインは内部的にスレッドセーフ
- `asyncio.to_thread()`により、ブロッキング操作を非同期化

## 参考資料

- [Intel RealSense D435仕様](https://www.intelrealsense.com/depth-camera-d435/)
- [pyrealsense2ドキュメント](https://github.com/IntelRealSense/librealsense/tree/master/wrappers/python)
- [RealSense SDK](https://github.com/IntelRealSense/librealsense)

---

**最終更新**: 2025-11-10  
**バージョン**: v1.0
