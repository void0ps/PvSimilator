"""
简化射线追踪算法
基于论文："Terrain Aware Backtracking via Forward Ray Tracing" (2022 IEEE PVSC)
"""
from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np

from app.models.bay import Bay


class RayTracer:
    """
    简化的射线追踪器
    
    实现论文中的前向射线追踪逻辑：
    "rays are traced from a "camera", through the pixels on a screen and into
    the scene and then finally towards a light source"
    """
    
    def __init__(self, epsilon: float = 1e-6):
        """
        初始化射线追踪器
        
        Args:
            epsilon: 数值计算的容差
        """
        self.epsilon = epsilon
    
    def check_shading(
        self,
        bay_receiver: Bay,
        bay_blocker: Bay,
        sun_vector: np.ndarray,
        rotation_angle_receiver: float = 0.0,
        rotation_angle_blocker: float = 0.0
    ) -> bool:
        """
        检测bay_blocker是否遮挡bay_receiver
        
        Args:
            bay_receiver: 接收bay（可能被遮挡）
            bay_blocker: 遮挡bay（可能造成遮挡）
            sun_vector: 太阳方向单位向量（指向太阳）
            rotation_angle_receiver: 接收bay的旋转角度
            rotation_angle_blocker: 遮挡bay的旋转角度
            
        Returns:
            True表示有遮挡，False表示无遮挡
        """
        # 1. 从receiver的质心发射反向太阳射线
        ray_origin = np.array(bay_receiver.centroid)
        ray_direction = sun_vector  # 指向太阳
        
        # 2. 计算射线与blocker平面的交点
        blocker_point = np.array(bay_blocker.point_on_plane(rotation_angle_blocker))
        blocker_normal = self._get_rotated_normal(
            bay_blocker, 
            rotation_angle_blocker
        )
        
        intersection = self._ray_plane_intersection(
            ray_origin,
            ray_direction,
            blocker_point,
            blocker_normal
        )
        
        if intersection is None:
            return False  # 射线不与平面相交
        
        # 3. 检查交点是否在blocker的有效范围内
        if self._point_in_bay_bounds(intersection, bay_blocker, rotation_angle_blocker):
            # 4. 确保交点在receiver和太阳之间（而不是背后）
            to_intersection = intersection - ray_origin
            if np.dot(to_intersection, ray_direction) > 0:
                return True
        
        return False
    
    def _ray_plane_intersection(
        self,
        ray_origin: np.ndarray,
        ray_direction: np.ndarray,
        plane_point: np.ndarray,
        plane_normal: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        计算射线与平面的交点
        
        Args:
            ray_origin: 射线起点
            ray_direction: 射线方向（单位向量）
            plane_point: 平面上的一个点
            plane_normal: 平面法向量（单位向量）
            
        Returns:
            交点坐标，如果不相交则返回None
        """
        # 射线方程: P = ray_origin + t * ray_direction
        # 平面方程: dot(P - plane_point, plane_normal) = 0
        
        denom = np.dot(ray_direction, plane_normal)
        
        # 检查射线是否平行于平面
        if abs(denom) < self.epsilon:
            return None
        
        # 计算参数t
        t = np.dot(plane_point - ray_origin, plane_normal) / denom
        
        # t必须为正（交点在射线方向上）
        if t < 0:
            return None
        
        # 计算交点
        intersection = ray_origin + t * ray_direction
        return intersection
    
    def _get_rotated_normal(self, bay: Bay, rotation_angle: float) -> np.ndarray:
        """
        获取bay在给定旋转角度下的法向量
        
        Args:
            bay: Bay对象
            rotation_angle: 旋转角度（度）
            
        Returns:
            旋转后的法向量（单位向量）
        """
        # 获取轴向
        axis_vector = bay.get_axis_vector()
        
        # 旋转角度转弧度
        theta = np.radians(rotation_angle)
        
        # 在0度位置，法向量垂直向上
        # 旋转后，法向量绕轴向旋转
        
        # 简化计算：假设初始法向量为(0, 0, 1)
        # 绕axis_vector旋转theta角度
        
        # 使用罗德里格斯旋转公式
        initial_normal = np.array([0.0, 0.0, 1.0])
        
        # 考虑axis_tilt的影响
        axis_tilt_rad = np.radians(bay.axis_tilt)
        axis_azimuth_rad = np.radians(bay.axis_azimuth)
        
        # 调整初始法向量
        initial_normal = np.array([
            np.sin(axis_tilt_rad) * np.cos(axis_azimuth_rad + np.pi/2),
            np.sin(axis_tilt_rad) * np.sin(axis_azimuth_rad + np.pi/2),
            np.cos(axis_tilt_rad)
        ])
        
        # 绕轴向旋转
        rotated_normal = self._rodrigues_rotation(
            initial_normal,
            axis_vector,
            theta
        )
        
        # 归一化
        norm = np.linalg.norm(rotated_normal)
        if norm > self.epsilon:
            rotated_normal = rotated_normal / norm
        
        return rotated_normal
    
    def _rodrigues_rotation(
        self,
        v: np.ndarray,
        k: np.ndarray,
        theta: float
    ) -> np.ndarray:
        """
        罗德里格斯旋转公式：将向量v绕轴k旋转theta角度
        
        Args:
            v: 待旋转向量
            k: 旋转轴（单位向量）
            theta: 旋转角度（弧度）
            
        Returns:
            旋转后的向量
        """
        return (v * np.cos(theta) +
                np.cross(k, v) * np.sin(theta) +
                k * np.dot(k, v) * (1 - np.cos(theta)))
    
    def _point_in_bay_bounds(
        self,
        point: np.ndarray,
        bay: Bay,
        rotation_angle: float
    ) -> bool:
        """
        检查点是否在bay的有效范围内
        
        Args:
            point: 待检查的点
            bay: Bay对象
            rotation_angle: bay的旋转角度
            
        Returns:
            True表示点在范围内
        """
        # 简化检查：使用bay的边界框
        min_x, max_x, min_y, max_y = bay.plane_bounds
        
        # 添加缓冲区（考虑模块宽度）
        buffer = bay.get_effective_width() / 2
        
        if (min_x - buffer <= point[0] <= max_x + buffer and
            min_y - buffer <= point[1] <= max_y + buffer):
            return True
        
        return False
    
    def compute_shading_matrix(
        self,
        bays: List[Bay],
        sun_vectors: List[np.ndarray],
        rotation_angles: List[List[float]]
    ) -> np.ndarray:
        """
        计算所有bay在所有时刻的遮挡矩阵
        
        Args:
            bays: bay列表
            sun_vectors: 太阳方向向量列表（每个时刻一个）
            rotation_angles: 旋转角度列表（每个时刻每个bay一个）
            
        Returns:
            遮挡矩阵 [n_timesteps x n_bays]，1表示无遮挡，0表示有遮挡
        """
        n_timesteps = len(sun_vectors)
        n_bays = len(bays)
        shading_matrix = np.ones((n_timesteps, n_bays))
        
        for t in range(n_timesteps):
            sun_vec = sun_vectors[t]
            
            for i, bay_receiver in enumerate(bays):
                # 检查是否被其他bay遮挡
                for j, bay_blocker in enumerate(bays):
                    if i == j:
                        continue  # 跳过自己
                    
                    if self.check_shading(
                        bay_receiver,
                        bay_blocker,
                        sun_vec,
                        rotation_angles[t][i],
                        rotation_angles[t][j]
                    ):
                        shading_matrix[t, i] = 0.0
                        break  # 只要有一个遮挡就够了
        
        return shading_matrix


def create_sun_vector(solar_azimuth: float, solar_elevation: float) -> np.ndarray:
    """
    从太阳方位角和高度角创建太阳方向向量
    
    Args:
        solar_azimuth: 太阳方位角（度，北0东90）
        solar_elevation: 太阳高度角（度）
        
    Returns:
        太阳方向单位向量（指向太阳）
    """
    az_rad = np.radians(solar_azimuth)
    el_rad = np.radians(solar_elevation)
    
    # 太阳方向向量
    x = np.cos(el_rad) * np.sin(az_rad)
    y = np.cos(el_rad) * np.cos(az_rad)
    z = np.sin(el_rad)
    
    return np.array([x, y, z])

















