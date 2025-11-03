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

    def _singleaxis(
        self,
        solar_zenith: pd.Series,
        solar_azimuth: pd.Series,
        row: TrackerRow,
    ) -> pd.Series:
        pitch = max(self.get_row_pitch(row.table_id), self.config.module_width * 1.01)
        gcr = np.clip(self.config.module_width / pitch, 0.05, 0.9)

        tracking_result = pvlib.tracking.singleaxis(
            apparent_zenith=solar_zenith,
            apparent_azimuth=solar_azimuth,
            axis_tilt=row.average_axis_tilt_deg(),
            axis_azimuth=row.axis_azimuth_deg(),
            max_angle=self.config.max_angle,
            backtrack=self.config.backtrack,
            gcr=gcr,
            cross_axis_tilt=0.0,
        )

        return tracking_result["tracker_theta"]

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
        """计算 terrain-aware backtracking 结果。"""

        solar_elevation = 90.0 - solar_zenith

        angles: Dict[int, pd.Series] = {}
        margins: Dict[int, pd.Series] = {}

        for row in self.rows:
            base_angles = self._singleaxis(solar_zenith, solar_azimuth, row).reindex(solar_zenith.index)
            shading_margin = self._compute_shading_margin(row, solar_elevation, solar_azimuth)

            negative_mask = shading_margin < 0
            if negative_mask.any():
                target_index = shading_margin.index[negative_mask]
                limits = shading_margin.loc[target_index].abs()
                limited_angles = base_angles.loc[target_index]
                corrected = np.sign(limited_angles) * np.minimum(np.abs(limited_angles), limits)
                base_angles.loc[target_index] = corrected

            angles[row.table_id] = base_angles
            margins[row.table_id] = shading_margin

        angles_df = pd.DataFrame(angles)
        angles_df.index.name = "timestamp"

        margins_df = pd.DataFrame(margins)
        margins_df.index = angles_df.index
        margins_df.index.name = "timestamp"

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


