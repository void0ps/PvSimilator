"""
简化射线追踪算法
基于论文："Terrain Aware Backtracking via Forward Ray Tracing" (2022 IEEE PVSC)
"""
from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np
import logging

from app.models.bay import Bay

logger = logging.getLogger(__name__)


class RayTracer:
    """
    简化的射线追踪器

    实现论文中的前向射线追踪逻辑：
    "rays are traced from a "camera", through the pixels on a screen and into
    the scene and then finally towards a light source"

    改进版本包含:
    - 多光线采样（bay四角 + 质心）
    - 迭代回溯机制
    """

    def __init__(self, epsilon: float = 1e-6, num_sample_rays: int = 5):
        """
        初始化射线追踪器

        Args:
            epsilon: 数值计算的容差
            num_sample_rays: 采样光线数量（5 = 4角 + 1中心）
        """
        self.epsilon = epsilon
        self.num_sample_rays = num_sample_rays

    def _get_bay_corners(self, bay: Bay) -> List[np.ndarray]:
        """
        获取bay的四个角点坐标

        Args:
            bay: Bay对象

        Returns:
            List[np.ndarray]: 四个角点的3D坐标列表
        """
        # 获取bay的边界
        min_x, max_x, min_y, max_y = bay.plane_bounds
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # 获取bay的Z坐标（高度）
        z = bay.centroid[2] if len(bay.centroid) > 2 else 0.0

        # 四个角点
        corners = [
            np.array([min_x, min_y, z]),  # 左下
            np.array([max_x, min_y, z]),  # 右下
            np.array([max_x, max_y, z]),  # 右上
            np.array([min_x, max_y, z]),  # 左上
        ]

        return corners

    def _generate_sample_rays(
        self,
        bay: Bay,
        sun_vector: np.ndarray
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        生成bay多个采样点的光线

        根据论文建议，从bay的四角和质心发射多条光线以提高遮挡检测精度。

        Args:
            bay: Bay对象
            sun_vector: 太阳方向单位向量

        Returns:
            List[Tuple[np.ndarray, np.ndarray]]: 光线列表，每个元素为 (起点, 方向)
        """
        rays = []

        # 添加四角采样点
        corners = self._get_bay_corners(bay)
        for corner in corners:
            rays.append((corner, sun_vector))

        # 添加质心采样点
        center = np.array(bay.centroid)
        rays.append((center, sun_vector))

        return rays[:self.num_sample_rays]  # 限制数量

    def check_shading(
        self,
        bay_receiver: Bay,
        bay_blocker: Bay,
        sun_vector: np.ndarray,
        rotation_angle_receiver: float = 0.0,
        rotation_angle_blocker: float = 0.0,
        use_multi_ray: bool = False
    ) -> bool:
        """
        检测bay_blocker是否遮挡bay_receiver

        Args:
            bay_receiver: 接收bay（可能被遮挡）
            bay_blocker: 遮挡bay（可能造成遮挡）
            sun_vector: 太阳方向单位向量（指向太阳）
            rotation_angle_receiver: 接收bay的旋转角度
            rotation_angle_blocker: 遮挡bay的旋转角度
            use_multi_ray: 是否使用多光线采样

        Returns:
            True表示有遮挡，False表示无遮挡
        """
        if use_multi_ray:
            # 使用多光线采样
            rays = self._generate_sample_rays(bay_receiver, sun_vector)
            for ray_origin, ray_direction in rays:
                if self._check_single_ray_shading(
                    ray_origin, ray_direction, bay_blocker, rotation_angle_blocker
                ):
                    return True
            return False
        else:
            # 单光线（质心）
            ray_origin = np.array(bay_receiver.centroid)
            ray_direction = sun_vector
            return self._check_single_ray_shading(
                ray_origin, ray_direction, bay_blocker, rotation_angle_blocker
            )

    def _check_single_ray_shading(
        self,
        ray_origin: np.ndarray,
        ray_direction: np.ndarray,
        bay_blocker: Bay,
        rotation_angle_blocker: float
    ) -> bool:
        """
        检测单条光线是否被遮挡

        Args:
            ray_origin: 光线起点
            ray_direction: 光线方向
            bay_blocker: 遮挡bay
            rotation_angle_blocker: 遮挡bay的旋转角度

        Returns:
            True表示有遮挡
        """
        # 计算射线与blocker平面的交点
        blocker_point = np.array(bay_blocker.point_on_plane(rotation_angle_blocker))
        blocker_normal = self._get_rotated_normal(bay_blocker, rotation_angle_blocker)

        intersection = self._ray_plane_intersection(
            ray_origin, ray_direction, blocker_point, blocker_normal
        )

        if intersection is None:
            return False

        # 检查交点是否在blocker的有效范围内
        if self._point_in_bay_bounds(intersection, bay_blocker, rotation_angle_blocker):
            # 确保交点在receiver和太阳之间
            to_intersection = intersection - ray_origin
            if np.dot(to_intersection, ray_direction) > 0:
                return True

        return False

    def find_optimal_backtrack_angle(
        self,
        initial_angle: float,
        bay_receiver: Bay,
        bay_blockers: List[Bay],
        sun_vector: np.ndarray,
        max_iterations: int = 10,
        angle_step: float = 1.0,
        min_angle: float = -85.0,
        max_angle: float = 85.0
    ) -> Tuple[float, bool]:
        """
        迭代寻找最优回溯角度

        根据论文建议，检测到遮挡后，两个跟踪器都回溯1度，重复测试直到无遮挡。

        Args:
            initial_angle: 初始跟踪角度
            bay_receiver: 接收bay
            bay_blockers: 可能造成遮挡的bay列表
            sun_vector: 太阳方向向量
            max_iterations: 最大迭代次数
            angle_step: 每次回溯的角度步长（度）
            min_angle: 最小角度限制
            max_angle: 最大角度限制

        Returns:
            Tuple[float, bool]: (最优角度, 是否有遮挡)
        """
        current_angle = initial_angle
        has_shading = False

        for iteration in range(max_iterations):
            shading_detected = False

            for blocker in bay_blockers:
                # 假设blocker使用相同角度（简化）
                if self.check_shading(
                    bay_receiver, blocker, sun_vector,
                    rotation_angle_receiver=current_angle,
                    rotation_angle_blocker=current_angle,
                    use_multi_ray=True
                ):
                    shading_detected = True
                    has_shading = True
                    break

            if shading_detected:
                # 回溯：减小角度绝对值
                if current_angle > 0:
                    current_angle = max(min_angle, current_angle - angle_step)
                else:
                    current_angle = min(max_angle, current_angle + angle_step)

                # 检查是否达到角度限制
                if abs(current_angle) >= abs(initial_angle):
                    break
            else:
                # 无遮挡，找到最优角度
                break

        return current_angle, has_shading
    
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
        rotation_angles: List[List[float]],
        use_multi_ray: bool = False,
        use_iterative_backtrack: bool = False
    ) -> np.ndarray:
        """
        计算所有bay在所有时刻的遮挡矩阵

        改进版本支持：
        - 多光线采样：从bay四角+质心发射光线
        - 迭代回溯：检测到遮挡后逐步回溯

        Args:
            bays: bay列表
            sun_vectors: 太阳方向向量列表（每个时刻一个）
            rotation_angles: 旋转角度列表（每个时刻每个bay一个）
            use_multi_ray: 是否使用多光线采样
            use_iterative_backtrack: 是否使用迭代回溯

        Returns:
            遮挡矩阵 [n_timesteps x n_bays]，1表示无遮挡，0表示有遮挡
        """
        n_timesteps = len(sun_vectors)
        n_bays = len(bays)
        shading_matrix = np.ones((n_timesteps, n_bays))

        for t in range(n_timesteps):
            sun_vec = sun_vectors[t]

            for i, bay_receiver in enumerate(bays):
                # 获取可能造成遮挡的bay列表（排除自己）
                potential_blockers = [bays[j] for j in range(n_bays) if j != i]

                if use_iterative_backtrack:
                    # 使用迭代回溯寻找最优角度
                    initial_angle = rotation_angles[t][i]
                    optimal_angle, has_shading = self.find_optimal_backtrack_angle(
                        initial_angle=initial_angle,
                        bay_receiver=bay_receiver,
                        bay_blockers=potential_blockers,
                        sun_vector=sun_vec
                    )
                    if has_shading:
                        shading_matrix[t, i] = 0.0
                    # 可以选择更新 rotation_angles[t][i] = optimal_angle
                else:
                    # 标准检测
                    for j, bay_blocker in enumerate(bays):
                        if i == j:
                            continue

                        if self.check_shading(
                            bay_receiver,
                            bay_blocker,
                            sun_vec,
                            rotation_angles[t][i],
                            rotation_angles[t][j],
                            use_multi_ray=use_multi_ray
                        ):
                            shading_matrix[t, i] = 0.0
                            break

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

















