#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/splebopi/SPLEBO/AutomatedAssemblyRobot"

cd "$PROJECT_ROOT"

LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

ROBOT_LOG="$LOG_DIR/robot_daemon.log"
APP_LOG="$LOG_DIR/app.log"

export ROBOT_REMOTE_BASE_URL="http://127.0.0.1:8081"
export CAMERA_REMOTE_BASE_URL="http://10.32.77.150:8080"

if ! sudo -v; then
	echo "[error] sudo認証に失敗しました。robot_daemonは起動されません。"
	exit 1
fi

echo "[start] robot_daemon.py (sudo)"
nohup sudo python "$PROJECT_ROOT/robot_daemon.py" > "$ROBOT_LOG" 2>&1 &

sleep 1

echo "[start] app.py"
nohup python "$PROJECT_ROOT/app.py" > "$APP_LOG" 2>&1 &

echo "robot_daemon log: $ROBOT_LOG"

echo "app log: $APP_LOG"

echo "done"
