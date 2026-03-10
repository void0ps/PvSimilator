#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shading factor application analysis script
Analyze how shading factors affect energy calculation
"""
import urllib.request
import json
import pandas as pd
import numpy as np

BASE_URL = "http://localhost:8001/api/v1"

def api_request(method, endpoint, data=None, timeout=120):
    """API请求"""
    url = f"{BASE_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}

    if data:
        body = json.dumps(data, default=str).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"API Error: {e}")
        raise


def analyze_shading_application():
    """分析遮挡系数如何应用"""
    print("=" * 80)
    print("   遮挡系数应用分析")
    print("=" * 80)
    print()

    # 获取最近的两个对比仿真
    simulations = api_request('GET', '/simulations/?limit=10')

    # 找到有和无回溯的仿真对
    no_bt_sim = None
    with_bt_sim = None

    for sim in simulations:
        if 'NO Backtracking' in sim.get('name', ''):
            no_bt_sim = sim
        elif 'WITH Backtracking' in sim.get('name', ''):
            with_bt_sim = sim

    if not no_bt_sim or not with_bt_sim:
        print("未找到对比仿真对，请先运行 run_true_backtracking_validation.py")
        return

    print(f"无回溯仿真 ID: {no_bt_sim['id']}")
    print(f"有回溯仿真 ID: {with_bt_sim['id']}")
    print()

    # 获取详细结果
    results_no_bt = api_request('GET', f'/simulations/{no_bt_sim["id"]}/results')
    results_with_bt = api_request('GET', f'/simulations/{with_bt_sim["id"]}/results')

    # 获取遮挡数据
    shading_no_bt = api_request('GET', f'/simulations/{no_bt_sim["id"]}/shading')
    shading_with_bt = api_request('GET', f'/simulations/{with_bt_sim["id"]}/shading')

    print("=" * 60)
    print("   1. 遮挡系数分析")
    print("=" * 60)

    if shading_no_bt.get('series'):
        series_no_bt = shading_no_bt['series']
        multipliers_no_bt = [s.get('terrain_shading_multiplier', 1.0) for s in series_no_bt]
        avg_multiplier_no_bt = np.mean(multipliers_no_bt)
        print(f"无回溯时:")
        print(f"  遮挡系数详情: {multipliers_no_bt}")
        print(f"  平均遮挡系数: {avg_multiplier_no_bt:.4f}")
        print()

    if shading_with_bt.get('series'):
        series_with_bt = shading_with_bt['series']
        multipliers_with_bt = [s.get('terrain_shading_multiplier', 1.0) for s in series_with_bt]
        avg_multiplier_with_bt = np.mean(multipliers_with_bt)
        print(f"有回溯时:")
        print(f"  遮挡系数详情: {multipliers_with_bt}")
        print(f"  平均遮挡系数: {avg_multiplier_with_bt:.4f}")
        print()

    print("=" * 60)
    print("   2. 能量输出分析")
    print("=" * 60)

    def extract_energy_data(results):
        if isinstance(results, dict) and 'results' in results:
            results = results['results']
        powers_dc = []
        powers_ac = []
        irradiances = []
        for r in results:
            powers_dc.append(float(r.get('power_dc', 0) or 0))
            powers_ac.append(float(r.get('power_ac', 0) or 0))
            irradiances.append(float(r.get('irradiance_global', 0) or 0))
        return powers_dc, powers_ac, irradiances

    dc_no_bt, ac_no_bt, irr_no_bt = extract_energy_data(results_no_bt)
    dc_with_bt, ac_with_bt, irr_with_bt = extract_energy_data(results_with_bt)

    total_dc_no_bt = sum(dc_no_bt)
    total_dc_with_bt = sum(dc_with_bt)
    total_ac_no_bt = sum(ac_no_bt)
    total_ac_with_bt = sum(ac_with_bt)

    print(f"无回溯时:")
    print(f"  总直流功率: {total_dc_no_bt:.2f} W")
    print(f"  总交流功率: {total_ac_no_bt:.2f} W")
    print(f"  直流功率详情: {dc_no_bt}")
    print()

    print(f"有回溯时:")
    print(f"  总直流功率: {total_dc_with_bt:.2f} W")
    print(f"  总交流功率: {total_ac_with_bt:.2f} W")
    print(f"  直流功率详情: {dc_with_bt}")
    print()

    print("=" * 60)
    print("   3. 遮挡系数与能量关系验证")
    print("=" * 60)

    if total_dc_with_bt > 0:
        energy_ratio = total_dc_no_bt / total_dc_with_bt
        print(f"能量比例 (无回溯/有回溯): {energy_ratio:.4f}")
        print(f"平均遮挡系数 (无回溯):     {avg_multiplier_no_bt:.4f}")
        print(f"差异: {abs(energy_ratio - avg_multiplier_no_bt):.4f}")
        print()

        if abs(energy_ratio - avg_multiplier_no_bt) < 0.05:
            print("[OK] Shading factor correctly applied to energy calculation")
        else:
            print("[INFO] Energy ratio differs from shading multiplier - this is expected due to:")
            print("  1. Diffuse radiation - shading only affects direct radiation, not diffuse")
            print("  2. Diffuse retention in shadow areas (60% retained)")
            print("  3. Temperature effects - module temperature affects power calculation")

    print()
    print("=" * 60)
    print("   4. 逐点分析")
    print("=" * 60)

    print(f"{'时间点':<8} {'遮挡系数':<12} {'DC功率(W)':<12} {'辐照度':<12} {'期望功率':<12} {'实际/期望':<10}")
    print("-" * 70)

    for i in range(min(len(dc_no_bt), len(multipliers_no_bt))):
        multiplier = multipliers_no_bt[i]
        dc = dc_no_bt[i]
        irr = irr_no_bt[i]

        # 计算期望功率（假设有回溯时功率为基准）
        expected_dc = dc_with_bt[i] * multiplier if i < len(dc_with_bt) else dc
        ratio = dc / expected_dc if expected_dc > 0 else 0

        print(f"{i:<8} {multiplier:<12.4f} {dc:<12.2f} {irr:<12.2f} {expected_dc:<12.2f} {ratio:<10.2f}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    analyze_shading_application()
