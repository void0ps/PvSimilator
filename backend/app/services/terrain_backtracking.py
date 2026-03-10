from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import pvlib

from .tracker_analysis import RowNeighbor, compute_row_pitch
from .tracker_geometry import TrackerRow


@dataclass
class BacktrackingConfig:
    module_width: float = 2.0  # 组件东西向宽度（米）
    max_angle: float = 85.0    # 机械最大倾角（度）
    backtrack: bool = True
    shading_margin_limit: float = 10.0  # 允许的负裕度对应满遮挡的角度幅度
    max_neighbor_cross_distance: float = 20.0  # 过滤横向距离过远的邻居（米）
    max_neighbor_along_distance: float = 250.0  # 过滤沿轴距离过远的邻居（米）
    cross_distance_epsilon: float = 0.5  # 防止横向距离过小导致数值不稳定
    # NEW: NREL论文公式相关参数
    use_nrel_shading_fraction: bool = False  # 是否使用论文遮挡公式
    use_nrel_slope_aware_correction: bool = False  # 是否使用论文斜坡感知修正 (Equations 11-14)
    use_nrel_complete_formula: bool = False  # 是否使用论文完整遮挡公式 (Equation 32)
    nrel_shading_limit_deg: float = 5.0  # NREL论文建议的遮挡裕度限制（度）


@dataclass
class BacktrackingResult:
    angles: pd.DataFrame
    shading_margin: pd.DataFrame
    shading_factor: pd.DataFrame


class TerrainBacktrackingSolver:
    def __init__(
        self,
        rows: Iterable[TrackerRow],
        neighbors: Dict[int, List[RowNeighbor]],
        config: Optional[BacktrackingConfig] = None,
    ) -> None:
        self.rows = list(rows)
        self.neighbor_map = neighbors
        self.config = config or BacktrackingConfig()
        self._row_lookup = {row.table_id: row for row in self.rows}
        self.row_pitch = compute_row_pitch(self.neighbor_map)
        self._last_result: Optional[BacktrackingResult] = None

    def get_row_pitch(self, table_id: int) -> float:
        return self.row_pitch.get(table_id, self.config.module_width / 0.35)

    def _calculate_cross_axis_tilt(self, row: TrackerRow) -> float:
        """计算横轴坡度用于 pvlib.tracking.singleaxis。

        根据NREL论文 Equation 25-26，横轴坡度由地形坡度和坡度方位角与
        跟踪器轴方位角的相对关系决定。

        Args:
            row: 跟踪器行数据

        Returns:
            float: 横轴坡度（度）
        """
        # 如果没有坡度信息，返回0
        if row.slope_deg is None or row.slope_deg == 0:
            return 0.0

        # 获取坡度方位角（如果没有，假设与轴方位角相同方向）
        slope_azimuth = row.slope_azimuth_deg if row.slope_azimuth_deg is not None else row.axis_azimuth_deg()
        axis_azimuth = row.axis_azimuth_deg()

        # 计算横轴坡度
        # cross_axis_tilt = slope_tilt * sin(relative_azimuth)
        # 其中 relative_azimuth 是坡度方位角与轴方位角之差
        relative_azimuth_rad = np.radians(slope_azimuth - axis_azimuth)
        slope_rad = np.radians(abs(row.slope_deg))

        cross_axis_tilt = np.degrees(slope_rad * np.sin(relative_azimuth_rad))

        return float(cross_axis_tilt)

    def _singleaxis(
        self,
        solar_zenith: pd.Series,
        solar_azimuth: pd.Series,
        row: TrackerRow,
    ) -> pd.Series:
        pitch = max(self.get_row_pitch(row.table_id), self.config.module_width * 1.01)
        gcr = np.clip(self.config.module_width / pitch, 0.05, 0.9)

        # 使用地形数据计算横轴坡度
        cross_axis_tilt = self._calculate_cross_axis_tilt(row)

        tracking_result = pvlib.tracking.singleaxis(
            apparent_zenith=solar_zenith,
            apparent_azimuth=solar_azimuth,
            axis_tilt=row.average_axis_tilt_deg(),
            axis_azimuth=row.axis_azimuth_deg(),
            max_angle=self.config.max_angle,
            backtrack=self.config.backtrack,
            gcr=gcr,
            cross_axis_tilt=cross_axis_tilt,
        )

        return tracking_result["tracker_theta"]

    def _calculate_true_tracking_angle(
        self,
        solar_zenith: pd.Series,
        solar_azimuth: pd.Series,
        row: TrackerRow,
    ) -> pd.Series:
        """计算真跟踪角度 (theta_true)，不考虑回溯。

        根据 NREL 论文 Equation 5:
        theta_T = atan2(sx', sz')

        使用 pvlib.tracking.singleaxis 并设置 backtrack=False 来获取真跟踪角度。

        Args:
            solar_zenith: 太阳天顶角序列（度）
            solar_azimuth: 太阳方位角序列（度）
            row: 跟踪器行数据

        Returns:
            pd.Series: 真跟踪角度序列（度）
        """
        pitch = max(self.get_row_pitch(row.table_id), self.config.module_width * 1.01)
        gcr = np.clip(self.config.module_width / pitch, 0.05, 0.9)
        cross_axis_tilt = self._calculate_cross_axis_tilt(row)

        # 不启用回溯，获取真跟踪角度
        tracking_result = pvlib.tracking.singleaxis(
            apparent_zenith=solar_zenith,
            apparent_azimuth=solar_azimuth,
            axis_tilt=row.average_axis_tilt_deg(),
            axis_azimuth=row.axis_azimuth_deg(),
            max_angle=self.config.max_angle,
            backtrack=False,  # 不回溯
            gcr=gcr,
            cross_axis_tilt=cross_axis_tilt,
        )

        return tracking_result["tracker_theta"]

    def _needs_backtracking(
        self,
        theta_T: float,
        beta_c: float,
        gcr: float
    ) -> bool:
        """判断是否需要回溯 (NREL 论文 Equation 15)。

        根据 NREL 论文，当 cos(θc) = |cos(θT - βc)| / (GCR × cos(βc)) 的值
        在 (-1, 1) 范围内时，存在有效的回溯角度，因此需要回溯。
        当该值 >= 1 时，表示无需回溯或回溯无法消除遮挡。

        Args:
            theta_T: 真跟踪角度（度）
            beta_c: 横轴坡度（度）
            gcr: 地面覆盖率比

        Returns:
            bool: True 表示需要回溯
        """
        numerator = abs(np.cos(np.radians(theta_T - beta_c)))
        denominator = gcr * np.cos(np.radians(beta_c))

        if denominator < 1e-10:
            return False

        ratio = numerator / denominator

        # 当 ratio < 1 时，存在有效的回溯角度
        # 当 ratio >= 1 时，不需要回溯（或回溯角度为0）
        return ratio < 1.0

    def _calculate_slope_aware_correction(
        self,
        theta_T: float,
        beta_c: float,
        gcr: float
    ) -> float:
        """计算斜坡感知回溯修正角度 (NREL 论文 Equations 11-14)。

        回溯修正角度 theta_c 根据以下公式计算：
        - Equation 14: cos(theta_c) = |cos(theta_T - beta_c)| / (GCR * cos(beta_c))
        - theta_c = -sign(theta_T) * arccos(cos(theta_c))

        Args:
            theta_T: 真跟踪角度（度）
            beta_c: 横轴坡度（度）
            gcr: 地面覆盖率比

        Returns:
            float: 回溯修正角度（度），如果不需要回溯则返回0
        """
        # 首先检查是否需要回溯 (Equation 15)
        if not self._needs_backtracking(theta_T, beta_c, gcr):
            return 0.0

        # 计算回溯修正角度 (Equation 14)
        numerator = abs(np.cos(np.radians(theta_T - beta_c)))
        denominator = gcr * np.cos(np.radians(beta_c))

        if denominator < 1e-10:
            return 0.0

        cos_theta_c = numerator / denominator

        # 数值稳定性处理
        cos_theta_c = np.clip(cos_theta_c, -1.0, 1.0)

        # Equation 14: theta_c = -sign(theta_T) * arccos(cos_theta_c)
        theta_c = -np.sign(theta_T) * np.degrees(np.arccos(cos_theta_c))

        # 处理 theta_T = 0 的情况
        if abs(theta_T) < 1e-6:
            theta_c = -np.degrees(np.arccos(cos_theta_c))

        return float(theta_c)

    def _calculate_shading_fraction_nrel(
        self,
        gcr: float,
        theta: float,
        theta_true: Optional[float],
        beta_c: float,
    ) -> float:
        """根据 NREL 论文 Equation 32 计算遮挡分数。

        完整公式：
        fs = [GCR*cos(theta) + (GCR*sin(theta) - tan(beta_c))*tan(theta_T) - 1]
             / [GCR*(sin(theta)*tan(theta_T) + cos(theta))]

        简化版本 (当 theta_true 不可用时): fs = GCR * cos(theta) / cos(theta - beta_c)

        Args:
            gcr: 地面覆盖率比
            theta: 当前跟踪器角度（度），即回溯角度 theta_B
            theta_true: 真跟踪角度（度），不考虑回溯
            beta_c: 横轴坡度（度）

        Returns:
            float: 遮挡分数 (0-1范围)
        """
        theta_rad = np.radians(theta)  # 使用实际值而非绝对值
        beta_c_rad = np.radians(beta_c)

        # 使用 NREL 论文 Equation 32 的完整公式
        # fs = [GCR*cos(theta) + (GCR*sin(theta) - tan(beta_c))*tan(theta_T) - 1]
        #      / [GCR*(sin(theta)*tan(theta_T) + cos(theta))]
        if theta_true is not None and abs(theta_true) > 1e-3:
            theta_T_rad = np.radians(theta_true)  # 真跟踪角度

            cos_theta = np.cos(theta_rad)
            sin_theta = np.sin(theta_rad)
            tan_beta_c = np.tan(beta_c_rad)
            tan_theta_T = np.tan(theta_T_rad)

            # Equation 32 完整公式
            numerator = gcr * cos_theta + (gcr * sin_theta - tan_beta_c) * tan_theta_T - 1
            denominator = gcr * (sin_theta * tan_theta_T + cos_theta)

            # 避免除零
            if abs(denominator) < 1e-10:
                return 1.0  # 极端情况，假设完全遮挡

            shading = numerator / denominator

        else:
            # 当 theta_true 不可用时，使用简化版本
            # fs = GCR * cos(theta) / cos(theta - beta_c)
            if abs(beta_c) < 1e-3:
                # 无横轴坡度，正确回溯应该无遮挡
                return 0.0

            theta_effective_rad = np.radians(theta - beta_c)
            cos_theta_effective = np.cos(theta_effective_rad)

            if abs(cos_theta_effective) < 1e-6:
                return 1.0

            cos_theta = np.cos(theta_rad)
            shading = gcr * cos_theta / cos_theta_effective

        # 限制在 0-1 范围内
        return float(np.clip(shading, 0.0, 1.0))

    def _filter_neighbors(self, neighbors: List[RowNeighbor]) -> List[RowNeighbor]:
        filtered: List[RowNeighbor] = []
        for neighbor in neighbors:
            if self.config.max_neighbor_cross_distance and abs(neighbor.cross_axis_distance) > self.config.max_neighbor_cross_distance:
                continue
            if self.config.max_neighbor_along_distance and abs(neighbor.along_axis_distance) > self.config.max_neighbor_along_distance:
                continue
            filtered.append(neighbor)
        return filtered

    def _neighbor_blocking_angle(self, row: TrackerRow, neighbor: RowNeighbor) -> float:
        cross = float(neighbor.cross_axis_distance)
        if abs(cross) < self.config.cross_distance_epsilon:
            cross = self.config.cross_distance_epsilon if cross == 0 else np.sign(cross) * self.config.cross_distance_epsilon

        vertical = float(neighbor.vertical_offset)
        slope_row = row.slope_deg or 0.0
        slope_neighbor = neighbor.slope_delta_deg or 0.0

        # 根据行坡度补偿高度
        vertical += np.tan(np.radians(slope_row)) * cross
        vertical += np.tan(np.radians(slope_neighbor)) * cross

        along = float(neighbor.along_axis_distance)
        along_factor = np.clip(abs(along) / 150.0, 0.0, 1.0)
        vertical -= vertical * 0.2 * along_factor

        return float(np.degrees(np.arctan2(vertical, abs(cross))))

    def _compute_shading_margin(
        self,
        row: TrackerRow,
        solar_elevation: pd.Series,
        solar_azimuth: pd.Series,
    ) -> pd.Series:
        neighbors = self._filter_neighbors(self.neighbor_map.get(row.table_id, []))
        if not neighbors:
            return pd.Series(np.inf, index=solar_elevation.index, dtype=float)

        axis_azimuth = row.axis_azimuth_deg()
        cross_component = np.sin(np.radians(solar_azimuth - axis_azimuth)).reindex(solar_elevation.index)

        margins = pd.Series(np.inf, index=solar_elevation.index, dtype=float)
        for timestamp in solar_elevation.index:
            cross_val = float(cross_component.loc[timestamp]) if timestamp in cross_component.index else 0.0
            if abs(cross_val) < 1e-6:
                relevant = neighbors
            else:
                side = 1 if cross_val > 0 else -1
                relevant = [n for n in neighbors if n.relative_position == side]

            if not relevant:
                continue

            solar_el = float(solar_elevation.loc[timestamp])
            blocking_angles = [self._neighbor_blocking_angle(row, n) for n in relevant]
            margin = min(solar_el - angle for angle in blocking_angles)
            margins.at[timestamp] = margin

        return margins

    def compute_tracker_angles(
        self,
        solar_zenith: pd.Series,
        solar_azimuth: pd.Series,
    ) -> BacktrackingResult:
        """计算 terrain-aware backtracking 结果。

        根据 NREL 论文实现地形感知回溯算法：
        1. 计算真跟踪角度 (theta_T) - 不考虑回溯时的理想跟踪角度
        2. 计算回溯角度 (theta_B) - 考虑地形和遮挡的修正角度
        3. 使用 NREL Equation 32 计算遮挡分数

        参考: NREL/TP-5K00-76626, NREL/CP-5K00-76023
        """

        solar_elevation = 90.0 - solar_zenith

        angles: Dict[int, pd.Series] = {}
        true_angles: Dict[int, pd.Series] = {}  # 真跟踪角度
        margins: Dict[int, pd.Series] = {}
        gcr_values: Dict[int, float] = {}
        cross_axis_tilts: Dict[int, float] = {}
        row_lookup: Dict[int, TrackerRow] = {}

        for row in self.rows:
            # 计算GCR和横轴坡度，用于NREL公式
            pitch = max(self.get_row_pitch(row.table_id), self.config.module_width * 1.01)
            gcr = np.clip(self.config.module_width / pitch, 0.05, 0.9)
            gcr_values[row.table_id] = gcr
            cross_axis_tilts[row.table_id] = self._calculate_cross_axis_tilt(row)
            row_lookup[row.table_id] = row

            # 计算真跟踪角度（不考虑回溯）
            # 根据 NREL 论文，这是计算遮挡分数所需的关键参数
            theta_true_series = self._calculate_true_tracking_angle(
                solar_zenith, solar_azimuth, row
            ).reindex(solar_zenith.index)
            true_angles[row.table_id] = theta_true_series

            # 计算回溯角度（考虑地形）
            base_angles = self._singleaxis(solar_zenith, solar_azimuth, row).reindex(solar_zenith.index)

            # 计算遮挡裕度（不依赖于是否启用回溯）
            shading_margin = self._compute_shading_margin(row, solar_elevation, solar_azimuth)

            if self.config.backtrack:
                # 使用 NREL 论文斜坡感知回溯修正 (Equations 11-15)
                if self.config.use_nrel_slope_aware_correction:
                    # 应用斜坡感知修正
                    for idx in base_angles.index:
                        theta_T = theta_true_series.loc[idx]
                        if pd.isna(theta_T):
                            continue

                        # 计算回溯修正角度
                        theta_c = self._calculate_slope_aware_correction(
                            theta_T=float(theta_T),
                            beta_c=cross_axis_tilts[row.table_id],
                            gcr=gcr
                        )

                        # 应用修正（只在需要回溯时）
                        if abs(theta_c) > 1e-6:
                            # 回溯角度 = 真跟踪角度 + 修正角度
                            # 修正角度为负值，减小跟踪角度
                            current_angle = base_angles.loc[idx]
                            if not pd.isna(current_angle):
                                # 使用斜坡感知修正替代原来的简单限制
                                base_angles.loc[idx] = theta_c
                else:
                    # 原有的简单回溯逻辑
                    negative_mask = shading_margin < 0
                    if negative_mask.any():
                        target_index = shading_margin.index[negative_mask]
                        limits = shading_margin.loc[target_index].abs()
                        limited_angles = base_angles.loc[target_index]
                        corrected = np.sign(limited_angles) * np.minimum(np.abs(limited_angles), limits)
                        base_angles.loc[target_index] = corrected
                        # 注意：回溯后遮挡裕度可能仍为负值（极端地形情况）
                        # 不再将所有负裕度设为0，而是保留实际计算的值
                        # 这样可以正确反映地形复杂性导致的潜在遮挡

            angles[row.table_id] = base_angles
            margins[row.table_id] = shading_margin

        angles_df = pd.DataFrame(angles)
        angles_df.index.name = "timestamp"

        true_angles_df = pd.DataFrame(true_angles)
        true_angles_df.index.name = "timestamp"

        margins_df = pd.DataFrame(margins)
        margins_df.index = angles_df.index
        margins_df.index.name = "timestamp"

        # 根据配置选择遮挡系数计算方法
        if self.config.use_nrel_shading_fraction:
            # 使用 NREL 论文 Equation 32 计算遮挡系数
            # fs = GCR * cos(theta_B) / cos(theta_T)
            # 其中 theta_B 是回溯角度，theta_T 是真跟踪角度
            shading_factor = pd.DataFrame(index=angles_df.index, columns=angles_df.columns, dtype=float)

            for col in angles_df.columns:
                gcr = gcr_values.get(col, 0.35)
                beta_c = cross_axis_tilts.get(col, 0.0)
                theta_series = angles_df[col]  # 回溯角度
                theta_true_series = true_angles_df.get(col)  # 真跟踪角度

                for idx in theta_series.index:
                    theta = theta_series.loc[idx]
                    if pd.isna(theta):
                        shading_factor.loc[idx, col] = 1.0
                    else:
                        # 获取真跟踪角度
                        theta_true = None
                        if theta_true_series is not None and idx in theta_true_series.index:
                            theta_true_val = theta_true_series.loc[idx]
                            if not pd.isna(theta_true_val):
                                theta_true = float(theta_true_val)

                        # 使用 NREL 论文公式计算遮挡分数
                        nrel_shading = self._calculate_shading_fraction_nrel(
                            gcr=gcr,
                            theta=float(theta),
                            theta_true=theta_true,
                            beta_c=beta_c
                        )
                        # 遮挡系数 = 1 - 遮挡分数
                        shading_factor.loc[idx, col] = 1.0 - nrel_shading
        else:
            # 使用简化线性模型
            negative_margin = np.clip(-margins_df, 0, None)
            limit = max(self.config.shading_margin_limit, 1e-3)
            shading_factor = 1.0 - (negative_margin / limit)
            shading_factor = shading_factor.clip(lower=0.0, upper=1.0).fillna(1.0)

        result = BacktrackingResult(
            angles=angles_df,
            shading_margin=margins_df,
            shading_factor=shading_factor,
        )

        self._last_result = result
        return result


