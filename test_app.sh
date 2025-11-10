#!/bin/bash
# 統合アプリケーションのテストスクリプト

echo "=== 統合アプリケーションテスト ==="
echo ""

# アプリが起動しているか確認
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "❌ アプリケーションが起動していません"
    echo "起動してください: python app.py"
    exit 1
fi

echo "✅ アプリケーション起動中"
echo ""

# ヘルスチェック
echo "--- ヘルスチェック ---"
curl -s http://localhost:8080/health | python -m json.tool
echo ""

# カメラコントロール取得
echo "--- カメラコントロール ---"
curl -s http://localhost:8080/api/camera/controls | python -m json.tool | head -20
echo "..."
echo ""

# グリッパーステータス
echo "--- グリッパーステータス ---"
curl -s http://localhost:8080/api/gripper/status | python -m json.tool
echo ""

echo "=== テスト完了 ==="
