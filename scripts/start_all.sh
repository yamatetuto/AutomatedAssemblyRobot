#!/bin/bash
# 全サービス起動スクリプト

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 マイクロサービス起動中..."

# ログディレクトリ作成
mkdir -p logs

# Camera Service起動
echo "📹 Camera Service起動 (port 8001)..."
cd services/camera
nohup python3 main.py > ../../logs/camera_service.log 2>&1 &
CAMERA_PID=$!
echo $CAMERA_PID > ../../logs/camera.pid
cd ../..
sleep 2

# Gripper Service起動
echo "�� Gripper Service起動 (port 8002)..."
cd services/gripper
nohup python3 main.py > ../../logs/gripper_service.log 2>&1 &
GRIPPER_PID=$!
echo $GRIPPER_PID > ../../logs/gripper.pid
cd ../..
sleep 2

# Gateway Service起動
echo "🌐 Gateway Service起動 (port 8000)..."
cd services/gateway
nohup python3 main.py > ../../logs/gateway_service.log 2>&1 &
GATEWAY_PID=$!
echo $GATEWAY_PID > ../../logs/gateway.pid
cd ../..
sleep 2

echo ""
echo "✅ 全サービス起動完了！"
echo ""
echo "📊 サービス状態:"
echo "  - Camera Service:  PID $CAMERA_PID  (http://localhost:8001)"
echo "  - Gripper Service: PID $GRIPPER_PID (http://localhost:8002)"
echo "  - Gateway Service: PID $GATEWAY_PID (http://localhost:8000)"
echo ""
echo "🌐 Web UI: http://localhost:8000"
echo ""
echo "📝 ログファイル:"
echo "  - logs/camera_service.log"
echo "  - logs/gripper_service.log"
echo "  - logs/gateway_service.log"
echo ""
echo "🛑 停止: ./scripts/stop_all.sh"
echo "💊 ヘルスチェック: ./scripts/health_check.sh"
