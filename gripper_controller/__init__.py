"""
グリッパー制御モジュール
IAI社製CONコントローラーのModbus RTU通信による制御
"""
from .CONController import CONController

__all__ = ['CONController']
