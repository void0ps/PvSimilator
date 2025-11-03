from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import numpy as np


def _as_point(entry: Dict[str, Any], key: str) -> np.ndarray:
    value = entry.get(key)
    if value is None:
        raise ValueError(f"缺少字段 {key}，无法构建桩点")
    return np.asarray(value, dtype=float)


def _safe_height(entry: Dict[str, Any]) -> float:
    if entry.get("z_top") is not None:
        return float(entry["z_top"])
    if entry.get("z_ground") is not None:
        return float(entry["z_ground"])
    raise ValueError("桩点缺少高度信息 (z_top 或 z_ground)")


@dataclass
class TrackerRow:
    table_id: int
    zone_id: Optional[str]
    preset_type: Optional[str]
    axis_origin: np.ndarray
    axis_direction: np.ndarray
    span_length: float
    pile_tops: List[np.ndarray]
    pile_grounds: List[np.ndarray]
    slope_deg: Optional[float]
    slope_delta_deg: Optional[float]
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def centroid(self) -> np.ndarray:
        return np.mean(np.vstack(self.pile_tops), axis=0)

    def horizontal_axis_vector(self) -> np.ndarray:
        vector = self.axis_direction.copy()
        vector[2] = 0.0
        norm = np.linalg.norm(vector)
        if norm == 0:
            return np.array([0.0, 0.0, 0.0])
        return vector / norm

    def axis_azimuth_deg(self) -> float:
        horizontal = self.axis_direction[:2]
        azimuth_rad = math.atan2(horizontal[0], horizontal[1])
        azimuth_deg = math.degrees(azimuth_rad)
        return (azimuth_deg + 360.0) % 360.0

    def average_axis_tilt_deg(self) -> float:
        horizontal_length = np.linalg.norm(self.axis_direction[:2])
        if horizontal_length == 0:
            return 0.0
        return math.degrees(math.atan2(self.axis_direction[2], horizontal_length))

    def pile_offsets(self) -> List[float]:
        offsets: List[float] = [0.0]
        origin = self.pile_tops[0]
        for point in self.pile_tops[1:]:
            offsets.append(np.linalg.norm(point[:2] - origin[:2]))
        return offsets

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "zone_id": self.zone_id,
            "preset_type": self.preset_type,
            "axis_origin": self.axis_origin.tolist(),
            "axis_direction": self.axis_direction.tolist(),
            "span_length": float(self.span_length),
            "slope_deg": self.slope_deg,
            "slope_delta_deg": self.slope_delta_deg,
            "average_axis_tilt_deg": self.average_axis_tilt_deg(),
            "axis_azimuth_deg": self.axis_azimuth_deg(),
            "pile_offsets": self.pile_offsets(),
            "pile_tops": [pt.tolist() for pt in self.pile_tops],
            "pile_grounds": [pt.tolist() for pt in self.pile_grounds],
            "centroid": self.centroid().tolist(),
            "notes": self.notes,
            "metadata": self.metadata,
        }


def build_tracker_rows(layout: Dict[str, Any]) -> List[TrackerRow]:
    tables = layout.get("tables", [])
    tracker_rows: List[TrackerRow] = []

    for table in tables:
        piles = table.get("piles", [])
        if len(piles) < 2:
            continue

        pile_tops: List[np.ndarray] = []
        pile_grounds: List[np.ndarray] = []

        for pile in piles:
            x = pile.get("x")
            y = pile.get("y")
            if x is None or y is None:
                raise ValueError(f"Table {table.get('table_id')} 中存在缺失坐标的桩点")

            z_top = pile.get("z_top")
            z_ground = pile.get("z_ground")

            if z_top is None and z_ground is None:
                raise ValueError(f"Table {table.get('table_id')} 的桩点缺失高度信息")

            top_point = np.array([float(x), float(y), float(z_top if z_top is not None else z_ground)])
            ground_point = np.array([float(x), float(y), float(z_ground if z_ground is not None else z_top)])

            pile_tops.append(top_point)
            pile_grounds.append(ground_point)

        axis_vector = pile_tops[-1] - pile_tops[0]
        span_length = float(np.linalg.norm(axis_vector))
        if span_length == 0:
            continue

        axis_direction = axis_vector / span_length

        slope_deg = table.get("table_slope_deg")
        slope_delta = table.get("slope_delta_deg")

        tracker_rows.append(
            TrackerRow(
                table_id=int(table.get("table_id")),
                zone_id=table.get("zone_id"),
                preset_type=table.get("preset_type"),
                axis_origin=pile_tops[0],
                axis_direction=axis_direction,
                span_length=span_length,
                pile_tops=pile_tops,
                pile_grounds=pile_grounds,
                slope_deg=float(slope_deg) if slope_deg is not None else None,
                slope_delta_deg=float(slope_delta) if slope_delta is not None else None,
                notes=table.get("notes"),
                metadata={
                    "table_direction": table.get("table_direction"),
                    "pile_count": len(pile_tops),
                },
            )
        )

    return tracker_rows


def serialize_tracker_rows(rows: Iterable[TrackerRow]) -> List[Dict[str, Any]]:
    return [row.to_dict() for row in rows]


