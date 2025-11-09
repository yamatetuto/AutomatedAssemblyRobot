"""ログ設定モジュール"""
import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(
    service_name: str,
    log_level: str = "INFO",
    log_dir: Optional[str] = None
) -> logging.Logger:
    """
    サービス用のロガーを設定
    
    Args:
        service_name: サービス名
        log_level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: ログディレクトリ（省略時は標準出力のみ）
    
    Returns:
        設定済みのLogger
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # フォーマッター
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 標準出力ハンドラ
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラ（指定された場合）
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_path / f"{service_name}.log",
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(service_name: str) -> logging.Logger:
    """既存のロガーを取得"""
    return logging.getLogger(service_name)
