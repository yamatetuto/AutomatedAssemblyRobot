# WebRTC Module

カメラ映像のWebRTCストリーミングモジュール

## 概要

このモジュールは、CameraManagerからのフレームをWebRTC経由でブラウザにリアルタイムストリーミングする機能を提供します。aiortcライブラリを使用したPython実装です。

### 主な機能

- **リアルタイムストリーミング**: カメラ映像をWebブラウザに配信（遅延 約300ms）
- **低遅延**: WebRTCプロトコルによるP2P通信
- **aiortc**: Python WebRTC実装ライブラリ使用
- **複数接続対応**: 複数ブラウザからの同時視聴
- **自動リソース管理**: 接続切断時の自動クリーンアップ

## ファイル構成

```
src/webrtc/
├── __init__.py          # モジュール初期化
├── webrtc_manager.py    # WebRTC接続管理クラス
└── README.md            # このファイル
```

## 使用方法

### FastAPIアプリケーションからの使用

```python
from fastapi import FastAPI
from src.webrtc.webrtc_manager import WebRTCManager
from src.camera.camera_manager import CameraManager

app = FastAPI()
camera_manager = CameraManager()
webrtc_manager = WebRTCManager(camera_manager)

@app.post("/api/webrtc/offer")
async def webrtc_offer(offer: dict):
    """WebRTC Offerを受け取りAnswerを返す"""
    answer = await webrtc_manager.create_offer(
        sdp=offer["sdp"],
        type=offer["type"]
    )
    return answer

@app.on_event("shutdown")
async def shutdown():
    await webrtc_manager.close_all()
```

### ブラウザ側の実装例

```javascript
// WebRTC接続
const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});

// ビデオストリーム受信
pc.ontrack = (event) => {
    const video = document.getElementById('video');
    video.srcObject = event.streams[0];
};

// 受信専用トランシーバーを追加
pc.addTransceiver("video", { direction: "recvonly" });

// Offer作成
const offer = await pc.createOffer();
await pc.setLocalDescription(offer);

// サーバーにOffer送信
const response = await fetch('/api/webrtc/offer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        sdp: pc.localDescription.sdp,
        type: pc.localDescription.type
    })
});

// Answer受信して設定
const answer = await response.json();
await pc.setRemoteDescription(new RTCSessionDescription(answer));
```

## API リファレンス

### WebRTCManager クラス

#### コンストラクタ

##### `__init__(camera_manager: CameraManager)`
WebRTCマネージャーを初期化します。

**引数**:
- `camera_manager`: CameraManagerインスタンス（フレーム取得元）

#### メソッド

##### `async create_offer(sdp: str, type: str) -> dict`
クライアントからのOfferを処理し、Answerを生成します。

**引数**:
- `sdp`: Session Description Protocol文字列
- `type`: SDPタイプ（"offer"）

**戻り値**:
- `dict`: `{"sdp": str, "type": "answer"}`

##### `async close_peer_connection(pc: RTCPeerConnection) -> None`
特定のPeerConnectionを閉じます。

##### `async close_all() -> None`
すべてのPeerConnectionを閉じます。アプリケーション終了時に呼び出します。

### VideoTrack クラス

カメラ映像をWebRTC VideoTrackとして提供するカスタムトラック。

#### コンストラクタ

##### `__init__(camera_manager: CameraManager)`
VideoTrackを初期化します。

**引数**:
- `camera_manager`: CameraManagerインスタンス

#### メソッド

##### `async recv() -> VideoFrame`
次のビデオフレームを取得します。

**動作**:
1. CameraManagerから最新フレームを取得
2. BGR → RGB変換
3. aiortc VideoFrameに変換
4. タイムスタンプ付与

**戻り値**:
- `VideoFrame`: aiortcのビデオフレームオブジェクト

## 接続状態の監視

WebRTCManagerは接続状態の変化を自動的に監視します:

| 状態 | 説明 |
|------|------|
| `new` | 接続開始 |
| `connecting` | 接続中 |
| `connected` | 接続完了 |
| `disconnected` | 一時切断 |
| `failed` | 接続失敗 |
| `closed` | 接続終了 |

`failed` または `closed` 状態になると、PeerConnectionは自動的にクリーンアップされます。

## 注意事項

- STUNサーバーにはGoogleの公開サーバー (`stun:stun.l.google.com:19302`) を使用
- ローカルネットワーク内では直接P2P接続が確立される
- NATを超える場合はTURNサーバーの設定が必要な場合がある
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
