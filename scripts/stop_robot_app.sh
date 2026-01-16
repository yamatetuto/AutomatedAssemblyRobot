#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/splebopi/SPLEBO/AutomatedAssemblyRobot"

cd "$PROJECT_ROOT"

echo "[stop] app.py"
if pgrep -f "python .*app.py" >/dev/null 2>&1; then
  pkill -f "python .*app.py"
  echo "app.py stopped"
else
  echo "app.py not running"
fi

echo "[stop] robot_daemon.py (sudo)"
if sudo pgrep -f "python .*robot_daemon.py" >/dev/null 2>&1; then
  sudo pkill -f "python .*robot_daemon.py"
  echo "robot_daemon.py stopped"
else
  echo "robot_daemon.py not running"
fi


echo "done"
