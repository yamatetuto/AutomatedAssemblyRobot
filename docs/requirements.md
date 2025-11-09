# 要件定義書

**作成日**: 2025-11-05  
**最終更新**: 2025-11-09  
**バージョン**: 2.0  
**プロジェクト**: 自動組立ロボットシステム

---

## 1. プロジェクト概要

### 1.1 目的
積層型3Dプリンター、ディスペンサー、XYZ直交ロボットを組み合わせた医療機器の自動組立システムを構築する。

### 1.2 現在の実装スコープ
- ✅ カメラ・画像処理システム（モジュール化済み）
- ✅ グリッパー制御システム（モジュール化済み）
- ✅ WebRTCストリーミング（モジュール化済み）
- ✅ 統合Webアプリケーション（app.py）

### 1.3 アーキテクチャ
**v2.0 (2025-11-09)**: モジュール化アーキテクチャ
- 各機能を独立したモジュールとして実装（src/camera, src/gripper, src/webrtc）
- 単一プロセスで全機能を統合（ハードウェア排他制御の制約に対応）
- コードの再利用性を維持

---

## 2. 主要機能

### 2.1 カメラ制御
- ✅ WebRTCリアルタイムストリーミング（低遅延）
- ✅ カメラパラメータ調整（明るさ、コントラスト、フォーカスなど）
- ✅ 解像度・コーデック変更（320x240〜1920x1080, MJPEG/YUYV）
- ✅ スナップショット撮影・保存

### 2.2 グリッパー制御
- ✅ サーボON/OFF
- ✅ 原点復帰
- ✅ ポジション移動（0-63）
- ✅ ステータス取得（位置、アラーム、サーボ状態）
- ✅ ポジションテーブル管理（64ポジション、各種パラメータ設定）

### 2.3 パフォーマンス実績
- グリッパーステータス取得: ~0.14秒（40倍以上高速化）
- ポジションデータ取得: ~0.18秒
- ポジション移動: ~0.22秒

---

## 3. 技術スタック

- **言語**: Python 3.9+
- **Webフレームワーク**: FastAPI
- **WebRTC**: aiortc
- **シリアル通信**: minimalmodbus (Modbus RTU)
- **画像処理**: OpenCV
- **カメラ制御**: v4l2-ctl
- **ハードウェア**: Raspberry Pi, C922 Pro Webcam, IAI製グリッパー

---

## 4. API仕様

### カメラAPI
- `GET /api/camera/status` - ステータス取得
- `GET /api/camera/controls` - コントロール一覧
- `POST /api/camera/control/{name}/{value}` - パラメータ設定
- `GET /api/camera/resolutions` - 対応解像度一覧
- `POST /api/camera/resolution` - 解像度変更
- `POST /api/camera/codec` - コーデック変更
- `POST /api/camera/snapshot` - スナップショット撮影
- `GET /api/camera/snapshots` - スナップショット一覧

### グリッパーAPI
- `GET /api/gripper/status` - ステータス取得
- `POST /api/gripper/servo/{action}` - サーボON/OFF
- `POST /api/gripper/home` - 原点復帰
- `POST /api/gripper/move/{position}` - ポジション移動
- `GET /api/gripper/position_table/{position}` - ポジションデータ取得
- `POST /api/gripper/position_table/{position}` - ポジションデータ設定

### WebRTC API
- `POST /api/webrtc/offer` - WebRTC接続確立

---

## 5. 将来の拡張

- [ ] ロボットアーム制御の統合
- [ ] ディスペンサー制御の統合
- [ ] 3Dプリンター制御の統合
- [ ] 自動シーケンス実行機能
- [ ] データロギング・分析機能

---

詳細な機能要件、非機能要件については別途設計書を参照。
