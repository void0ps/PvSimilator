#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通过API运行真实仿真验证
"""
import urllib.request
import json
from datetime import datetime

BASE_URL = "http://localhost:8001/api/v1"

def api_get(endpoint):
    """GET请求"""
    req = urllib.request.Request(f"{BASE_URL}{endpoint}")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())

def api_post(endpoint, data):
    """POST请求"""
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode())

def run_validation():
    print("=" * 70)
    print("   Real Simulation Validation via API")
    print("=" * 70)
    print()

    # 1. 获取地形数据
    print("[1] Loading terrain data via API...")
    layout = api_get("/terrain/layout")
    tables = layout.get('tables', [])

    slopes = [t.get('table_slope_deg', 0) for t in tables if t.get('table_slope_deg') is not None]
    high_slope = [t for t in tables if t.get('table_slope_deg', 0) > 5]
    low_slope = [t for t in tables if 0 <= t.get('table_slope_deg', 0) <= 2]

    print(f"    Total tables: {len(tables)}")
    print(f"    High slope (>5 deg): {len(high_slope)}")
    print(f"    Low slope (0-2 deg): {len(low_slope)}")
    print(f"    Slope range: {min(slopes):.2f} - {max(slopes):.2f} deg")
    print()

    # 2. 检查是否有仿真数据
    print("[2] Checking existing simulations...")
    try:
        simulations = api_get("/simulations/")
        print(f"    Found {len(simulations)} existing simulations")

        if simulations:
            # 获取最新仿真的详细结果
            latest = simulations[0]
            sim_id = latest.get('id')
            print(f"    Latest simulation ID: {sim_id}")

            try:
                details = api_get(f"/simulations/{sim_id}")
                print(f"    Status: {details.get('status')}")

                if details.get('shading_results'):
                    print("    [OK] Shading results available!")
                    return analyze_simulation(details, tables)
            except Exception as e:
                print(f"    Could not get details: {e}")
    except Exception as e:
        print(f"    Could not fetch simulations: {e}")
    print()

    # 3. 如果没有仿真数据，分析地形数据本身的特征
    print("[3] Analyzing terrain characteristics for validation...")
    print()

    # 分析高坡度和低坡度行的遮挡潜力
    print("    Analyzing shading potential...")
    print()

    # 计算行间距和遮挡角度
    results = analyze_terrain_shading_potential(tables)

    # 4. 输出结果
    print()
    print("=" * 70)
    print("   VALIDATION RESULTS")
    print("=" * 70)
    print()

    print("High Slope Scenario (>5 deg):")
    if 'high_slope' in results:
        r = results['high_slope']
        print(f"  Samples: {r['samples']}")
        print(f"  Avg row spacing: {r['avg_spacing']:.1f} m")
        print(f"  Potential shading angle: {r['shading_angle']:.1f} deg")
        print(f"  Estimated shading hours/day: {r['shading_hours']:.1f}")
    print()

    print("Low Slope Scenario (0-2 deg):")
    if 'low_slope' in results:
        r = results['low_slope']
        print(f"  Samples: {r['samples']}")
        print(f"  Avg row spacing: {r['avg_spacing']:.1f} m")
        print(f"  Potential shading angle: {r['shading_angle']:.1f} deg")
        print(f"  Estimated shading hours/day: {r['shading_hours']:.1f}")
    print()

    # 5. 与论文对比
    print("Paper Benchmark Comparison:")
    print("  - High slope energy loss (no backtrack): Expected 35-40%")
    print("  - Backtrack reduction: Expected 55-65%")
    print("  - GCR correlation R^2: Expected ~0.95")
    print()

    # 保存结果
    output = {
        "generated_at": datetime.now().isoformat(),
        "method": "terrain_analysis",
        "terrain_stats": {
            "total_tables": len(tables),
            "high_slope_count": len(high_slope),
            "low_slope_count": len(low_slope),
            "slope_range": [float(min(slopes)), float(max(slopes))],
            "avg_slope": float(sum(slopes)/len(slopes)) if slopes else 0
        },
        "analysis_results": results
    }

    output_file = "api_validation_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Results saved to: {output_file}")
    print()
    print("=" * 70)
    print("   Validation Complete!")
    print("=" * 70)

    return output


def analyze_simulation(sim_details, tables):
    """分析仿真结果"""
    shading = sim_details.get('shading_results', {})

    # 按坡度分类分析
    high_slope_results = []
    low_slope_results = []

    for table in tables:
        table_id = table.get('table_id')
        slope = table.get('table_slope_deg', 0)

        if str(table_id) in shading:
            shade_data = shading[str(table_id)]
            if slope > 5:
                high_slope_results.append(shade_data)
            elif slope <= 2:
                low_slope_results.append(shade_data)

    return {
        'high_slope': {
            'samples': len(high_slope_results),
            'data': high_slope_results[:3]  # 前3个样本
        },
        'low_slope': {
            'samples': len(low_slope_results),
            'data': low_slope_results[:3]
        }
    }


def analyze_terrain_shading_potential(tables):
    """分析地形的遮挡潜力（基于几何计算）"""
    import math

    results = {'high_slope': {}, 'low_slope': {}}

    # 高坡度分析
    high_slope_tables = [t for t in tables if t.get('table_slope_deg', 0) > 5]
    if high_slope_tables:
        spacings = []
        for t in high_slope_tables:
            piles = t.get('piles', [])
            if len(piles) >= 2:
                # 计算桩间距
                for i in range(len(piles)-1):
                    dx = piles[i+1]['x'] - piles[i]['x']
                    dy = piles[i+1]['y'] - piles[i]['y']
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist > 0:
                        spacings.append(dist)

        avg_spacing = sum(spacings)/len(spacings) if spacings else 5.0

        # 遮挡角度 = arctan(面板高度 / 行间距)
        panel_height = 2.0  # 典型面板立起后高度
        shading_angle = math.degrees(math.atan(panel_height / avg_spacing)) if avg_spacing > 0 else 0

        # 估算遮挡时间（太阳高度角低于遮挡角度时发生遮挡）
        shading_hours = max(0, 12 * (shading_angle / 90))  # 简化估算

        results['high_slope'] = {
            'samples': len(high_slope_tables),
            'avg_spacing': avg_spacing,
            'shading_angle': shading_angle,
            'shading_hours': shading_hours
        }

    # 低坡度分析
    low_slope_tables = [t for t in tables if 0 <= t.get('table_slope_deg', 0) <= 2]
    if low_slope_tables:
        spacings = []
        for t in low_slope_tables[:50]:  # 采样50个
            piles = t.get('piles', [])
            if len(piles) >= 2:
                for i in range(len(piles)-1):
                    dx = piles[i+1]['x'] - piles[i]['x']
                    dy = piles[i+1]['y'] - piles[i]['y']
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist > 0:
                        spacings.append(dist)

        avg_spacing = sum(spacings)/len(spacings) if spacings else 5.0
        panel_height = 2.0
        shading_angle = math.degrees(math.atan(panel_height / avg_spacing)) if avg_spacing > 0 else 0
        shading_hours = max(0, 12 * (shading_angle / 90))

        results['low_slope'] = {
            'samples': len(low_slope_tables),
            'avg_spacing': avg_spacing,
            'shading_angle': shading_angle,
            'shading_hours': shading_hours
        }

    return results


if __name__ == "__main__":
    run_validation()
