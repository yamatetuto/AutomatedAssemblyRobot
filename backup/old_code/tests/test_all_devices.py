#!/usr/bin/env python3
"""
全デバイス動作確認スクリプト
カメラとグリッパーの動作を一括確認
"""
import sys
import subprocess

def run_test(script_name, description):
    """テストスクリプトを実行"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print('='*60)
    
    result = subprocess.run(
        ["python3", script_name],
        cwd="/home/pi/assembly/AutomatedAssemblyRobot"
    )
    
    return result.returncode == 0

def main():
    print("🚀 自動組立ロボット - デバイス動作確認")
    print("="*60)
    
    tests = [
        ("tests/test_camera_check.py", "カメラ動作確認"),
        ("tests/test_gripper_check.py", "グリッパー動作確認"),
    ]
    
    results = {}
    for script, description in tests:
        results[description] = run_test(script, description)
    
    # 結果サマリー
    print("\n" + "="*60)
    print("📊 テスト結果サマリー")
    print("="*60)
    
    for description, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"  {description}: {status}")
    
    all_success = all(results.values())
    
    print()
    if all_success:
        print("🎉 すべてのデバイスが正常に動作しています！")
    else:
        print("⚠️ 一部のデバイスに問題があります。上記のログを確認してください。")
    
    print("="*60)
    
    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
