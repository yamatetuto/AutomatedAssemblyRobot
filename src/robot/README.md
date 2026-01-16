# ロボット専用デーモン運用 (2026-01-16)

## 目的
- ロボット制御のみrootで起動し、app.pyは通常ユーザーで運用
- sudo pip を避け、WebRTC/カメラ/UIの依存を分離

---

## 1. ロボットデーモン起動 (root)
```bash
cd /home/splebopi/SPLEBO/AutomatedAssemblyRobot
sudo python robot_daemon.py
```

ポート: `8081`

---

## 2. メインアプリ起動 (ユーザー)
```bash
export ROBOT_REMOTE_BASE_URL=http://127.0.0.1:8081
cd /home/splebopi/SPLEBO/AutomatedAssemblyRobot
python app.py
```

---

## 3. 動作確認
```bash
curl http://127.0.0.1:8081/health
curl http://127.0.0.1:8080/api/robot/config
```

---

## 5. ロボット動作手順（実運用）
1) ロボットデーモン起動（root）
```bash
cd /home/splebopi/SPLEBO/AutomatedAssemblyRobot
sudo python robot_daemon.py
```

2) メインアプリ起動（ユーザー）
```bash
export ROBOT_REMOTE_BASE_URL=http://127.0.0.1:8081
cd /home/splebopi/SPLEBO/AutomatedAssemblyRobot
python app.py
```

3) UI で動作
- 画面の「🧭 SPLEBO-N 制御」パネルを開く
- 現在位置が 1 秒ごとに更新される
- 「🏠 原点復帰」/「JOG」/「💾 現在位置を登録」/「🎯 ポイントへ移動」/「⛔ 停止」を使用

4) 停止
- robot_daemon と app.py を Ctrl+C で停止（ロボットはクローズ処理される）

---

## 6. スクリプトでの起動/停止
- 起動: `scripts/start_robot_app.sh`
- 停止: `scripts/stop_robot_app.sh`

起動時は sudo 認証が必要です（robot_daemon 起動のため）。

---

## 4. フォールバック
- `ROBOT_REMOTE_BASE_URL` 未設定の場合は app.py がローカルロボットを起動
- 接続後はローカルロボットを停止してリモートに切り替え
