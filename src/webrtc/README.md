# WebRTC Module

カメラ映像のWebRTCストリーミングモジュール

## 概要

このモジュールは、Intel RealSense D435カメラの映像をWebRTC経由でブラウザにストリーミングする機能を提供します。

### 主な機能

- **リアルタイムストリーミング**: RGB/Depthカメラ映像をWebブラウザに配信
- **低遅延**: WebRTCプロトコルによる低遅延伝送
- **aiortc**: Python WebRTC実装ライブラリ使用
- **非同期処理**: FastAPIとの統合

## ファイル構成

```
src/webrtc/
├── __init__.py        # モジュール初期化
├── webrtc_handler.py  # WebRTCセッション管理
└── README.md          # このファイル
```

## 使用方法

### FastAPIアプリケーションからの使用

```python
from fastapi import FastAPI
from src.webrtc.webrtc_handler import create_peer_connection

app = FastAPI()

@app.post("/offer")
async def offer(sdp: dict):
    pc = create_peer_connection()
    # WebRTC SDP交換処理
    await pc.setRemoteDescription(RTCSessionDescription(**sdp))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
```

### ブラウザ側の実装例

```javascript
// WebRTC接続
const pc = new RTCPeerConnection();

// ビデオストリーム受信
pc.ontrack = (event) => {
    const video = document.getElementById('video');
    video.srcObject = event.streams[0];
};

// Offer作成
const offer = await pc.createOffer();
await pc.setLocalDescription(offer);

// サーバーにOffer送信
const response = await fetch('/offer', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        sdp: pc.localDescription.sdp,
        type: pc.localDescription.type
    })
});

// Answer受信
const answer = await response.json();
await pc.setRemoteDescription(answer);
```

## API リファレンス

### WebRTCHandler クラス

#### メソッド

##### `create_peer_connection(camera_manager: CameraManager) -> RTCPeerConnection`
WebRTC Peer Connectionを作成します。

**引数**:
- `camera_manager`: CameraManagerインスタンス

**戻り値**:
- `RTCPeerConnection`: aiortcのPeerConnectionオブジェクト

**動作**:
1. RTCPeerConnectionインスタンス作成
2. カメラからビデオトラック作成
3. トラックをPeerConnectionに追加

### VideoStreamTrack クラス

カメラ映像をWebRTC VideoTrackとして提供するカスタムトラック。

##### `__init__(camera_manager: CameraManager)`
ビデオストリームトラックを初期化します。

##### `async recv() -> av.VideoFrame`
次のビデオフレームを取得します。

**戻り値**:
- `av.VideoFrame`: PyAV形式のビデオフレーム

## WebRTC接続フロー

```
[ブラウザ]                     [サーバー]
    |                              |
    |--- POST /offer (SDP) ------->|
    |                              | create_peer_connection()
    |                              | setRemoteDescription()
    |                              | createAnswer()
    |                              | setLocalDescription()
    |<----- Answer (SDP) ----------|
    |                              |
    | ICE Candidate交換             |
    |<----------------------------->|
    |                              |
    | ビデオストリーム開始            |
    |<=============================|
```

## トラブルシューティング

### ブラウザでビデオが表示されない

**原因**: WebRTC接続失敗、カメラエラー

**対策**:
1. ブラウザの開発者ツールでコンソールエラーを確認
2. HTTPS接続を使用（HTTPでは一部ブラウザでWebRTCが動作しない）
3. カメラが正しく起動しているか確認
4. ファイアウォール設定を確認

### "ICE connection failed"

**原因**: NAT/ファイアウォール、ICE Candidate交換失敗

**対策**:
1. STUNサーバー設定を確認:
   ```python
   RTCConfiguration(iceServers=[
       RTCIceServer(urls=["stun:stun.l.google.com:19302"])
   ])
   ```
2. ローカルネットワーク内での接続を確認
3. TURNサーバーの導入を検討

### 映像遅延が大きい

**原因**: ネットワーク帯域不足、エンコーディング負荷

**対策**:
1. ビデオ解像度を下げる（CameraManagerの設定を変更）
2. フレームレートを下げる
3. ネットワーク帯域を確認

## 依存関係

- **aiortc**: Python WebRTC実装
- **av (PyAV)**: 動画フレーム処理
- **opencv-python**: 画像変換（必要に応じて）

インストール:
```bash
pip install aiortc av opencv-python
```

## パフォーマンス

### Raspberry Pi 4での推奨設定

- **解像度**: 640×480 (VGA) 推奨
- **フレームレート**: 15-30 FPS
- **ビットレート**: 500-1000 kbps

1920×1080の高解像度ストリーミングはCPU負荷が高いため、用途に応じて調整してください。

### CPU使用率

- 640×480, 30FPS: 約30-40%
- 1920×1080, 30FPS: 約60-80%

## セキュリティ

### HTTPS必須

WebRTCはセキュアコンテキストを要求するため、本番環境ではHTTPSを使用してください:

```bash
# 自己署名証明書の生成（開発用）
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# uvicornでHTTPS起動
uvicorn app:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### CORS設定

FastAPIアプリケーションでCORSを適切に設定してください:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 開発者向け情報

### aiortcの内部動作

1. **VideoStreamTrack**: カメラフレームをWebRTCフレームに変換
2. **RTCPeerConnection**: SDPネゴシエーション、ICE処理
3. **MediaStreamTrack**: ビデオ/オーディオトラックの抽象化

### フレーム変換処理

```python
# CameraManager (NumPy) → PyAV (VideoFrame) → WebRTC
rgb_frame = await camera.get_color_frame()  # numpy.ndarray
av_frame = av.VideoFrame.from_ndarray(rgb_frame, format='bgr24')
return av_frame
```

## 参考資料

- [aiortcドキュメント](https://aiortc.readthedocs.io/)
- [WebRTC API仕様](https://www.w3.org/TR/webrtc/)
- [PyAVドキュメント](https://pyav.org/)

---

**最終更新**: 2025-11-10  
**バージョン**: v1.0
