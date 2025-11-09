# 高解像度カメラ映像停止問題の調査レポート

**日付**: 2025-11-09  
**問題**: 640x480以上の解像度でWebRTC映像が停止する  
**影響範囲**: app.py, main_webrtc_fixed.py 両方で発生

## 1. カメラハードウェア仕様（C922 Pro）

### サポートフォーマット

#### YUYV (非圧縮)
- 640x480: 最大30fps
- 800x600: 最大24fps
- 1280x720: 最大10fps
- 1920x1080: 最大5fps
- **高解像度では低フレームレート**

#### MJPG (圧縮)
- 640x480: 最大30fps
- 800x600: 最大30fps
- 1280x720: 最大60fps ✅
- 1920x1080: 最大30fps ✅
- **高解像度でも高フレームレート対応**

### 結論
- 現在の設定（MJPG）は正しい
- カメラハードウェア自体は高解像度をサポート

## 2. 現在の実装状況

### src/camera/camera_manager.py
```python
# フォーマット設定を先に行う (MJPEG)
fourcc = cv2.VideoWriter_fourcc(*self.settings["fourcc"])
self.camera.set(cv2.CAP_PROP_FOURCC, fourcc)

# 解像度とFPS設定
self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings["width"])
self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings["height"])
self.camera.set(cv2.CAP_PROP_FPS, self.settings["fps"])
```

✅ フォーマット設定順序は正しい（FOURCC → 解像度）

## 3. 推測される原因

### A. WebRTC帯域幅の問題
- 高解像度映像のビットレートが帯域を超過
- WebRTC接続がタイムアウトまたはスタック

### B. フレームレートの不一致
- カメラ: 30fps (MJPG 1920x1080)
- WebRTC: 設定値との不一致でバッファオーバーフロー

### C. バッファサイズの不足
- OpenCVのバッファサイズが高解像度に対して小さい
- `CAP_PROP_BUFFERSIZE`が未設定

### D. CPU処理能力の限界
- Raspberry Pi 4での映像エンコード処理が追いつかない
- 1920x1080 30fpsのMJPEG→H.264変換が重い

## 4. 検証すべき項目

### ステップ1: OpenCVバッファサイズの確認
```python
self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # バッファを1フレームに制限
```

### ステップ2: フレームレート制限
```python
# 高解像度時はフレームレートを下げる
if width >= 1280:
    self.camera.set(cv2.CAP_PROP_FPS, 15)  # 30→15fps
```

### ステップ3: WebRTCビットレート制限
```python
# aiortcのVideoStreamTrackでフレームレート制御
```

### ステップ4: CPU使用率モニタリング
- `top -p <pid>`でapp.pyのCPU使用率を確認
- 100%に達している場合は処理能力の問題

## 5. 次のアクション

1. **バッファサイズを1に設定**（最も可能性が高い）
2. **高解像度時のFPS自動調整**
3. **WebRTC側でのフレームスキップ実装**
4. **CPU使用率の測定**

## 6. 参考情報

- C922 Pro仕様: MJPG 1920x1080@30fps対応
- Raspberry Pi 4: 4コアCortex-A72 1.5GHz
- OpenCV 4.6+: バッファサイズ設定サポート
- aiortc: 自動ビットレート調整機能なし（手動実装必要）
