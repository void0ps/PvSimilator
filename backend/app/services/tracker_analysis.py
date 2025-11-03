from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Iterable, List

import numpy as np

from .tracker_geometry import TrackerRow


@dataclass
class RowNeighbor:
    source_id: int
    neighbor_id: int
    horizontal_distance: float
    cross_axis_distance: float
    along_axis_distance: float
    vertical_offset: float
    slope_delta_deg: float
    blocking_angle_deg: float
    relative_position: int

    def to_dict(self) -> Dict[str, float | int]:
        return {
            "source_id": self.source_id,
            "neighbor_id": self.neighbor_id,
            "horizontal_distance": self.horizontal_distance,
            "cross_axis_distance": self.cross_axis_distance,
            "along_axis_distance": self.along_axis_distance,
            "vertical_offset": self.vertical_offset,
            "slope_delta_deg": self.slope_delta_deg,
            "blocking_angle_deg": self.blocking_angle_deg,
            "relative_position": self.relative_position,
        }


def _projection_components(row: TrackerRow, diff_xy: np.ndarray) -> tuple[float, float]:
    axis_dir = row.horizontal_axis_vector()[:2]
    if np.linalg.norm(axis_dir) == 0:
        return 0.0, np.linalg.norm(diff_xy)
    perp_dir = np.array([-axis_dir[1], axis_dir[0]])
    along = float(np.dot(diff_xy, axis_dir))
    cross = float(np.dot(diff_xy, perp_dir))
    return along, cross


def find_row_neighbors(rows: Iterable[TrackerRow], max_neighbors: int = 4) -> Dict[int, List[RowNeighbor]]:
    rows_list = list(rows)
    centroids = {row.table_id: row.centroid() for row in rows_list}

    neighbor_map: Dict[int, List[RowNeighbor]] = {row.table_id: [] for row in rows_list}

    for i, row_a in enumerate(rows_list):
        for row_b in rows_list[i + 1 :]:
            cent_a = centroids[row_a.table_id]
            cent_b = centroids[row_b.table_id]

            diff = cent_b - cent_a
            diff_xy = diff[:2]
            horizontal_distance = float(np.linalg.norm(diff_xy))
            vertical_offset = float(diff[2])

            along_ab, cross_ab = _projection_components(row_a, diff_xy)
            along_ba, cross_ba = _projection_components(row_b, -diff_xy)

            if abs(cross_ab) < 0.1 and abs(along_ab) > 1.0:
                # 近乎共线但相距较远，视为沿轴延伸，不计作跨行邻居
                continue

            def _blocking_angle(cross_distance: float, vertical: float) -> float:
                if abs(cross_distance) < 1e-6:
                    return 90.0 if vertical > 0 else -90.0 if vertical < 0 else 0.0
                return math.degrees(math.atan2(vertical, cross_distance))

            neighbor_a = RowNeighbor(
                source_id=row_a.table_id,
                neighbor_id=row_b.table_id,
                horizontal_distance=horizontal_distance,
                cross_axis_distance=cross_ab,
                along_axis_distance=along_ab,
                vertical_offset=vertical_offset,
                slope_delta_deg=(row_b.average_axis_tilt_deg() - row_a.average_axis_tilt_deg()),
                blocking_angle_deg=_blocking_angle(cross_ab, vertical_offset),
                relative_position=int(np.sign(cross_ab)) if abs(cross_ab) >= 1e-6 else 0,
            )

            neighbor_b = RowNeighbor(
                source_id=row_b.table_id,
                neighbor_id=row_a.table_id,
                horizontal_distance=horizontal_distance,
                cross_axis_distance=cross_ba,
                along_axis_distance=along_ba,
                vertical_offset=-vertical_offset,
                slope_delta_deg=(row_a.average_axis_tilt_deg() - row_b.average_axis_tilt_deg()),
                blocking_angle_deg=_blocking_angle(cross_ba, -vertical_offset),
                relative_position=int(np.sign(cross_ba)) if abs(cross_ba) >= 1e-6 else 0,
            )

            neighbor_map[row_a.table_id].append(neighbor_a)
            neighbor_map[row_b.table_id].append(neighbor_b)

    # 按横向距离排序并裁剪邻居数量
    for table_id, neighbors in neighbor_map.items():
        neighbors.sort(key=lambda n: abs(n.cross_axis_distance))
        if max_neighbors and len(neighbors) > max_neighbors:
            neighbor_map[table_id] = neighbors[:max_neighbors]

    return neighbor_map


def serialize_neighbors(neighbor_map: Dict[int, List[RowNeighbor]]) -> Dict[int, List[Dict[str, float | int]]]:
    return {table_id: [neighbor.to_dict() for neighbor in neighbors] for table_id, neighbors in neighbor_map.items()}


def compute_row_pitch(neighbor_map: Dict[int, List[RowNeighbor]], default_pitch: float = 8.0) -> Dict[int, float]:
    """为每条跟踪行估算行间距（pitch）。"""

    row_pitch: Dict[int, float] = {}
    for table_id, neighbors in neighbor_map.items():
        spacings = [abs(neighbor.cross_axis_distance) for neighbor in neighbors if abs(neighbor.cross_axis_distance) > 1e-3]
        if spacings:
            row_pitch[table_id] = float(min(spacings))
        else:
            row_pitch[table_id] = float(default_pitch)
    return row_pitch


