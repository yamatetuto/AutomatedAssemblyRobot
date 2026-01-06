"""
位置データ管理モジュール

ロボットのティーチングポイント（教示点）を管理する。
JSON形式での保存・読込、レガシー形式からの変換機能を提供。

参照元ファイル:
    - TEACHING/file_ctrl.py: save_position(), load_position(), parse_posi_file()
    - TEACHING/SPLEBO-N.pos: 位置データファイル形式の参考
    - TEACHING/splebo_n.py: posi_data_class (L800-900)

参照元の主要関数:
    - file_ctrl.save_position() → PositionManager.save()
    - file_ctrl.load_position() → PositionManager.load()
    - file_ctrl.parse_posi_file() → LegacyPositionConverter.from_legacy_format()

移植時の変更点:
    - 独自テキスト形式 → JSON形式に変更（拡張性向上）
    - PositionデータをDataclassで型安全に管理
    - async/await対応
    - レガシー形式（.pos）からの変換機能を追加
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """位置データ"""
    point_no: int
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    u: float = 0.0
    s1: float = 0.0
    s2: float = 0.0
    a: float = 0.0
    b: float = 0.0
    is_absolute: bool = True
    is_protected: bool = False
    comment: str = ""
    
    def to_dict(self) -> Dict:
        """辞書に変換"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Position":
        """辞書から生成"""
        return cls(**data)
    
    def get_axis_value(self, axis: int) -> float:
        """軸番号から座標値を取得"""
        axis_map = {0: self.x, 1: self.y, 2: self.z, 3: self.u,
                    4: self.s1, 5: self.s2, 6: self.a, 7: self.b}
        return axis_map.get(axis, 0.0)
    
    def set_axis_value(self, axis: int, value: float) -> None:
        """軸番号で座標値を設定"""
        if axis == 0:
            self.x = value
        elif axis == 1:
            self.y = value
        elif axis == 2:
            self.z = value
        elif axis == 3:
            self.u = value
        elif axis == 4:
            self.s1 = value
        elif axis == 5:
            self.s2 = value
        elif axis == 6:
            self.a = value
        elif axis == 7:
            self.b = value


@dataclass
class PositionFile:
    """位置ファイルデータ"""
    data_type: str = "SPLEBO-N.POS"
    version: str = "1.00"
    timestamp: str = ""
    positions: List[Position] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "data_type": self.data_type,
            "version": self.version,
            "timestamp": self.timestamp,
            "positions": [p.to_dict() for p in self.positions]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PositionFile":
        positions = [Position.from_dict(p) for p in data.get("positions", [])]
        return cls(
            data_type=data.get("data_type", "SPLEBO-N.POS"),
            version=data.get("version", "1.00"),
            timestamp=data.get("timestamp", ""),
            positions=positions
        )


class PositionManager:
    """
    位置データ管理クラス
    
    ティーチングポイントの保存・読み込み・編集を行う。
    """
    
    def __init__(self, file_path: str = None):
        """
        初期化
        
        Args:
            file_path: 位置データファイルパス
        """
        from src.config.settings import ROBOT_POSITION_FILE
        
        self.file_path = Path(file_path) if file_path else ROBOT_POSITION_FILE
        self._data: PositionFile = PositionFile()
        self._lock = asyncio.Lock()
        self._modified = False
    
    async def load(self) -> bool:
        """
        ファイルから読み込み
        
        Returns:
            成功時True
        """
        async with self._lock:
            try:
                if not self.file_path.exists():
                    logger.info(f"位置ファイルが存在しません。新規作成: {self.file_path}")
                    await self._create_default()
                    return True
                
                content = await asyncio.to_thread(self.file_path.read_text, encoding='utf-8')
                data = json.loads(content)
                self._data = PositionFile.from_dict(data)
                
                logger.info(f"位置ファイル読み込み完了: {len(self._data.positions)}ポイント")
                return True
                
            except Exception as e:
                logger.error(f"位置ファイル読み込みエラー: {e}")
                return False
    
    async def save(self) -> bool:
        """
        ファイルに保存
        
        Returns:
            成功時True
        """
        async with self._lock:
            try:
                self._data.timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
                content = json.dumps(self._data.to_dict(), indent=2, ensure_ascii=False)
                
                # ディレクトリ作成
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                
                await asyncio.to_thread(self.file_path.write_text, content, encoding='utf-8')
                self._modified = False
                
                logger.info(f"位置ファイル保存完了: {self.file_path}")
                return True
                
            except Exception as e:
                logger.error(f"位置ファイル保存エラー: {e}")
                return False
    
    async def _create_default(self) -> None:
        """デフォルトファイル作成"""
        self._data = PositionFile(
            timestamp=datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
            positions=[
                Position(point_no=1, comment="Home Position")
            ]
        )
        await self.save()
    
    def get_position(self, point_no: int) -> Optional[Position]:
        """
        ポイント番号で位置取得
        
        Args:
            point_no: ポイント番号
        
        Returns:
            Positionオブジェクト（見つからない場合はNone）
        """
        for pos in self._data.positions:
            if pos.point_no == point_no:
                return pos
        return None
    
    def get_axis_value(self, point_no: int, axis: int) -> Optional[float]:
        """
        ポイント番号と軸から座標値取得
        
        Args:
            point_no: ポイント番号
            axis: 軸番号 (0=X, 1=Y, 2=Z, ...)
        
        Returns:
            座標値（見つからない場合はNone）
        """
        pos = self.get_position(point_no)
        if pos:
            return pos.get_axis_value(axis)
        return None
    
    def get_all_positions(self) -> List[Position]:
        """全位置データ取得"""
        return self._data.positions.copy()
    
    async def add_position(self, position: Position) -> bool:
        """
        位置を追加
        
        Args:
            position: 追加する位置データ
        
        Returns:
            成功時True
        """
        async with self._lock:
            # 既存のポイント番号チェック
            if self.get_position(position.point_no):
                logger.warning(f"ポイント番号{position.point_no}は既に存在します")
                return False
            
            self._data.positions.append(position)
            self._sort_positions()
            self._modified = True
            
            logger.info(f"ポイント{position.point_no}を追加しました")
            return True
    
    async def update_position(self, position: Position) -> bool:
        """
        位置を更新
        
        Args:
            position: 更新する位置データ
        
        Returns:
            成功時True
        """
        async with self._lock:
            for i, pos in enumerate(self._data.positions):
                if pos.point_no == position.point_no:
                    self._data.positions[i] = position
                    self._modified = True
                    logger.info(f"ポイント{position.point_no}を更新しました")
                    return True
            
            logger.warning(f"ポイント{position.point_no}が見つかりません")
            return False
    
    async def delete_position(self, point_no: int) -> bool:
        """
        位置を削除
        
        Args:
            point_no: 削除するポイント番号
        
        Returns:
            成功時True
        """
        async with self._lock:
            for i, pos in enumerate(self._data.positions):
                if pos.point_no == point_no:
                    del self._data.positions[i]
                    self._modified = True
                    logger.info(f"ポイント{point_no}を削除しました")
                    return True
            
            logger.warning(f"ポイント{point_no}が見つかりません")
            return False
    
    async def teach_position(
        self,
        point_no: int,
        current_position: Dict[str, float],
        comment: str = ""
    ) -> bool:
        """
        現在位置をティーチング
        
        Args:
            point_no: ポイント番号
            current_position: 現在位置 {'x': float, 'y': float, ...}
            comment: コメント
        
        Returns:
            成功時True
        """
        position = Position(
            point_no=point_no,
            x=current_position.get('x', 0.0),
            y=current_position.get('y', 0.0),
            z=current_position.get('z', 0.0),
            u=current_position.get('u', 0.0),
            s1=current_position.get('s1', 0.0),
            s2=current_position.get('s2', 0.0),
            a=current_position.get('a', 0.0),
            b=current_position.get('b', 0.0),
            comment=comment
        )
        
        existing = self.get_position(point_no)
        if existing:
            return await self.update_position(position)
        else:
            return await self.add_position(position)
    
    async def copy_position(self, from_no: int, to_no: int) -> bool:
        """
        位置をコピー
        
        Args:
            from_no: コピー元ポイント番号
            to_no: コピー先ポイント番号
        
        Returns:
            成功時True
        """
        source = self.get_position(from_no)
        if not source:
            logger.warning(f"コピー元ポイント{from_no}が見つかりません")
            return False
        
        new_position = Position(
            point_no=to_no,
            x=source.x, y=source.y, z=source.z, u=source.u,
            s1=source.s1, s2=source.s2, a=source.a, b=source.b,
            is_absolute=source.is_absolute,
            comment=f"Copy from P{from_no}"
        )
        
        return await self.add_position(new_position)
    
    def _sort_positions(self) -> None:
        """ポイント番号でソート"""
        self._data.positions.sort(key=lambda p: p.point_no)
    
    @property
    def is_modified(self) -> bool:
        """未保存の変更があるか"""
        return self._modified
    
    @property
    def count(self) -> int:
        """登録ポイント数"""
        return len(self._data.positions)
    
    def to_dict(self) -> Dict:
        """全データを辞書で取得"""
        return self._data.to_dict()


# レガシー形式（SPLEBO-N.pos）からの変換用
class LegacyPositionConverter:
    """
    レガシー形式（SPLEBO-N.pos）からJSON形式への変換
    """
    
    @staticmethod
    async def convert(legacy_path: str, output_path: str) -> bool:
        """
        レガシーファイルをJSON形式に変換
        
        Args:
            legacy_path: 変換元ファイルパス
            output_path: 出力先ファイルパス
        
        Returns:
            成功時True
        """
        try:
            positions = []
            
            with open(legacy_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            in_point_section = False
            for line in lines:
                line = line.strip()
                
                if line == "[Point]":
                    in_point_section = True
                    continue
                
                if in_point_section and line.startswith("Item"):
                    # Item1=1,0,0.0,0.0,0.0,0.0,,,,,,0,Home Position
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        values = parts[1].split(",")
                        if len(values) >= 11:
                            pos = Position(
                                point_no=int(values[0]) if values[0] else 0,
                                is_absolute=values[1] == "0",
                                x=float(values[2]) if values[2] else 0.0,
                                y=float(values[3]) if values[3] else 0.0,
                                z=float(values[4]) if values[4] else 0.0,
                                u=float(values[5]) if values[5] else 0.0,
                                s1=float(values[6]) if values[6] else 0.0,
                                s2=float(values[7]) if values[7] else 0.0,
                                a=float(values[8]) if values[8] else 0.0,
                                b=float(values[9]) if values[9] else 0.0,
                                is_protected=values[10] == "1" if len(values) > 10 else False,
                                comment=values[11] if len(values) > 11 else ""
                            )
                            positions.append(pos)
            
            # 保存
            manager = PositionManager(output_path)
            manager._data.positions = positions
            await manager.save()
            
            logger.info(f"変換完了: {len(positions)}ポイント")
            return True
            
        except Exception as e:
            logger.error(f"変換エラー: {e}")
            return False
