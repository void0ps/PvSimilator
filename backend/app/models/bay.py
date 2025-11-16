"""Bay数据模型：代表跟踪器中相同torque tube倾角的模块子集"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


@dataclass
class Pile:
    """桩点数据"""
    pile_id: int
    x: float
    y: float
    z: float


@dataclass
class Bay:
    """
    跟踪器Bay：一组具有相同torque tube倾角的模块
    
    根据论文："In a Nevados tracker, a bay represents a subsection of a tracker 
    which has a set of modules which all have the same torque tube axis tilt angle"
    """
    bay_id: str  # 格式："table_{table_id}_bay_{index}"
    table_id: int  # 所属跟踪行ID
    bay_index: int  # 在该跟踪行中的bay序号
    
    # 几何信息
    piles: List[Pile]  # 该bay包含的桩点
    centroid: Tuple[float, float, float]  # 质心坐标(x, y, z)
    
    # 模块信息
    module_count: int  # 该bay的模块数量
    module_width: float = 2.0  # 单个模块宽度（米）
    
    # 轴向信息
    axis_azimuth: float = 0.0  # 轴向方位角（度，北0东90）
    axis_tilt: float = 0.0  # torque tube倾角（度，正值向南）
    
    # 用于射线追踪的平面信息
    plane_normal: Tuple[float, float, float] = None  # 平面法向量
    plane_bounds: Tuple[float, float, float, float] = None  # 平面边界(min_x, max_x, min_y, max_y)
    
    def __post_init__(self):
        """计算质心和平面信息"""
        if self.centroid == (0.0, 0.0, 0.0) and self.piles:
            self.centroid = self._compute_centroid()
        if not self.plane_normal:
            self.plane_normal = self._compute_plane_normal()
        if not self.plane_bounds:
            self.plane_bounds = self._compute_bounds()
    
    def _compute_centroid(self) -> Tuple[float, float, float]:
        """计算bay的质心"""
        if not self.piles:
            return (0.0, 0.0, 0.0)
        
        x = np.mean([p.x for p in self.piles])
        y = np.mean([p.y for p in self.piles])
        z = np.mean([p.z for p in self.piles])
        return (float(x), float(y), float(z))
    
    def _compute_plane_normal(self) -> Tuple[float, float, float]:
        """
        计算bay平面的法向量
        
        假设跟踪器在0度位置（水平），法向量指向天空
        考虑axis_tilt的影响
        """
        # 基础法向量（垂直向上）
        # 根据axis_tilt调整
        tilt_rad = np.radians(self.axis_tilt)
        azimuth_rad = np.radians(self.axis_azimuth)
        
        # 法向量计算（简化模型）
        # 在水平位置，法向量应该垂直于轴向
        nx = np.sin(tilt_rad) * np.cos(azimuth_rad)
        ny = np.sin(tilt_rad) * np.sin(azimuth_rad)
        nz = np.cos(tilt_rad)
        
        # 归一化
        norm = np.sqrt(nx**2 + ny**2 + nz**2)
        return (float(nx/norm), float(ny/norm), float(nz/norm))
    
    def _compute_bounds(self) -> Tuple[float, float, float, float]:
        """计算bay的边界"""
        if not self.piles:
            return (0.0, 0.0, 0.0, 0.0)
        
        xs = [p.x for p in self.piles]
        ys = [p.y for p in self.piles]
        
        return (min(xs), max(xs), min(ys), max(ys))
    
    def get_effective_width(self) -> float:
        """获取bay的有效宽度（用于遮挡计算）"""
        return self.module_count * self.module_width
    
    def get_axis_vector(self) -> np.ndarray:
        """获取轴向单位向量"""
        azimuth_rad = np.radians(self.axis_azimuth)
        return np.array([
            np.cos(azimuth_rad),
            np.sin(azimuth_rad),
            0.0
        ])
    
    def point_on_plane(self, rotation_angle: float = 0.0) -> Tuple[float, float, float]:
        """
        获取bay平面上的一个参考点（考虑旋转角度）
        
        Args:
            rotation_angle: 跟踪器旋转角度（度）
            
        Returns:
            平面上的点坐标
        """
        # 简化：返回质心加上根据旋转角度的偏移
        cx, cy, cz = self.centroid
        
        # 根据旋转角度调整高度
        rotation_rad = np.radians(rotation_angle)
        height_offset = self.get_effective_width() / 2 * np.sin(rotation_rad)
        
        return (cx, cy, cz + height_offset)


def create_bay_from_piles(
    table_id: int,
    bay_index: int,
    piles: List[Pile],
    module_count: int,
    axis_azimuth: float = 0.0,
    axis_tilt: float = 0.0,
    module_width: float = 2.0
) -> Bay:
    """
    从桩点列表创建Bay对象
    
    Args:
        table_id: 跟踪行ID
        bay_index: bay序号
        piles: 桩点列表
        module_count: 模块数量
        axis_azimuth: 轴向方位角
        axis_tilt: torque tube倾角
        module_width: 模块宽度
        
    Returns:
        Bay对象
    """
    bay_id = f"table_{table_id}_bay_{bay_index}"
    
    return Bay(
        bay_id=bay_id,
        table_id=table_id,
        bay_index=bay_index,
        piles=piles,
        centroid=(0.0, 0.0, 0.0),  # 将在__post_init__中计算
        module_count=module_count,
        module_width=module_width,
        axis_azimuth=axis_azimuth,
        axis_tilt=axis_tilt
    )

