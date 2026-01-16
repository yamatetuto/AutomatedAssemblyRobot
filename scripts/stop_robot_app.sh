#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/splebopi/SPLEBO/AutomatedAssemblyRobot"

cd "$PROJECT_ROOT"

echo "[stop] gripper servo off"
if command -v curl >/dev/null 2>&1; then
  curl -s -m 2 -X POST http://127.0.0.1:8080/api/gripper/servo/off >/dev/null 2>&1 || true
else
  echo "curl not found; skipping servo off request"
fi

echo "[stop] app.py"
if pgrep -f "python .*app.py" >/dev/null 2>&1; then
  pkill -TERM -f "python .*app.py"
  for i in {1..10}; do
    if ! pgrep -f "python .*app.py" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
  if pgrep -f "python .*app.py" >/dev/null 2>&1; then
    echo "app.py did not stop, sending SIGKILL"
    pkill -KILL -f "python .*app.py"
  fi
  echo "app.py stopped"
else
  echo "app.py not running"
fi

echo "[stop] robot_daemon.py (sudo)"
if sudo pgrep -f "python .*robot_daemon.py" >/dev/null 2>&1; then
  sudo pkill -TERM -f "python .*robot_daemon.py"
  for i in {1..10}; do
    if ! sudo pgrep -f "python .*robot_daemon.py" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
  if sudo pgrep -f "python .*robot_daemon.py" >/dev/null 2>&1; then
    echo "robot_daemon.py did not stop, sending SIGKILL"
    sudo pkill -KILL -f "python .*robot_daemon.py"
  fi
  echo "robot_daemon.py stopped"
else
  echo "robot_daemon.py not running"
fi


echo "done"
