"""
Bay提取服务：从TrackerRow中提取bay信息

根据论文：
"In a Nevados tracker, a bay represents a subsection of a tracker which has 
a set of modules which all have the same torque tube axis tilt angle"
"""
from __future__ import annotations

from typing import List, Tuple
import numpy as np

from app.models.bay import Bay, Pile, create_bay_from_piles
from app.services.tracker_geometry import TrackerRow


class BayExtractor:
    """从TrackerRow提取Bay的服务"""
    
    def __init__(
        self,
        angle_threshold: float = 0.5,  # 角度差异阈值（度）
        min_modules_per_bay: int = 1,  # 每个bay最小模块数
        modules_per_pile: int = 5  # 每个桩默认模块数（简化假设）
    ):
        """
        初始化Bay提取器
        
        Args:
            angle_threshold: torque tube倾角差异阈值，超过此值则分割为新bay
            min_modules_per_bay: 每个bay的最小模块数
            modules_per_pile: 每个桩位的模块数（简化假设）
        """
        self.angle_threshold = angle_threshold
        self.min_modules_per_bay = min_modules_per_bay
        self.modules_per_pile = modules_per_pile
    
    def extract_bays_from_row(self, row: TrackerRow) -> List[Bay]:
        """
        从TrackerRow中提取bays
        
        策略：
        1. 如果桩点之间高度变化显著，则分割为不同bay
        2. 如果计算的axis_tilt变化超过阈值，则分割
        3. 否则将整行作为单个bay
        
        Args:
            row: TrackerRow对象
            
        Returns:
            Bay对象列表
        """
        if not row.pile_tops or len(row.pile_tops) < 2:
            # 桩点太少，作为单个bay
            return [self._create_single_bay(row)]
        
        # 计算每对相邻桩点之间的倾角
        pile_tilts = self._compute_pile_tilts(row)
        
        # 根据倾角变化分割bay
        bay_segments = self._segment_by_tilt_change(pile_tilts)
        
        # 为每个片段创建Bay对象
        bays = []
        for bay_index, (start_idx, end_idx) in enumerate(bay_segments):
            bay = self._create_bay_from_segment(
                row, 
                bay_index, 
                start_idx, 
                end_idx,
                pile_tilts
            )
            bays.append(bay)
        
        return bays
    
    def _compute_pile_tilts(self, row: TrackerRow) -> List[float]:
        """
        计算每个桩点位置的轴向倾角
        
        Args:
            row: TrackerRow对象
            
        Returns:
            每个桩点的倾角列表（度）
        """
        pile_tops = row.pile_tops
        n_piles = len(pile_tops)
        tilts = []
        
        for i in range(n_piles):
            if i == 0:
                # 第一个桩：使用与下一个桩的倾角
                if n_piles > 1:
                    tilt = self._compute_tilt_between_points(pile_tops[0], pile_tops[1])
                else:
                    tilt = 0.0
            elif i == n_piles - 1:
                # 最后一个桩：使用与前一个桩的倾角
                tilt = self._compute_tilt_between_points(pile_tops[i-1], pile_tops[i])
            else:
                # 中间桩：使用前后桩的平均倾角
                tilt1 = self._compute_tilt_between_points(pile_tops[i-1], pile_tops[i])
                tilt2 = self._compute_tilt_between_points(pile_tops[i], pile_tops[i+1])
                tilt = (tilt1 + tilt2) / 2
            
            tilts.append(tilt)
        
        return tilts
    
    def _compute_tilt_between_points(self, point1: np.ndarray, point2: np.ndarray) -> float:
        """
        计算两个点之间的倾角
        
        Args:
            point1: 起始点坐标(x, y, z)
            point2: 结束点坐标(x, y, z)
            
        Returns:
            倾角（度，正值表示point2比point1高）
        """
        # 计算水平距离和垂直距离
        dx = point2[0] - point1[0]
        dy = point2[1] - point1[1]
        dz = point2[2] - point1[2]
        
        horizontal_dist = np.sqrt(dx**2 + dy**2)
        
        if horizontal_dist < 0.01:  # 避免除零
            return 0.0
        
        # 计算倾角
        tilt_rad = np.arctan2(dz, horizontal_dist)
        tilt_deg = np.degrees(tilt_rad)
        
        return tilt_deg
    
    def _segment_by_tilt_change(self, tilts: List[float]) -> List[Tuple[int, int]]:
        """
        根据倾角变化将桩点序列分割为bay片段
        
        Args:
            tilts: 每个桩点的倾角列表
            
        Returns:
            bay片段列表，每个片段为(start_idx, end_idx)，左闭右开
        """
        if not tilts:
            return []
        
        segments = []
        start_idx = 0
        
        for i in range(1, len(tilts)):
            # 检查倾角变化是否超过阈值
            angle_diff = abs(tilts[i] - tilts[i-1])
            
            if angle_diff > self.angle_threshold:
                # 分割点
                segments.append((start_idx, i))
                start_idx = i
        
        # 添加最后一个片段
        segments.append((start_idx, len(tilts)))
        
        return segments
    
    def _create_bay_from_segment(
        self,
        row: TrackerRow,
        bay_index: int,
        start_idx: int,
        end_idx: int,
        pile_tilts: List[float]
    ) -> Bay:
        """
        从桩点片段创建Bay对象
        
        Args:
            row: TrackerRow对象
            bay_index: bay序号
            start_idx: 起始桩点索引
            end_idx: 结束桩点索引（不包含）
            pile_tilts: 桩点倾角列表
            
        Returns:
            Bay对象
        """
        # 提取该片段的桩点
        segment_piles = []
        for i in range(start_idx, end_idx):
            pile_top = row.pile_tops[i]
            segment_piles.append(Pile(
                pile_id=i,
                x=float(pile_top[0]),
                y=float(pile_top[1]),
                z=float(pile_top[2])
            ))
        
        # 计算该片段的平均倾角
        avg_tilt = np.mean(pile_tilts[start_idx:end_idx])
        
        # 估算模块数量（简化：每个桩间距有一定数量的模块）
        n_piles = len(segment_piles)
        module_count = max(self.min_modules_per_bay, n_piles * self.modules_per_pile)
        
        # 创建Bay对象
        bay = create_bay_from_piles(
            table_id=row.table_id,
            bay_index=bay_index,
            piles=segment_piles,
            module_count=module_count,
            axis_azimuth=row.axis_azimuth_deg(),
            axis_tilt=avg_tilt,
            module_width=2.0
        )
        
        return bay
    
    def _create_single_bay(self, row: TrackerRow) -> Bay:
        """
        将整个TrackerRow作为单个Bay
        
        Args:
            row: TrackerRow对象
            
        Returns:
            Bay对象
        """
        piles = [
            Pile(pile_id=i, x=float(p[0]), y=float(p[1]), z=float(p[2]))
            for i, p in enumerate(row.pile_tops)
        ]
        
        # 估算模块数量
        module_count = max(self.min_modules_per_bay, len(piles) * self.modules_per_pile)
        
        # 计算平均倾角
        if len(row.pile_tops) >= 2:
            avg_tilt = self._compute_tilt_between_points(row.pile_tops[0], row.pile_tops[-1])
        else:
            avg_tilt = 0.0
        
        bay = create_bay_from_piles(
            table_id=row.table_id,
            bay_index=0,
            piles=piles,
            module_count=module_count,
            axis_azimuth=row.axis_azimuth_deg(),
            axis_tilt=avg_tilt,
            module_width=2.0
        )
        
        return bay


def extract_all_bays(rows: List[TrackerRow]) -> List[Bay]:
    """
    从所有TrackerRow中提取所有bays
    
    Args:
        rows: TrackerRow对象列表
        
    Returns:
        所有Bay对象的列表
    """
    extractor = BayExtractor()
    all_bays = []
    
    for row in rows:
        bays = extractor.extract_bays_from_row(row)
        all_bays.extend(bays)
    
    return all_bays

