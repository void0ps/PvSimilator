"""生成地形遮挡算法验证用的数据集。

输出文件：`backend/analysis/terrain_validation_angles.csv`
包含高坡度与低坡度示例跟踪行的时序跟踪角、遮挡裕量与遮挡因子。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
import pvlib

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.append(str(PROJECT_ROOT / "backend"))

from app.services.terrain_service import terrain_service  # noqa: E402
from app.services.tracker_geometry import build_tracker_rows  # noqa: E402
from app.services.tracker_analysis import find_row_neighbors  # noqa: E402
from app.services.terrain_backtracking import TerrainBacktrackingSolver  # noqa: E402


def load_case_ids(path: Path) -> Dict[str, List[int]]:
    if not path.exists():
        raise FileNotFoundError(f"案例文件不存在: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "high": [item["table_id"] for item in data.get("high_slope", [])[:3]],
        "low": [item["table_id"] for item in data.get("low_slope", [])[:3]],
    }


def main() -> None:
    layout = terrain_service.load_layout()
    tracker_rows = build_tracker_rows(layout)
    row_map = {row.table_id: row for row in tracker_rows}
    neighbor_map = find_row_neighbors(tracker_rows, max_neighbors=4)

    candidates_path = PROJECT_ROOT / "backend" / "case_candidates.json"
    groups = load_case_ids(candidates_path)

    sample_table = layout["tables"][0]
    first_pile = sample_table["piles"][0]
    latitude = first_pile.get("lat") or first_pile.get("latitude")
    longitude = first_pile.get("lon") or first_pile.get("longitude")
    if latitude is None or longitude is None:
        raise RuntimeError("地形数据缺少经纬度，无法生成太阳位置")

    site = pvlib.location.Location(latitude, longitude, tz="Pacific/Auckland")
    times = pd.date_range(
        start="2024-01-15 05:00",
        end="2024-01-15 20:00",
        freq="15min",
        tz=site.tz,
    )
    solar = site.get_solarposition(times)

    records: List[Dict[str, float]] = []

    for group, table_ids in groups.items():
        if not table_ids:
            continue
        subset_rows: Iterable = [row_map[tid] for tid in table_ids if tid in row_map]
        solver = TerrainBacktrackingSolver(subset_rows, neighbor_map)
        result = solver.compute_tracker_angles(
            solar["apparent_zenith"],
            solar["azimuth"],
        )

        for table_id in table_ids:
            if table_id not in result.angles.columns:
                continue
            row = row_map[table_id]
            for ts in times:
                records.append(
                    {
                        "group": group,
                        "table_id": table_id,
                        "timestamp": ts.isoformat(),
                        "slope_deg": row.slope_deg,
                        "tracker_angle_deg": float(result.angles.at[ts, table_id]),
                        "shading_margin_deg": float(result.shading_margin.at[ts, table_id]),
                        "shading_factor": float(result.shading_factor.at[ts, table_id]),
                    }
                )

    output_dir = PROJECT_ROOT / "backend" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "terrain_validation_angles.csv"
    pd.DataFrame(records).to_csv(output_path, index=False)
    print(f"写入 {output_path}，记录数 {len(records)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        import traceback

        print("生成验证数据时发生异常:")
        traceback.print_exc()
        raise

