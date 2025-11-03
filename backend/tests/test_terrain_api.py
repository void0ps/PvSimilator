from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import pandas as pd
import pvlib

from app.services.terrain_backtracking import TerrainBacktrackingSolver  # noqa: E402
from app.services.terrain_service import terrain_service  # noqa: E402
from app.services.tracker_analysis import find_row_neighbors  # noqa: E402
from app.services.tracker_geometry import build_tracker_rows  # noqa: E402


def main() -> None:
    print("start")
    payload = terrain_service.load_layout(refresh=False)
    metadata = payload.get("metadata", {})
    tables = payload.get("tables", [])

    print(json.dumps({
        "total_tables": metadata.get("total_tables"),
        "total_piles": metadata.get("total_piles"),
        "sample_table_id": tables[0].get("table_id") if tables else None,
        "sample_pile_count": len(tables[0].get("piles", [])) if tables else 0,
    }, ensure_ascii=False, indent=2))

    if tables:
        sample = tables[0]
        print("Sample piles:")
        for pile in sample.get("piles", [])[:3]:
            print(f"  pile #{pile['index']}: x={pile['x']}, y={pile['y']}, z_top={pile['z_top']}")

    tracker_rows = build_tracker_rows(payload)
    print(f"Tracker rows built: {len(tracker_rows)}")
    if tracker_rows:
        row = tracker_rows[0]
        print(
            f"First-row azimuth: {row.axis_azimuth_deg():.2f} deg | "
            f"avg tilt: {row.average_axis_tilt_deg():.2f} deg | "
            f"pile count: {len(row.pile_tops)}"
        )

    neighbor_map = find_row_neighbors(tracker_rows, max_neighbors=3)
    if tracker_rows:
        sample_neighbors = neighbor_map.get(tracker_rows[0].table_id, [])
        print("Nearest neighbors (by cross-axis distance):")
        for idx, neighbor in enumerate(sample_neighbors, start=1):
            print(
                f"  {idx}. row {neighbor.neighbor_id} | cross-axis: {neighbor.cross_axis_distance:.2f} m | "
                f"along-axis: {neighbor.along_axis_distance:.2f} m | elevation delta: {neighbor.vertical_offset:.2f} m | "
                f"blocking angle: {neighbor.blocking_angle_deg:.2f} deg | side: {neighbor.relative_position}"
            )

    if tracker_rows and tables:
        sample_pile = tables[0]["piles"][0]
        latitude = sample_pile.get("lat") or sample_pile.get("latitude")
        longitude = sample_pile.get("lon") or sample_pile.get("longitude")

        if latitude is not None and longitude is not None:
            site = pvlib.location.Location(latitude, longitude, tz="Pacific/Auckland")
            times = pd.date_range("2024-01-15", periods=6, freq="4H", tz=site.tz)
            solar = site.get_solarposition(times)

            solver = TerrainBacktrackingSolver(tracker_rows, neighbor_map)
            result = solver.compute_tracker_angles(
                solar["apparent_zenith"],
                solar["azimuth"],
            )

            print("Sample tracker angles (deg):")
            print(result.angles.iloc[:, :3].round(2))

            print("Shading margin (deg):")
            print(result.shading_margin.iloc[:, :3].round(2))

            print("Shading factor:")
            print(result.shading_factor.iloc[:, :3].round(2))
        else:
            print("Latitude/Longitude missing; skip backtracking preview.")


if __name__ == "__main__":
    main()


