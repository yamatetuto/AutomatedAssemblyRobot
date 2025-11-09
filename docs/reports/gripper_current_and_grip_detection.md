# グリッパー電流値監視と把持判定機能の調査レポート

**日付**: 2025-11-09  
**要件**: 
1. 電流値をリアルタイムで読み取り、波形として表示
2. グリッパによる把持が成功したか失敗したかを表示

## 1. 利用可能なデータソース

### A. 電流値モニター (CNOW)
- **Modbusアドレス**: 0x900C
- **データ型**: 16ビット符号付き整数
- **用途**: モーター電流の監視
- **単位**: 要確認（通常はmAまたはA）
- **更新頻度**: リアルタイム（数ms単位）

### B. 荷重データ (FBFC)
- **Modbusアドレス**: 0x901E
- **データ型**: 16ビット符号付き整数
- **用途**: ロードセル値（把持力）
- **単位**: 要確認（通常はN）
- **更新頻度**: リアルタイム

### C. 押付け空振りフラグ (PSFL)
- **Modbusアドレス**: 0x9005 (ビット11)
- **データ型**: ブール値
- **意味**: 
  - 0 = 正常に把持
  - 1 = 空振り（対象物なし）
- **用途**: 把持成功/失敗の直接判定

## 2. 把持判定ロジック

### 優先度1: 押付け空振りフラグ (PSFL)
```python
status = read_register(0x9005)
psfl = (status >> 11) & 0x1

if psfl == 1:
    return "把持失敗（空振り）"
elif psfl == 0:
    return "把持成功"
```

**利点**:
- ハードウェアが直接判定
- 最も信頼性が高い
- 追加計算不要

### 優先度2: 電流値閾値判定
```python
current = read_register(0x900C)

if current > GRIP_CURRENT_THRESHOLD:
    return "把持成功（負荷検出）"
else:
    return "把持失敗（無負荷）"
```

**利点**:
- 把持力の強弱を判定可能
- 部品の重さ・サイズの判別に使用可能

### 優先度3: 荷重データ判定
```python
load = read_register(0x901E)

if load > GRIP_FORCE_THRESHOLD:
    return "把持成功"
else:
    return "把持失敗"
```

**利点**:
- より正確な把持力測定
- 滑りの検出に使用可能

### 推奨: 複合判定
```python
def check_grip_status():
    status = read_register(0x9005)
    psfl = (status >> 11) & 0x1
    
    current = read_register(0x900C)
    load = read_register(0x901E)
    
    # 空振りフラグが最優先
    if psfl == 1:
        return {
            "status": "failure",
            "reason": "empty_grip",
            "current": current,
            "load": load
        }
    
    # 荷重データで詳細判定
    if load < WEAK_GRIP_THRESHOLD:
        return {
            "status": "warning",
            "reason": "weak_grip",
            "current": current,
            "load": load
        }
    
    return {
        "status": "success",
        "reason": "normal",
        "current": current,
        "load": load
    }
```

## 3. 電流値波形表示の実装計画

### バックエンド実装

#### 3.1 新しいAPIエンドポイント

```python
# GET /api/gripper/current
# 現在の電流値を取得（単発）

# GET /api/gripper/current/stream (WebSocket)
# リアルタイム電流値ストリーム

# GET /api/gripper/load
# 現在の荷重データを取得

# GET /api/gripper/grip_status
# 把持状態の判定結果
```

#### 3.2 GripperManagerへのメソッド追加

```python
class GripperManager:
    def get_current(self) -> int:
        """電流値を取得"""
        return self.controller.instrument.read_register(0x900C, signed=True)
    
    def get_load(self) -> int:
        """荷重データを取得"""
        return self.controller.instrument.read_register(0x901E, signed=True)
    
    def check_grip_status(self) -> dict:
        """把持状態を判定"""
        status_reg = self.controller.instrument.read_register(0x9005)
        psfl = (status_reg >> 11) & 0x1
        current = self.get_current()
        load = self.get_load()
        
        if psfl == 1:
            return {"status": "failure", "reason": "empty", "current": current, "load": load}
        elif load < 50:  # 閾値は要調整
            return {"status": "warning", "reason": "weak", "current": current, "load": load}
        else:
            return {"status": "success", "reason": "normal", "current": current, "load": load}
```

### フロントエンド実装

#### 3.3 波形表示ライブラリの選択

**推奨: Chart.js**
- 軽量（約200KB）
- リアルタイム更新対応
- レスポンシブ
- カスタマイズ性が高い

**代替: Plotly.js**
- インタラクティブ性が高い
- より高機能だが重い（約3MB）

#### 3.4 HTML/JavaScript実装例

```html
<!-- 電流値波形表示エリア -->
<div class="card">
    <div class="card-header">
        <h3>電流値モニター</h3>
    </div>
    <div class="card-body">
        <canvas id="currentChart" width="400" height="200"></canvas>
        <div class="current-value">
            <span>現在値: </span>
            <span id="currentValue">0</span> mA
        </div>
    </div>
</div>

<!-- 把持状態表示 -->
<div class="card">
    <div class="card-header">
        <h3>把持状態</h3>
    </div>
    <div class="card-body">
        <div id="gripStatus" class="grip-status">
            <div class="status-indicator"></div>
            <span class="status-text">待機中</span>
        </div>
        <div class="grip-details">
            <p>電流値: <span id="gripCurrent">-</span> mA</p>
            <p>荷重: <span id="gripLoad">-</span> N</p>
        </div>
    </div>
</div>

<script>
// Chart.js初期化
const ctx = document.getElementById('currentChart').getContext('2d');
const currentChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: '電流値 (mA)',
            data: [],
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1,
            fill: false
        }]
    },
    options: {
        responsive: true,
        animation: false,  // リアルタイム更新のため無効化
        scales: {
            x: {
                display: true,
                title: {
                    display: true,
                    text: '時間'
                }
            },
            y: {
                display: true,
                title: {
                    display: true,
                    text: '電流値 (mA)'
                }
            }
        }
    }
});

// 電流値のポーリング（250ms間隔）
setInterval(async () => {
    const response = await fetch('/api/gripper/current');
    const data = await response.json();
    
    if (data.status === 'ok') {
        const now = new Date();
        const timeLabel = now.toLocaleTimeString();
        
        // グラフ更新（最大100データポイント）
        currentChart.data.labels.push(timeLabel);
        currentChart.data.datasets[0].data.push(data.current);
        
        if (currentChart.data.labels.length > 100) {
            currentChart.data.labels.shift();
            currentChart.data.datasets[0].data.shift();
        }
        
        currentChart.update();
        
        // 現在値表示更新
        document.getElementById('currentValue').textContent = data.current;
    }
}, 250);

// 把持状態の確認（移動完了後など、イベントドリブン）
async function checkGripStatus() {
    const response = await fetch('/api/gripper/grip_status');
    const data = await response.json();
    
    const statusDiv = document.getElementById('gripStatus');
    const statusText = statusDiv.querySelector('.status-text');
    const indicator = statusDiv.querySelector('.status-indicator');
    
    if (data.status === 'success') {
        statusText.textContent = '把持成功';
        indicator.className = 'status-indicator success';
    } else if (data.status === 'warning') {
        statusText.textContent = '把持弱い';
        indicator.className = 'status-indicator warning';
    } else {
        statusText.textContent = '把持失敗（空振り）';
        indicator.className = 'status-indicator failure';
    }
    
    document.getElementById('gripCurrent').textContent = data.current;
    document.getElementById('gripLoad').textContent = data.load;
}
</script>

<style>
.grip-status {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 15px;
}

.status-indicator {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background-color: #gray;
}

.status-indicator.success {
    background-color: #28a745;
    box-shadow: 0 0 10px #28a745;
}

.status-indicator.warning {
    background-color: #ffc107;
    box-shadow: 0 0 10px #ffc107;
}

.status-indicator.failure {
    background-color: #dc3545;
    box-shadow: 0 0 10px #dc3545;
}

.status-text {
    font-size: 1.2em;
    font-weight: bold;
}

.current-value {
    margin-top: 10px;
    font-size: 1.5em;
    text-align: center;
}
</style>
```

## 4. 実装の優先順位

### フェーズ1: 基本実装
1. ✅ 電流値読み取りAPIエンドポイント (`GET /api/gripper/current`)
2. ✅ 荷重データ読み取りAPIエンドポイント (`GET /api/gripper/load`)
3. ✅ 把持状態判定APIエンドポイント (`GET /api/gripper/grip_status`)
4. ✅ GripperManagerへのメソッド追加

### フェーズ2: フロントエンド
5. Chart.jsの追加（CDN経由）
6. 電流値波形表示の実装
7. 把持状態インジケーターの実装
8. UIのスタイリング

### フェーズ3: 最適化
9. WebSocketによるリアルタイムストリーム（オプション）
10. データ保存機能（CSV/JSON出力）
11. 閾値の調整UI
12. アラーム通知機能

## 5. 必要な追加ライブラリ

### バックエンド
- なし（既存のminimalmodbusで対応可能）

### フロントエンド
```html
<!-- Chart.js (CDN) -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

## 6. 事前調査項目

### 実機テストで確認すべき事項
1. **電流値の単位とスケール**
   - 0x900Cから読み取った値の実際の単位
   - スケーリング係数の確認
   
2. **荷重データの単位とスケール**
   - 0x901Eから読み取った値の実際の単位
   - スケーリング係数の確認

3. **押付け空振りフラグの動作確認**
   - 実際に空振りさせた時のフラグ挙動
   - 正常把持時のフラグ挙動

4. **適切な閾値の決定**
   - 様々な対象物での電流値・荷重値の測定
   - 成功/失敗/警告の境界値の決定

## 7. 次のステップ

1. **実機で電流値・荷重データの読み取りテスト**
   ```python
   # テストスクリプト
   import minimalmodbus
   
   instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1, mode='rtu')
   instrument.serial.baudrate = 38400
   instrument.serial.timeout = 2.0
   
   while True:
       current = instrument.read_register(0x900C, signed=True)
       load = instrument.read_register(0x901E, signed=True)
       status = instrument.read_register(0x9005)
       psfl = (status >> 11) & 0x1
       
       print(f"電流: {current}, 荷重: {load}, PSFL: {psfl}")
       time.sleep(0.1)
   ```

2. **単位とスケールの特定**
3. **APIエンドポイントの実装**
4. **フロントエンド実装**
5. **閾値のキャリブレーション**
