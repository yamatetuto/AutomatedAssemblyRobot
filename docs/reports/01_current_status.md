# プロジェクト現状調査レポート

**作成日**: 2025-11-05  
**調査者**: GitHub Copilot  
**目的**: 自動組立ロボットシステムの既存実装状況を把握し、不足機能を洗い出す

---

## 1. プロジェクト概要

### 目的
積層型3Dプリンター、ディスペンサー、XYZ直交ロボットを組み合わせた医療機器の自動組立システムの開発。

### 対象デバイス
- **Raspberry Pi (x2)**: メイン制御用CPU
- **自動組立装置**: XYZ直交ロボット (X: 800mm, Y: 250mm, Z: 100mm)
- **3Dプリンター**: Tronxy社 GEMINI S (OctoPrint制御予定)
- **電動グリッパー**: IAI社 RCP2-GRSS (Modbus通信)
- **ディスペンサー**: I/O制御予定

---

## 2. 既存実装の分析

### 2.1 実装済み機能

#### ✅ カメラコントローラー (`camera_controller/`)
**ファイル構成**:
```
camera_controller/
├── CameraStreamer.py           # メインエントリーポイント
├── webrtc_index.html           # WebRTC UI
├── webrtc/
│   ├── streamer.py             # WebRTCサーバー実装
│   └── __init__.py
├── capture/
│   ├── opencv.py               # OpenCVキャプチャ実装
│   └── __init__.py
├── processor/
│   ├── processors.py           # 画像処理モジュール
│   └── __init__.py
├── snapshots/                  # スナップショット保存先
├── DEPENDENCIES.md             # 依存関係
├── INSTALL.md                  # インストールガイド
└── README_UPDATES.md           # 機能更新履歴
```

**実装済み機能**:
- ✅ OpenCV経由でのカメラキャプチャ
- ✅ WebRTCストリーミング (aiortc使用)
- ✅ カメラ設定値の取得・変更 (brightness, contrast, saturation, hue)
- ✅ スナップショット撮影・保存機能
- ✅ リアルタイムプレビュー
- ✅ Webブラウザベースの制御UI

**技術スタック**:
- OpenCV (cv2)
- aiortc (WebRTC)
- aiohttp (非同期Webサーバー)

**不足機能**:
- ❌ 画像処理アルゴリズム (`processor/processors.py` は空実装)
- ❌ 複数カメラ対応
- ❌ 物体検出・認識機能
- ❌ 座標キャリブレーション機能

---

#### ✅ グリッパーコントローラー (`gripper_controller/`)
**ファイル構成**:
```
gripper_controller/
├── CONController.py            # IAI社CONコントローラー制御
└── README.md                   # 使用方法
```

**実装済み機能**:
- ✅ IAI社製ポジショナーコントローラのModbus RTU通信
- ✅ サーボON/OFF制御
- ✅ 原点復帰
- ✅ 位置決め動作
- ✅ 現在位置・電流値・荷重データのモニタリング
- ✅ ステータス確認（サーボ準備完了、移動中、動作完了など）

**技術スタック**:
- minimalmodbus (Modbus RTU通信)
- pySerial

**不足機能**:
- ❌ 高レベルAPIラッパー（把持・開放などの抽象化）
- ❌ 力制御・押付け制御の実装例
- ❌ エラーハンドリングの拡張

---

### 2.2 未実装機能

#### ❌ 3Dプリンター制御
**要件**: OctoPrint経由での制御
- OctoPrint REST APIクライアントの実装が必要
- Gコード送信、プリント開始/停止、温度制御
- プリント状態のモニタリング

**推奨実装**:
- `printer_controller/OctoPrintController.py`
- `requests` ライブラリを使用したREST API通信

---

#### ❌ ディスペンサー制御
**要件**: I/O制御
- GPIO経由での制御 (Raspberry Pi)
- 接着剤吐出のタイミング制御
- 吐出量の制御

**推奨実装**:
- `dispenser_controller/DispenserController.py`
- `RPi.GPIO` または `gpiozero` ライブラリ使用

---

#### ❌ ロボットアーム制御の統合
**要件**: 企業提供のPythonライブラリを統合
- 既存ライブラリの場所と使用方法の確認が必要
- 座標変換・逆運動学の実装
- カメラ座標とロボット座標の変換

**推奨実装**:
- `robot_controller/RobotController.py`
- 企業ライブラリのラッパークラス

---

#### ❌ 統合制御システム
**要件**: 各コントローラーを統合した上位制御層
- 組立シーケンスの実行
- デバイス間の同期制御
- エラーハンドリングと回復処理
- ログ記録

**推奨実装**:
- `core/AssemblyController.py` (メイン制御クラス)
- `core/Sequencer.py` (シーケンス実行エンジン)

---

#### ❌ Webアプリケーション
**要件**: 各デバイスを一括制御できるWebアプリ
- ダッシュボードUI
- デバイス状態のリアルタイム表示
- 組立シーケンスの設定・実行
- カメラ映像の表示

**推奨実装**:
- FastAPI または Flask によるバックエンド
- React/Vue.js または単純なHTML/JSによるフロントエンド

---

## 3. ファイル構造の問題点

### 3.1 バックアップファイルの乱雑さ
以下の不要なバックアップファイルが散在:
```
camera_controller/webrtc/streamer_backup*.py (5ファイル)
camera_controller/webrtc_index_backup*.html (2ファイル)
```

**対応**: `.gitignore` に `*_backup*` を追加し、バックアップファイルは削除推奨

### 3.2 依存関係管理の不備
- `requirements.txt` が存在しない
- `setup.py` または `pyproject.toml` が存在しない
- インストール手順が各モジュールに分散

**対応**: プロジェクトルートに統一された依存関係ファイルを作成

### 3.3 ドキュメント不足
- プロジェクト全体のREADMEが簡素
- API仕様書が存在しない
- データ構造・スキーマの定義が不明確

**対応**: `docs/` ディレクトリの整備

---

## 4. 技術スタックの分析

### 4.1 確認済み依存ライブラリ
- `opencv-python` (cv2)
- `aiortc` (WebRTC)
- `aiohttp` (非同期HTTP)
- `minimalmodbus` (Modbus通信)
- `pyserial` (シリアル通信)

### 4.2 追加必要ライブラリ
- `requests` (OctoPrint API通信用)
- `RPi.GPIO` または `gpiozero` (ディスペンサー制御用)
- `fastapi` または `flask` (統合Webアプリ用)
- `uvicorn` (FastAPI用ASGIサーバー)
- `websockets` (リアルタイム通信用)
- `pydantic` (データバリデーション用)
- `pytest` (テスト用)

---

## 5. 優先度付き実装計画の提案

### フェーズ1: 基盤整備 🔧
1. プロジェクト構造の再編成
2. `requirements.txt` の作成
3. 不要ファイルの削除・整理
4. `docs/` ディレクトリの整備

### フェーズ2: コア機能実装 🚀
1. 3Dプリンター制御モジュール (`printer_controller/`)
2. ディスペンサー制御モジュール (`dispenser_controller/`)
3. ロボットアーム制御の統合 (`robot_controller/`)
4. 画像処理アルゴリズム (`camera_controller/processor/`)

### フェーズ3: 統合制御システム 🎯
1. 統合コントローラー (`core/AssemblyController.py`)
2. シーケンスエンジン (`core/Sequencer.py`)
3. 設定管理 (`config/`)

### フェーズ4: Webアプリケーション 🌐
1. FastAPI バックエンド
2. REST API設計
3. WebSocketによるリアルタイム通信
4. フロントエンドUI

### フェーズ5: テスト・デバッグ ✅
1. ユニットテスト
2. 統合テスト
3. 実機デバッグ

---

## 6. リスクと課題

### 6.1 不明点
- ❓ 企業提供のロボットライブラリの仕様・場所
- ❓ ディスペンサーの具体的な型番・I/O仕様
- ❓ 3DプリンターのOctoPrint設定状況
- ❓ Raspberry Pi 2台の役割分担

### 6.2 技術的課題
- ⚠️ リアルタイム性の確保 (PythonはGILがあるため)
- ⚠️ 座標キャリブレーション精度
- ⚠️ デバイス間の通信遅延
- ⚠️ エラー回復処理の設計

---

## 7. 次のアクション

### 即座に実施可能
1. ✅ `requirements.txt` の作成
2. ✅ バックアップファイルの削除
3. ✅ `docs/schema.md` でデータ構造を定義
4. ✅ `docs/requirements.md` で要件を整理

### ユーザーへの質問事項
1. ❓ 企業提供のロボット制御ライブラリの場所と使用方法
2. ❓ ディスペンサーの型番とI/O仕様
3. ❓ OctoPrintのIPアドレスとAPIキー
4. ❓ Raspberry Pi 2台の具体的な役割分担
5. ❓ 最優先で実装すべき機能

---

## まとめ

### 🎯 現状
- カメラ制御とグリッパー制御は既に実装済み
- 基本的なインフラは整っている

### ⚠️ 課題
- 3Dプリンター、ディスペンサー、ロボットアームの制御が未実装
- 統合制御システムが未構築
- プロジェクト構造の整理が必要

### 🚀 推奨アプローチ
1. まず基盤整備（依存関係、ドキュメント、構造整理）
2. 各デバイスの制御モジュールを独立して実装
3. 統合制御システムで各モジュールを連携
4. Webアプリで操作インターフェースを提供

---

**次のステップ**: `02_technical_research.md` で各デバイスの制御方法を技術調査
