#!/bin/bash
# src/ ディレクトリ構造を作成

mkdir -p src/{camera,gripper,webrtc,config}

# 各ディレクトリに__init__.pyを作成
touch src/__init__.py
touch src/camera/__init__.py
touch src/gripper/__init__.py
touch src/webrtc/__init__.py
touch src/config/__init__.py

echo "✓ src/ ディレクトリ構造を作成しました"
tree src/ -I "__pycache__"
