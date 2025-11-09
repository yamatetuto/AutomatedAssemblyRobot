# 電流値モニタリングと把持判定機能の実装

**日付**: 2025-11-09  
**作業者**: GitHub Copilot  
**バージョン**: v2.2

## 概要

グリッパーの電流値モニタリングと把持状態判定機能を実装しました。Chart.jsによるリアルタイムグラフ表示、Modbus排他制御によるタイムアウト対策を含みます。

---

## 実装した機能

### 1. 電流値モニタリング

#### API実装
- **エンドポイント**: `GET /api/gripper/current`
- **レスポンス**: `{"status": "ok", "current": 150}` (mA単位)
- **Modbusレジスタ**: `0x900C` (CNOW - 現在電流値)
- **実装箇所**: `src/gripper/gripper_manager.py::get_current()`

#### UI実装
- **グラフライブラリ**: Chart.js 4.4.0
- **更新間隔**: 500ms
- **データポイント**: 60ポイント（ローリングバッファ）
- **グラフタイプ**: ラインチャート（緑色）
- **実装箇所**: `web_app/static/js/app.js::startCurrentMonitor()`

#### 特徴
- リアルタイム更新
- スムーズなアニメーション
- 自動スケーリング
- パネル開閉でモニタリングON/OFF

### 2. 把持状態判定

#### API実装
- **エンドポイント**: `GET /api/gripper/grip_status`
- **パラメータ**: `target_position` (オプション)
- **レスポンス**:
```json
{
  "status": "success",  // "success" | "failure" | "warning" | "moving"
  "reason": "normal",
  "current": 150,
  "position_mm": 45.23,
  "psfl": false,
  "confidence": "high"
}
```

#### 判定ロジック

**優先順位**:
1. **移動中判定** - MOVEビット（0x9007 bit 5）が1の場合
   - ステータス: `"moving"`
   - 理由: `"positioning"`

2. **空振り判定** - PSFLビット（0x9005 bit 11）が1の場合
   - ステータス: `"failure"`
   - 理由: `"empty_grip"`
   - 信頼度: `"high"`

3. **電流値判定** - PSFL=0の場合
   - 閾値: 100mA (調整可能)
   - 電流 > 閾値: `"success"` / `"normal"` / `"high"`
   - 電流 ≤ 閾値: `"warning"` / `"low_current"` / `"medium"`

#### UI実装
- **LEDインジケーター**: 緑(成功)/赤(失敗)/黄(警告)/青(移動中)
- **ステータステキスト**: 日本語表示
- **詳細情報**: 電流値、位置、理由を表示
- **実装箇所**: `web_app/static/js/app.js::checkGripStatus()`

### 3. Modbus排他制御

#### 問題
- 複数のAPIリクエストが同時にModbusアクセスし、タイムアウトエラー発生
- エラーメッセージ: `"No communication with the instrument (no answer)"`

#### 解決策
- **`asyncio.Lock()`による排他制御**
- すべてのModbus操作を非同期化（`asyncio.to_thread()`）
- 実装箇所: `src/gripper/gripper_manager.py::__init__()`

```python
class GripperManager:
    def __init__(self):
        self._modbus_lock = asyncio.Lock()
        
    async def get_current(self):
        async with self._modbus_lock:
            current = await asyncio.to_thread(
                self.controller.instrument.read_register, 0x900C
            )
            return current
```

#### 対象メソッド
- `get_status()` - 非同期化してロック追加
- `servo_on()` / `servo_off()` - ロック追加
- `home()` - ロック追加
- `move_to_position()` - ロック追加
- `get_position_table()` - 非同期化してロック追加
- `update_position_table()` - 非同期化してロック追加
- `get_current()` - ロック追加
- `check_grip_status()` - ロック追加（内部で電流値を直接読み取り）

### 4. PEND信号からMOVE信号への変更

#### 問題
- PENDビット（0x9005 bit 3）が位置決め完了後に立ち上がらない問題
- 「ポジション位置移動後になぜかPENDが立ち上がらない問題」

#### 解決策
- **MOVEビット（0x9007 bit 5）を使用**
- レジスタ: 0x9007 (DSSE - 拡張デバイスステータス)
- ビット5: MOVE（移動中信号）
- MOVE=1: 移動中 → ステータス `"moving"`
- MOVE=0: 停止中 → 把持判定を実行

#### メリット
- より信頼性の高い移動検出
- ハードウェア信号による正確な状態把握
- PENDの不安定性を回避

### 5. CSS/JS分離

#### 背景
- HTMLファイルが1008行と肥大化
- 保守性の低下

#### 実装
- **CSS**: `web_app/static/css/style.css` (12,777文字)
- **JS**: `web_app/static/js/app.js` (25,937文字)
- キャッシュバスティング: `?v=1762686546`

#### 効果
- HTMLの可読性向上
- CSS/JSの再利用性向上
- ブラウザキャッシュの効率化

---

## バグ修正

### 1. Chart.js高さ問題
**症状**: グラフが縦に無限に拡大

**原因**: `height: auto !important;` がChart.jsの高さ設定を上書き

**修正**: `max-height: 250px;` に変更

**ファイル**: `web_app/static/css/style.css` line 385-388

### 2. スナップショットURL修正
**症状**: スナップショット一覧が表示されない

**原因**: URL `/api/camera/snapshot/` (singular) vs `/api/camera/snapshots/` (plural)

**修正**: `app.js`の`loadSnapshots()`で正しいURLに修正

### 3. app.py重複エンドポイント
**症状**: IndentationError

**原因**: `/api/camera/snapshots`エンドポイントが重複定義

**修正**: 重複コード削除、不要な`/api/camera/resolution`復元

---

## 既知の課題

### 電流値取得の安定性

**症状**:
- 電流値取得時に間欠的にタイムアウトエラー発生
- `"No communication with the instrument (no answer)"`

**現状の対策**:
- ✅ Modbus排他制御実装（`asyncio.Lock()`）
- ✅ 取得間隔を500msに延長（負荷軽減）
- ✅ すべてのModbus操作を非同期化

**今後の対策案**:
1. 取得間隔のさらなる延長（500ms → 1000ms）
2. Modbusタイムアウト値の調整（現在2.0秒）
3. リトライロジックの実装
4. エラー時のフォールバック処理

**推定原因**:
- Modbus通信の物理的な制約（RS-485）
- グリッパー側のレスポンス遅延
- 複数操作の同時実行による輻輳

---

## 技術的詳細

### Modbusレジスタマップ

| アドレス | 名称 | 説明 | 使用箇所 |
|---------|------|------|---------|
| 0x900C | CNOW | 現在電流値（mA） | 電流値モニタリング |
| 0x9005 | DSS1 | デバイスステータス1 | PSFL（bit 11） |
| 0x9007 | DSSE | 拡張デバイスステータス | MOVE（bit 5） |
| 0x9000 | PNOW | 現在位置（0.01mm単位） | 位置表示 |

### Chart.js設定

```javascript
{
  type: 'line',
  data: {
    labels: [],  // タイムスタンプ
    datasets: [{
      label: '電流値 (mA)',
      data: [],
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,  // パフォーマンス優先
    scales: {
      y: { beginAtZero: true }
    }
  }
}
```

---

## パフォーマンス

### API応答時間
- 電流値取得: ~0.1秒（成功時）、タイムアウト時2秒
- 把持状態判定: ~0.2秒（レジスタ複数読み取り）
- グリッパーステータス: ~0.14秒

### UI更新頻度
- 電流値グラフ: 500ms間隔
- グリッパーステータス: 2秒間隔
- 把持状態: マニュアル取得

---

## ファイル一覧

### 変更ファイル
- `app.py` - エンドポイント追加、重複削除
- `src/gripper/gripper_manager.py` - Modbusロック、電流値/把持判定実装
- `src/gripper/controller.py` - PEND関連コメントアウト（既存）
- `web_app/static/css/style.css` - 新規作成、Chart.js高さ修正
- `web_app/static/js/app.js` - 新規作成、UIロジック実装
- `web_app/templates/index_webrtc_fixed.html` - パネル追加、CSS/JS分離
- `README.md` - v2.2への更新、機能追加記載
- `docs/requirements.md` - API仕様更新

### 調査レポート（新規）
- `docs/reports/camera_high_resolution_issue.md`
- `docs/reports/grip_detection_available_data.md`
- `docs/reports/gripper_current_and_grip_detection.md`
- `docs/reports/multi_raspberry_pi_architecture.md`

---

## 次のステップ

### 短期（次回セッション）
1. **電流値取得の安定化**
   - タイムアウトエラーの根本原因調査
   - リトライロジック実装
   - エラーハンドリング改善

2. **把持判定の精度向上**
   - 電流閾値の実機調整
   - 位置差分判定の追加
   - 信頼度計算の改善

### 中期
1. **画像処理統合**
   - 物体検出による把持確認
   - カメラ映像との同期表示

2. **シーケンス制御**
   - 自動把持シーケンス実装
   - エラーリカバリー処理

### 長期
1. **3Dプリンター統合**
   - OctoPrint API連携
   - 印刷完了検出

2. **ロボットアーム統合**
   - XYZ直交ロボット制御
   - 協調動作実装

---

## まとめ

### 達成したこと
- ✅ 電流値リアルタイムモニタリング
- ✅ 把持状態の多重判定ロジック
- ✅ Modbus排他制御による安定性向上
- ✅ PEND→MOVE信号への切り替え
- ✅ CSS/JS分離による保守性向上
- ✅ Chart.js高さ問題修正
- ✅ ドキュメント整備

### 残課題
- ⚠️ 電流値取得の安定性向上（継続中）
- 📋 把持判定精度の実機調整
- 📋 エラーハンドリングの改善

### 学んだこと
- Modbus通信の排他制御の重要性
- Chart.jsのレスポンシブ設定の注意点
- ハードウェア信号の信頼性の違い（PEND vs MOVE）
- 非同期処理とロック機構の適切な使い分け

---

**作成日**: 2025-11-09  
**次回作業**: 電流値取得の安定化、把持判定の実機調整
