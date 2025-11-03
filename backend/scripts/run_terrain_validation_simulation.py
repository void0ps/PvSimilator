"""运行带/不带地形遮挡的对比模拟，并输出汇总数据。

输出：
- `backend/analysis/terrain_validation_power.csv`
- `backend/analysis/terrain_validation_power_summary.json`
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple

import pandas as pd

import sys
import argparse
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.models.pv_system import PVSystem  # noqa: E402
from app.models.simulation import Simulation, SimulationResult  # noqa: E402
from app.api.simulations import run_simulation_task  # noqa: E402


def ensure_system() -> PVSystem:
    session = SessionLocal()
    try:
        system = session.query(PVSystem).first()
        if system is None:
            raise RuntimeError("数据库中缺少光伏系统，请先运行 add_test_pv_systems.py")
        # 预加载必要字段
        _ = system.latitude, system.longitude
        return system
    finally:
        session.close()

def get_or_create_simulation(
    system_id: int,
    name: str,
    include_shading: bool,
    start_dt: datetime,
    end_dt: datetime,
    time_resolution: str,
    extra_key: str,
) -> Simulation:
    session = SessionLocal()
    try:
        simulation = (
            session.query(Simulation)
            .filter(
                Simulation.system_id == system_id,
                Simulation.name == name,
                Simulation.start_date == start_dt,
                Simulation.end_date == end_dt,
                Simulation.time_resolution == time_resolution,
                Simulation.description == extra_key,
            )
            .order_by(Simulation.id.desc())
            .first()
        )
        if simulation:
            session.expunge(simulation)
            session.close()
            return simulation

        simulation = Simulation(
            system_id=system_id,
            name=name,
            description=extra_key,
            start_date=start_dt,
            end_date=end_dt,
            time_resolution=time_resolution,
            weather_source="nasa_sse",
            include_shading=include_shading,
            include_soiling=False,
            include_degradation=False,
            shading_factor=0.0,
            soiling_loss=0.0,
            degradation_rate=0.0,
        )
        session.add(simulation)
        session.commit()
        session.refresh(simulation)
        session.expunge(simulation)
        return simulation
    finally:
        session.close()


def ensure_simulation_completed(simulation: Simulation) -> int:
    session = SessionLocal()
    try:
        sim = session.query(Simulation).get(simulation.id)
        if sim is None:
            raise RuntimeError(f"模拟 {simulation.id} 不存在")
        if sim.status != "completed":
            print(f"开始运行模拟 {sim.name} (ID={sim.id})，include_shading={sim.include_shading}")
            asyncio.run(run_simulation_task(sim.id, session))
            print(f"模拟 {sim.name} 完成，状态={sim.status}")
        else:
            print(f"复用已完成模拟 {sim.name} (ID={sim.id})")
        return sim.id
    finally:
        session.close()


def fetch_results(simulation_id: int) -> pd.DataFrame:
    session = SessionLocal()
    try:
        rows: List[SimulationResult] = (
            session.query(SimulationResult)
            .filter(SimulationResult.simulation_id == simulation_id)
            .order_by(SimulationResult.timestamp)
            .all()
        )
        records: List[Dict[str, float]] = []
        for row in rows:
            detailed = row.detailed_data or {}
            records.append(
                {
                    "timestamp": row.timestamp,
                    "power_dc": row.power_dc,
                    "power_ac": row.power_ac,
                    "efficiency": row.efficiency,
                    "irradiance_global": row.irradiance_global,
                    "terrain_shading_multiplier": detailed.get("terrain_shading_multiplier"),
                    "shading_multiplier": detailed.get("shading_multiplier"),
                }
            )
        return pd.DataFrame(records)
    finally:
        session.close()

def summarise_variant(
    df: pd.DataFrame,
    weighting: str,
    row_summary: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date

    total_energy_kwh = float(df["power_ac"].fillna(0).sum() / 1000.0)

    daily_energy = (
        df.groupby("date")["power_ac"].sum().div(1000.0).apply(float).to_dict()
    )
    daily_energy = {str(k): v for k, v in daily_energy.items()}

    terrain_mean = None
    terrain_mean_field = None
    terrain_mean_row = None
    terrain_daily: Dict[str, float] = {}
    if "terrain_shading_multiplier" in df:
        terrain_series = df["terrain_shading_multiplier"].dropna()
        if not terrain_series.empty:
            terrain_mean_field = float(terrain_series.mean())
            terrain_mean = terrain_mean_field
            if weighting == "row":
                if row_summary and "tables" in row_summary:
                    weighted_sum = 0.0
                    weight_total = 0.0
                    for entry in row_summary["tables"].values():
                        mean_factor = entry.get("mean_shading_factor")
                        if mean_factor is None:
                            continue
                        span_length = entry.get("span_length")
                        pile_count = entry.get("pile_count")
                        weight = None
                        if isinstance(span_length, (int, float)) and span_length > 0:
                            weight = span_length
                        elif isinstance(pile_count, (int, float)) and pile_count > 0:
                            weight = pile_count
                        else:
                            weight = 1.0
                        weighted_sum += float(mean_factor) * float(weight)
                        weight_total += float(weight)
                    if weight_total > 0:
                        terrain_mean_row = float(weighted_sum / weight_total)
                        terrain_mean = terrain_mean_row
        terrain_daily = {
            str(date): float(series.mean())
            for date, series in df.groupby("date")["terrain_shading_multiplier"]
            if not series.dropna().empty
        }

    return {
        "total_energy_kwh": total_energy_kwh,
        "mean_shading_multiplier": terrain_mean,
        "mean_shading_multiplier_field": terrain_mean_field,
        "mean_shading_multiplier_row": terrain_mean_row,
        "daily_energy_kwh": daily_energy,
        "daily_mean_shading_multiplier": terrain_daily,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行地形遮挡验证模拟")
    parser.add_argument(
        "--start",
        dest="start_date",
        default="2024-01-15",
        help="开始日期 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        dest="end_date",
        default="2024-01-17",
        help="结束日期 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--resolution",
        dest="time_resolution",
        default="hourly",
        choices=["hourly", "daily"],
        help="模拟时间分辨率",
    )
    parser.add_argument(
        "--weighting",
        dest="weighting",
        default="field",
        choices=["field", "row"],
        help="遮挡乘数权重: field=整场平均, row=按行均值加权",
    )
    parser.add_argument(
        "--shading-summary",
        dest="shading_summary_path",
        default="backend/analysis/terrain_validation_shading_summary.json",
        help="逐行遮挡摘要 JSON 路径 (row 权重时使用)",
    )
    return parser.parse_args()


def prepare_datetimes(start_date: str, end_date: str) -> Tuple[datetime, datetime]:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=0, second=0, microsecond=0)
    if end_dt < start_dt:
        raise ValueError("结束日期不能早于开始日期")
    return start_dt, end_dt


def main(args: argparse.Namespace) -> None:
    start_dt, end_dt = prepare_datetimes(args.start_date, args.end_date)

    system = ensure_system()
    variants = [
        ("terrain_shading", True),
        ("baseline_no_shading", False),
    ]

    outputs: Dict[str, Dict[str, Any]] = {}
    dfs: List[pd.DataFrame] = []

    row_summary: Dict[str, Any] | None = None
    if args.weighting == "row" and args.shading_summary_path:
        summary_path = Path(args.shading_summary_path)
        if summary_path.exists():
            try:
                row_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover
                print(f"无法读取遮挡摘要 {summary_path}: {exc}")
        else:
            print(f"警告：未找到遮挡摘要文件 {summary_path}，改用整场平均")
            row_summary = None

    for variant_name, include_shading in variants:
        variant_start = time.perf_counter()

        sim_name = f"验证-{variant_name}-{args.weighting}"
        extra_key = f"Terrain-aware backtracking 验证[{args.weighting}]"
        sim = get_or_create_simulation(
            system.id,
            sim_name,
            include_shading,
            start_dt,
            end_dt,
            args.time_resolution,
            extra_key,
        )
        sim_id = ensure_simulation_completed(sim)

        df = fetch_results(sim_id)
        if df.empty:
            print(f"警告：模拟 {variant_name} 未生成结果")
            continue
        df["variant"] = variant_name
        dfs.append(df)

        summary = summarise_variant(
            df,
            args.weighting,
            row_summary if include_shading else None,
        )
        summary["simulation_id"] = sim_id
        summary["runtime_seconds"] = time.perf_counter() - variant_start
        summary["record_count"] = int(len(df))
        outputs[variant_name] = summary

    if not dfs:
        raise RuntimeError("无可用模拟数据")

    if "baseline_no_shading" in outputs and "terrain_shading" in outputs:
        baseline_energy = outputs["baseline_no_shading"].get("total_energy_kwh")
        shading_energy = outputs["terrain_shading"].get("total_energy_kwh")
        if baseline_energy and baseline_energy > 0:
            relative = (shading_energy / baseline_energy) - 1.0
            outputs["terrain_shading"]["relative_loss_pct"] = float(relative * 100.0)
            outputs["baseline_no_shading"]["relative_loss_pct"] = 0.0

    merged = pd.concat(dfs, ignore_index=True)
    output_dir = BACKEND_ROOT / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = output_dir / "terrain_validation_power.csv"
    merged.to_csv(data_path, index=False)
    summary_path = output_dir / "terrain_validation_power_summary.json"
    summary_path.write_text(json.dumps(outputs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写入功率对比数据: {data_path}")
    print(f"写入功率汇总: {summary_path}")


if __name__ == "__main__":
    try:
        arguments = parse_args()
        main(arguments)
    except Exception:
        import traceback

        print("模拟运行失败:")
        traceback.print_exc()
        raise

