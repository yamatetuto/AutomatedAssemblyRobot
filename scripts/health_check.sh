#!/bin/bash
# ヘルスチェックスクリプト

echo "💊 サービスヘルスチェック"
echo "================================"

# Camera Service
echo -n "📹 Camera Service (8001): "
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    STATUS=$(curl -s http://localhost:8001/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "✅ $STATUS"
else
    echo "❌ 応答なし"
fi

# Gripper Service
echo -n "🤏 Gripper Service (8002): "
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    STATUS=$(curl -s http://localhost:8002/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "✅ $STATUS"
else
    echo "❌ 応答なし"
fi

# Gateway Service
echo -n "🌐 Gateway Service (8000): "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    STATUS=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "✅ $STATUS"
else
    echo "❌ 応答なし"
fi

echo "================================"
