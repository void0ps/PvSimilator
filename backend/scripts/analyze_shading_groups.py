"""分析 terrain_validation_angles.csv，输出逐行遮挡统计。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.services.terrain_service import terrain_service  # noqa: E402
from app.services.tracker_geometry import build_tracker_rows  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="分析地形遮挡分组统计")
    parser.add_argument(
        "--input",
        dest="input_path",
        default="backend/analysis/terrain_validation_angles.csv",
        help="输入 CSV 路径",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default="backend/analysis/terrain_validation_shading_summary.json",
        help="输出 JSON 路径",
    )
    return parser.parse_args()


def clean_margin(series: pd.Series) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan)


def load_row_weights() -> Dict[int, Dict[str, float]]:
    layout = terrain_service.load_layout()
    tracker_rows = build_tracker_rows(layout)
    weights: Dict[int, Dict[str, float]] = {}
    for row in tracker_rows:
        weights[int(row.table_id)] = {
            "span_length": float(row.span_length),
            "pile_count": float(row.metadata.get("pile_count", len(row.pile_tops))),
        }
    return weights


def summarise_groups(df: pd.DataFrame) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    weights = load_row_weights()

    total_tables = df["table_id"].nunique()
    group_weighted = 0.0
    total_weight = 0.0

    for group_name, group_df in df.groupby("group"):
        table_ids = sorted(group_df["table_id"].unique())
        shading = group_df["shading_factor"].dropna()
        margin = clean_margin(group_df["shading_margin_deg"]).dropna()

        row_means: Dict[int, float] = {}
        weighted_sum = 0.0
        weight_sum = 0.0
        for table_id, table_df in group_df.groupby("table_id"):
            row_shading = table_df["shading_factor"].dropna()
            if row_shading.empty:
                continue
            row_mean = float(row_shading.mean())
            row_means[int(table_id)] = row_mean
            info = weights.get(int(table_id), {})
            row_weight = info.get("span_length") or info.get("pile_count") or 1.0
            weighted_sum += row_mean * row_weight
            weight_sum += row_weight

        weighted_mean = float(weighted_sum / weight_sum) if weight_sum else None

        group_summary = {
            "table_ids": [int(tid) for tid in table_ids],
            "records": int(len(group_df)),
            "table_count": int(len(table_ids)),
            "mean_shading_factor": float(shading.mean()) if not shading.empty else None,
            "median_shading_factor": float(shading.median()) if not shading.empty else None,
            "min_shading_factor": float(shading.min()) if not shading.empty else None,
            "max_shading_factor": float(shading.max()) if not shading.empty else None,
            "mean_shading_margin_deg": float(margin.mean()) if not margin.empty else None,
            "median_shading_margin_deg": float(margin.median()) if not margin.empty else None,
            "weighted_mean_shading_factor": weighted_mean,
        }

        if weight_sum:
            total_weight += weight_sum
            group_weighted += weighted_sum

        summary[group_name] = group_summary

    overall_weighted_mean = float(group_weighted / total_weight) if total_weight else None

    summary["weighted_mean_shading_factor"] = overall_weighted_mean
    summary["total_table_count"] = int(total_tables)

    table_stats: Dict[str, Any] = {}
    for table_id, table_df in df.groupby("table_id"):
        shading = table_df["shading_factor"].dropna()
        margin = clean_margin(table_df["shading_margin_deg"]).dropna()
        info = weights.get(int(table_id), {})
        table_stats[str(int(table_id))] = {
            "group": table_df["group"].iloc[0],
            "slope_deg": float(table_df["slope_deg"].iloc[0]),
            "records": int(len(table_df)),
            "mean_shading_factor": float(shading.mean()) if not shading.empty else None,
            "median_shading_factor": float(shading.median()) if not shading.empty else None,
            "min_shading_factor": float(shading.min()) if not shading.empty else None,
            "max_shading_factor": float(shading.max()) if not shading.empty else None,
            "mean_shading_margin_deg": float(margin.mean()) if not margin.empty else None,
            "span_length": info.get("span_length"),
            "pile_count": info.get("pile_count"),
        }

    summary["tables"] = table_stats
    return summary


def main() -> None:
    args = parse_args()

    input_path = Path(args.input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    df = pd.read_csv(input_path)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    summary = summarise_groups(df)

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写入 {output_path}")


if __name__ == "__main__":
    main()

