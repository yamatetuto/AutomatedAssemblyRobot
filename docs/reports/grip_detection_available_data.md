# 把持判定に利用可能なデータと推奨手法

**日付**: 2025-11-09  
**制約**: 荷重データ(FBFC, 0x901E)は利用不可

## 1. 利用可能なデータソース

### A. 電流値モニター (CNOW) ✅ 利用可能
- **Modbusアドレス**: 0x900C
- **データ型**: 16ビット符号付き整数
- **用途**: モーター電流の監視
- **把持判定への活用**: 
  - 把持時は電流が上昇（対象物の抵抗）
  - 空振り時は電流が低い（無負荷）
  - 閾値判定で把持成功/失敗を判別可能

### B. 押付け空振りフラグ (PSFL) ✅ 利用可能
- **Modbusアドレス**: 0x9005（ビット11）
- **データ型**: ブール値
- **意味**: 
  - 0 = 正常に把持
  - 1 = 空振り（対象物なし）
- **把持判定への活用**: 
  - ハードウェアが直接判定
  - **最も信頼性が高い**

### C. 現在位置 (PNOW) ✅ 利用可能
- **Modbusアドレス**: 0x9000
- **データ型**: 16ビット符号付き整数
- **単位**: 0.01mm単位（片側）
- **把持判定への活用**: 
  - 目標位置と実際の停止位置の差を検出
  - 対象物のサイズ推定が可能
  - 滑り検出（時間経過で位置変化）

### D. 位置決め完了フラグ (PEND) ✅ 利用可能
- **Modbusアドレス**: 0x9005（ビット3）
- **データ型**: ブール値
- **把持判定への活用**: 
  - 移動完了を確認してから判定開始

### E. 移動中信号 (MOVE) ✅ 利用可能
- **Modbusアドレス**: 0x9007（ビット5）
- **データ型**: ブール値
- **把持判定への活用**: 
  - 移動中は判定を保留

### F. サーボON状態 (SV) ✅ 利用可能
- **Modbusアドレス**: 0x9005（ビット12）
- **データ型**: ブール値
- **把持判定への活用**: 
  - サーボOFF = 把持力なし

## 2. 推奨する把持判定ロジック

### レベル1: 基本判定（PSFL + 電流値）

```python
def check_grip_status_basic():
    """基本的な把持判定"""
    # ステータス読み取り
    status_dss1 = instrument.read_register(0x9005)
    psfl = (status_dss1 >> 11) & 0x1
    pend = (status_dss1 >> 3) & 0x1
    
    # 位置決め完了待ち
    if not pend:
        return {"status": "moving", "reason": "positioning"}
    
    # 空振りフラグチェック（最優先）
    if psfl == 1:
        return {
            "status": "failure",
            "reason": "empty_grip",
            "confidence": "high"
        }
    
    # 電流値チェック
    current = instrument.read_register(0x900C, signed=True)
    
    if current > GRIP_CURRENT_THRESHOLD:  # 例: 100
        return {
            "status": "success",
            "reason": "normal",
            "current": current,
            "confidence": "high"
        }
    else:
        return {
            "status": "warning",
            "reason": "low_current",
            "current": current,
            "confidence": "medium"
        }
```

### レベル2: 高度判定（位置差分 + 電流値 + PSFL）

```python
def check_grip_status_advanced(target_position_mm):
    """高度な把持判定（位置差分を利用）"""
    # ステータス読み取り
    status_dss1 = instrument.read_register(0x9005)
    psfl = (status_dss1 >> 11) & 0x1
    pend = (status_dss1 >> 3) & 0x1
    
    if not pend:
        return {"status": "moving", "reason": "positioning"}
    
    # 現在位置読み取り（0.01mm単位）
    current_pos_raw = instrument.read_register(0x9000, signed=True)
    current_pos_mm = current_pos_raw * 0.01
    
    # 電流値読み取り
    current = instrument.read_register(0x900C, signed=True)
    
    # 位置差分計算
    position_error = abs(target_position_mm - current_pos_mm)
    
    # 判定ロジック
    if psfl == 1:
        return {
            "status": "failure",
            "reason": "empty_grip",
            "current": current,
            "position_mm": current_pos_mm,
            "target_mm": target_position_mm,
            "error_mm": position_error,
            "confidence": "high"
        }
    
    # 位置差分が大きい = 対象物があって手前で停止
    if position_error > 0.5:  # 0.5mm以上のずれ
        if current > GRIP_CURRENT_THRESHOLD:
            return {
                "status": "success",
                "reason": "object_detected",
                "object_size_mm": position_error * 2,  # 両側
                "current": current,
                "position_mm": current_pos_mm,
                "confidence": "high"
            }
        else:
            return {
                "status": "warning",
                "reason": "obstacle_low_current",
                "current": current,
                "position_mm": current_pos_mm,
                "confidence": "medium"
            }
    
    # 位置差分が小さい + 電流高い = 薄い対象物
    elif current > GRIP_CURRENT_THRESHOLD:
        return {
            "status": "success",
            "reason": "thin_object",
            "current": current,
            "position_mm": current_pos_mm,
            "confidence": "medium"
        }
    
    # 位置差分小 + 電流低 = 把持失敗の可能性
    else:
        return {
            "status": "failure",
            "reason": "no_grip_force",
            "current": current,
            "position_mm": current_pos_mm,
            "confidence": "medium"
        }
```

### レベル3: 時系列判定（滑り検出）

```python
def check_grip_stability(duration_sec=2.0, interval_sec=0.1):
    """把持安定性チェック（滑り検出）"""
    positions = []
    currents = []
    
    iterations = int(duration_sec / interval_sec)
    
    for _ in range(iterations):
        pos = instrument.read_register(0x9000, signed=True) * 0.01
        cur = instrument.read_register(0x900C, signed=True)
        
        positions.append(pos)
        currents.append(cur)
        
        time.sleep(interval_sec)
    
    # 位置変動の標準偏差
    pos_std = statistics.stdev(positions) if len(positions) > 1 else 0
    
    # 電流変動の標準偏差
    cur_std = statistics.stdev(currents) if len(currents) > 1 else 0
    
    if pos_std > 0.1:  # 0.1mm以上の変動 = 滑り
        return {
            "status": "warning",
            "reason": "slipping",
            "position_variation_mm": pos_std,
            "confidence": "high"
        }
    elif cur_std > 20:  # 電流変動が大きい = 不安定
        return {
            "status": "warning",
            "reason": "unstable_grip",
            "current_variation": cur_std,
            "confidence": "medium"
        }
    else:
        return {
            "status": "stable",
            "reason": "normal",
            "confidence": "high"
        }
```

## 3. 把持に必要な追加情報の提案

### 現在取得できているデータで十分ですが、以下があればより精度向上可能：

#### A. 対象物の事前情報
- **対象物の想定サイズ（厚み）**
  - 目標位置と実際の停止位置を比較して検証
  - 異物混入やサイズ違い部品の検出

- **対象物の想定重量**
  - 荷重データは取れないが、電流値から間接的に推定可能
  - 重い物 = 高電流が必要

- **対象物の材質（硬さ・滑りやすさ）**
  - 金属 vs プラスチック vs ゴム
  - 把持判定の閾値を材質ごとに調整

#### B. グリッパー校正データ
- **無負荷時の基準電流値**
  - 起動時に自動測定
  - 温度変化による電流値のドリフト補正

- **各ポジションでの基準電流値**
  - ポジションごとに電流の基準値が異なる可能性
  - ポジションテーブルに保存

#### C. 環境データ（オプション）
- **グリッパーの動作回数（摩耗監視）**
  - 長期使用で把持力が低下
  - 閾値の自動調整

- **温度（モーター温度）**
  - 温度上昇で電流値が変化
  - アラーム判定に使用

## 4. 実装推奨順序

### フェーズ1: 基本実装（最小限）
1. ✅ PSFL（空振りフラグ）による判定
2. ✅ 電流値閾値判定
3. ✅ API実装 (`GET /api/gripper/grip_status`)

### フェーズ2: 精度向上
4. 位置差分による対象物サイズ推定
5. 電流値の校正（無負荷時基準値の自動測定）
6. 材質・サイズ別の閾値設定UI

### フェーズ3: 高度機能
7. 時系列監視（滑り検出）
8. 統計データ収集（成功率、平均電流値など）
9. 機械学習による把持判定（オプション）

## 5. 最初に実装すべきデータ取得

### 優先度1: 必須データ
```python
# これだけで基本的な把持判定が可能
- PSFL (0x9005, bit 11)  # 空振り判定
- CNOW (0x900C)          # 電流値
- PEND (0x9005, bit 3)   # 完了確認
```

### 優先度2: 精度向上
```python
# 対象物サイズ推定に使用
- PNOW (0x9000)          # 現在位置
- target_position        # 目標位置（ポジションテーブルから）
```

### 優先度3: 安定性監視
```python
# 継続的な監視
- PNOW の時系列データ   # 滑り検出
- CNOW の時系列データ   # 電流変動監視
```

## 6. 校正手順の提案

### 初期校正
1. **無負荷電流の測定**
   - グリッパーを完全に開いた状態で電流値測定
   - 各ポジションで閉じた状態（空振り）の電流値測定

2. **標準サンプルでの測定**
   - 既知のサイズ・重量の対象物を把持
   - 成功時の電流値を記録
   - 閾値を決定

3. **異常ケースの測定**
   - 対象物なし（空振り）
   - 異なるサイズ
   - 滑りやすい対象物

### データ例

| 状態 | PSFL | 電流値(CNOW) | 位置差分(mm) | 判定 |
|------|------|--------------|--------------|------|
| 空振り | 1 | 50 | 0.0 | 失敗 |
| 正常把持（薄） | 0 | 150 | 0.5 | 成功 |
| 正常把持（厚） | 0 | 200 | 2.0 | 成功 |
| 異物 | 0 | 80 | 1.5 | 警告 |

## 7. まとめ

### 必要十分なデータ（現在利用可能）
- ✅ PSFL（空振りフラグ）: 最も信頼性が高い
- ✅ 電流値（CNOW）: 把持力の間接測定
- ✅ 現在位置（PNOW）: 対象物サイズ推定

### これだけで実現可能な機能
- 把持成功/失敗の判定（精度: 高）
- 対象物のサイズ推定（精度: 中）
- 滑り検出（精度: 中）
- 異常検出（精度: 中）

### 荷重データがなくても問題なし
電流値と位置データの組み合わせで十分な把持判定が可能です。
