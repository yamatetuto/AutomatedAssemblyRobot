#!/bin/bash
# 全サービス停止スクリプト

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🛑 マイクロサービス停止中..."

# PIDファイルから停止
for service in camera gripper gateway; do
    PID_FILE="logs/${service}.pid"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "  - ${service} Service停止 (PID: $PID)"
            kill "$PID"
            rm "$PID_FILE"
        else
            echo "  - ${service} Service は既に停止しています"
            rm "$PID_FILE"
        fi
    else
        echo "  - ${service} Service のPIDファイルが見つかりません"
    fi
done

# プロセス名でも停止（念のため）
pkill -f "python3.*services/camera/main.py" 2>/dev/null || true
pkill -f "python3.*services/gripper/main.py" 2>/dev/null || true
pkill -f "python3.*services/gateway/main.py" 2>/dev/null || true

echo ""
echo "✅ 全サービス停止完了"
