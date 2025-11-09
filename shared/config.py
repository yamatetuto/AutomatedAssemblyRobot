"""設定管理モジュール"""
import os
import yaml
from typing import Optional, Dict, Any
from pathlib import Path


class Config:
    """設定管理クラス"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: 設定ファイルのパス（YAML形式）
        """
        self.config_data: Dict[str, Any] = {}
        if config_path and Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f) or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得（環境変数を優先）"""
        # 環境変数をチェック
        env_key = key.upper().replace('.', '_')
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        # YAMLファイルから取得
        keys = key.split('.')
        value = self.config_data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """整数値を取得"""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """真偽値を取得"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return default


def load_config(service_name: str) -> Config:
    """サービスの設定をロード"""
    config_path = Path(__file__).parent.parent / "services" / service_name / "config.yaml"
    return Config(str(config_path) if config_path.exists() else None)
