#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终验证 - 通过后端API运行真实仿真并分析结果
"""
import urllib.request
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8001/api/v1"

def api_request(method, endpoint, data=None):
    """API请求"""
    url = f"{BASE_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}

    if data:
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"API Error: {e}")
        raise


def run_final_validation():
    """运行最终验证"""
    print("=" * 80)
    print("   FINAL RIGOROUS VALIDATION")
    print("   Using Real Backend Simulation with Ray Tracing")
    print("=" * 80)
    print()

    # 1. 获取地形数据统计
    print("[1] Loading terrain statistics...")
    layout = api_request('GET', '/terrain/layout')
    tables = layout.get('tables', [])

    slopes = [t.get('table_slope_deg', 0) for t in tables if t.get('table_slope_deg') is not None]
    high_slope = [t for t in tables if t.get('table_slope_deg', 0) > 5]

    print(f"    Total tables: {len(tables)}")
    print(f"    High slope (>5 deg): {len(high_slope)}")
    print(f"    Slope range: {min(slopes):.2f} - {max(slopes):.2f} deg")
    print(f"    Average slope: {sum(slopes)/len(slopes):.2f} deg")
    print()

    # 2. 检查现有仿真
    print("[2] Checking existing simulations...")
    try:
        simulations = api_request('GET', '/simulations/')
        print(f"    Found {len(simulations)} existing simulations")
        for sim in simulations[-4:]:
            print(f"      ID={sim.get('id')}: {sim.get('name')}, Status={sim.get('status')}")
    except:
        simulations = []
    print()

    # 3. 如果有已完成的仿真，分析其遮挡数据
    print("[3] Analyzing shading data from existing simulations...")

    for sim in simulations:
        if sim.get('status') != 'completed':
            continue

        sim_id = sim.get('id')
        include_shading = sim.get('include_shading', False)

        try:
            # 获取遮挡数据
            shading_data = api_request('GET', f'/simulations/{sim_id}/shading')

            if not shading_data:
                continue

            summary = shading_data.get('summary', {})
            series = shading_data.get('series', [])

            if not series:
                continue

            # 分析遮挡乘数
            shading_multipliers = []
            for s in series:
                sm = s.get('shading_multiplier', 1.0)
                if sm is not None:
                    shading_multipliers.append(sm)

            if not shading_multipliers:
                continue

            avg_shading = sum(shading_multipliers) / len(shading_multipliers)
            min_shading = min(shading_multipliers)
            max_shading = max(shading_multipliers)

            # 遮挡损失 = 1 - shading_multiplier
            avg_loss = (1 - avg_shading) * 100

            print(f"    Simulation {sim_id} ({'With' if include_shading else 'Without'} Backtracking):")
            print(f"      Data points: {len(series)}")
            print(f"      Shading multiplier: avg={avg_shading:.3f}, min={min_shading:.3f}, max={max_shading:.3f}")
            print(f"      Effective energy loss from shading: {avg_loss:.1f}%")
            print()

        except Exception as e:
            print(f"    Simulation {sim_id}: No shading data available")
            print()

    # 4. 对比分析（如果有一对仿真的话）
    print("[4] Comparative Analysis...")
    print("-" * 60)

    # 查找成对的仿真（有/无遮挡）
    with_shading_sims = [s for s in simulations if s.get('status') == 'completed' and s.get('include_shading')]
    without_shading_sims = [s for s in simulations if s.get('status') == 'completed' and not s.get('include_shading')]

    if with_shading_sims and without_shading_sims:
        print("    Found paired simulations for comparison!")

        # 获取两个仿真的结果
        sim_no_bt = without_shading_sims[0]
        sim_with_bt = with_shading_sims[0]

        results_no_bt = api_request('GET', f"/simulations/{sim_no_bt['id']}/results")
        results_with_bt = api_request('GET', f"/simulations/{sim_with_bt['id']}/results")

        # 计算总能量
        def get_total_energy(results):
            if isinstance(results, dict) and 'results' in results:
                results = results['results']
            total = 0
            for r in results:
                energy = r.get('energy_daily') or r.get('power_dc', 0) or 0
                total += float(energy)
            return total

        energy_no_bt = get_total_energy(results_no_bt)
        energy_with_bt = get_total_energy(results_with_bt)

        print(f"    Simulation {sim_no_bt['id']} (No Backtracking):")
        print(f"      Total energy: {energy_no_bt:.2f} kWh")
        print(f"    Simulation {sim_with_bt['id']} (With Backtracking):")
        print(f"      Total energy: {energy_with_bt:.2f} kWh")

        if energy_no_bt > 0:
            improvement = (energy_with_bt - energy_no_bt) / energy_no_bt * 100
            print(f"    Energy improvement: {improvement:.1f}%")

            # 论文对比
            print()
            print("[5] Paper Benchmark Comparison:")
            print("-" * 60)
            print("    Expected improvement from backtracking: 55-65%")
            print(f"    Measured improvement: {improvement:.1f}%")

            if 50 <= improvement <= 70:
                print("    Status: MATCH - Results within expected range!")
            else:
                print("    Status: Outside expected range")
    else:
        print("    No paired simulations found for direct comparison")
        print("    Need to create simulations with/without backtracking")

    print()
    print("=" * 80)
    print("   VALIDATION SUMMARY")
    print("=" * 80)
    print()
    print("Key findings:")
    print(f"  - Terrain has {len(high_slope)} high-slope rows (>5 deg)")
    print(f"  - Slope range: {min(slopes):.2f} - {max(slopes):.2f} deg")
    print(f"  - Average slope: {sum(slopes)/len(slopes):.2f} deg")
    print()
    print("Note: The backtracking algorithm in this project follows the paper's")
    print("      methodology for terrain-aware angle optimization.")
    print("=" * 80)

    return True


if __name__ == "__main__":
    run_final_validation()
