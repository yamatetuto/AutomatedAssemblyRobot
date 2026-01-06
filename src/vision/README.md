# Vision Module

画像処理・物体検出モジュール

## 概要

このモジュールは、カメラ画像から特定のオブジェクト（光ファイバー、ガラス玉など）を検出し、画像中心からのオフセットを計算する機能を提供します。

### 主な機能

- **光ファイバー検出**: Cannyエッジ検出 + 確率的Hough変換による直線検出
- **ガラス玉検出**: Hough円変換による円形物体検出
- **オフセット計算**: 検出物体と画像中心との距離・方向を算出
- **結果画像生成**: 検出結果を可視化したBase64エンコード画像

## ファイル構成

```
src/vision/
├── __init__.py           # モジュール初期化
├── manager.py            # VisionManager（検出統括クラス）
├── README.md             # このファイル
└── detectors/            # 検出器クラス
    ├── __init__.py
    ├── base.py           # BaseDetector（抽象基底クラス）
    ├── fiber.py          # FiberDetector（光ファイバー検出）
    └── bead.py           # BeadDetector（ガラス玉検出）
```

## 使用方法

### 基本的な使い方

```python
from src.vision.manager import VisionManager
import cv2

# 初期化
vision = VisionManager()

# 画像読み込み
image = cv2.imread("sample.jpg")

# 光ファイバー検出
fiber_result = vision.detect_fiber(image)
if fiber_result["detected"]:
    print(f"検出数: {fiber_result['count']}")
    print(f"オフセット: dx={fiber_result['offset']['dx']}, dy={fiber_result['offset']['dy']}")

# ガラス玉検出
bead_result = vision.detect_bead(image)
if bead_result["detected"]:
    for circle in bead_result["circles"]:
        print(f"中心: {circle['center']}, 半径: {circle['radius']}")
```

### 結果画像の表示

```python
import base64

# 検出実行
result = vision.detect_fiber(image)

# Base64デコードして画像表示
if "image_base64" in result:
    img_data = base64.b64decode(result["image_base64"])
    # Webアプリなら: <img src="data:image/jpeg;base64,{result['image_base64']}">
```

## 検出器の詳細

### FiberDetector（光ファイバー検出）

細長い物体（光ファイバーなど）を検出します。

#### アルゴリズム
1. グレースケール変換
2. ガウシアンブラーによるノイズ除去
3. Cannyエッジ検出
4. 確率的Hough変換で直線検出
5. 長さでソートし、上位2本をペアリング
6. 2本の中心線を算出
7. 画像中心からのオフセット計算

#### 設定パラメータ（環境変数）

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `VISION_FIBER_CANNY_THRESHOLD1` | 50 | Cannyエッジ検出の低閾値 |
| `VISION_FIBER_CANNY_THRESHOLD2` | 150 | Cannyエッジ検出の高閾値 |
| `VISION_FIBER_MIN_LINE_LENGTH` | 100 | 検出する直線の最小長さ（ピクセル） |
| `VISION_FIBER_MAX_LINE_GAP` | 10 | 同一直線とみなす最大隙間（ピクセル） |

#### 戻り値

```python
{
    "detected": True,           # 検出成功
    "count": 5,                 # 検出された線分の数
    "lines": [                  # 全ての検出線分
        ((x1, y1), (x2, y2)),
        ...
    ],
    "paired_lines": [           # ペアリングされた2本の線
        ((x1, y1), (x2, y2)),
        ((x1, y1), (x2, y2))
    ],
    "center_line": ((x1, y1), (x2, y2)),  # 中心線
    "offset": {                 # 画像中心からのオフセット
        "dx": 10.5,             # X方向オフセット（ピクセル）
        "dy": -5.2              # Y方向オフセット（ピクセル）
    },
    "image_base64": "..."       # 結果画像（Base64 JPEG）
}
```

### BeadDetector（ガラス玉検出）

丸い物体（ガラス玉など）を検出します。

#### アルゴリズム
1. グレースケール変換
2. メディアンブラーによるノイズ除去（円検出に効果的）
3. Hough円変換で円検出
4. 最も画像中心に近い円を選択
5. オフセット計算

#### 設定パラメータ（環境変数）

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `VISION_BEAD_MIN_DIST` | 20 | 検出円の中心間の最小距離（ピクセル） |
| `VISION_BEAD_PARAM1` | 50 | Cannyエッジ検出の高閾値（内部使用） |
| `VISION_BEAD_PARAM2` | 30 | 円の中心検出閾値（小さいほど多く検出） |
| `VISION_BEAD_MIN_RADIUS` | 10 | 検出する円の最小半径（ピクセル） |
| `VISION_BEAD_MAX_RADIUS` | 50 | 検出する円の最大半径（ピクセル） |

#### 戻り値

```python
{
    "detected": True,           # 検出成功
    "count": 3,                 # 検出された円の数
    "circles": [                # 検出された全ての円
        {"center": (100, 150), "radius": 25},
        {"center": (200, 180), "radius": 30},
        ...
    ],
    "offset": {                 # 最も近い円へのオフセット
        "dx": 20,               # X方向オフセット（ピクセル）
        "dy": -10               # Y方向オフセット（ピクセル）
    },
    "image_base64": "..."       # 結果画像（Base64 JPEG）
}
```

## 結果画像の描画内容

### 光ファイバー検出
- **緑の十字**: 画像中心
- **薄い青の線**: 検出された全ての線分
- **青の線**: ペアリングされた2本の線
- **赤の線**: 算出された中心線
- **黄色の線**: 画像中心から目標点へのオフセットベクトル

### ガラス玉検出
- **緑の十字**: 画像中心
- **緑の円**: 検出された円の周囲
- **赤の点**: 検出された円の中心
- **黄色の線**: 画像中心から最も近い円へのオフセットベクトル

## カスタム検出器の作成

BaseDetectorを継承して新しい検出器を作成できます:

```python
from src.vision.detectors.base import BaseDetector
import numpy as np
from typing import Dict, Any

class CustomDetector(BaseDetector):
    def __init__(self, param1: int = 100):
        self.param1 = param1
    
    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        if image is None:
            return {"detected": False, "data": None}
        
        # カスタム検出ロジック
        # ...
        
        return {
            "detected": True,
            "data": {...}
        }
```

## 依存関係

- **opencv-python**: 画像処理、エッジ検出、Hough変換
- **numpy**: 画像データ配列処理

## パフォーマンス

### Raspberry Pi 4での実測値

| 処理 | 640×480 | 1280×720 |
|------|---------|----------|
| 光ファイバー検出 | ~50ms | ~120ms |
| ガラス玉検出 | ~30ms | ~80ms |

## トラブルシューティング

### 検出精度が低い

**対策**:
1. カメラの露出・フォーカスを調整
2. 照明条件を改善（均一な照明）
3. 閾値パラメータを調整（環境変数で設定）

### 誤検出が多い

**対策**:
1. `VISION_FIBER_MIN_LINE_LENGTH` を大きくする
2. `VISION_BEAD_PARAM2` を大きくする（円検出の閾値を厳しくする）
3. `VISION_BEAD_MIN_RADIUS` / `MAX_RADIUS` で半径範囲を絞る

### 検出が遅い

**対策**:
1. 入力画像の解像度を下げる
2. ROI（関心領域）を設定して処理範囲を限定

---

**最終更新**: 2026-01-06
