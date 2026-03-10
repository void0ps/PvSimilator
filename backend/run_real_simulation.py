#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
真实仿真验证 - 通过API创建并运行完整仿真
"""
import urllib.request
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001/api/v1"

def api_request(method, endpoint, data=None):
    """通用API请求"""
    url = f"{BASE_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}

    if data:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        print(f"HTTP Error {e.code}: {error_body}")
        raise

def get_terrain_data():
    """获取地形数据用于创建PV系统"""
    return api_request('GET', '/terrain/layout')

def create_pv_system(terrain_data):
    """创建PV系统"""
    # 从地形数据获取坐标信息
    tables = terrain_data.get('tables', [])
    if not tables:
        raise ValueError("No terrain data available")

    # 获取中心坐标
    all_piles = []
    for table in tables:
        all_piles.extend(table.get('piles', []))

    if all_piles:
        lat = all_piles[0].get('lat', -37.6)
        long = all_piles[0].get('long', 175.5)
    else:
        lat, long = -37.6, 175.5

    # 计算系统容量（基于桩位数量）
    total_piles = len(all_piles)
    module_count = total_piles  # 每个桩位一个模块
    capacity_kw = module_count * 0.55 / 1000  # 假设550W模块

    system_data = {
        "name": f"Validation System {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "System for algorithm validation with terrain-aware backtracking",
        "capacity_kw": round(capacity_kw, 2),
        "tilt_angle": 0.0,  # 单轴跟踪器，初始倾角为0
        "azimuth": 180.0,   # 朝南（南半球）
        "latitude": lat,
        "longitude": long,
        "altitude": 100.0,
        "module_count": module_count,
        "string_count": module_count // 14,  # 假设14个模块一组串
        "pitch": 6.5  # 行间距
    }

    print(f"Creating PV system with {module_count} modules...")
    return api_request('POST', '/systems/', system_data)

def create_simulation(system_id, with_shading=True):
    """创建仿真任务"""
    # 使用夏至日（最大遮挡风险）
    start_date = datetime(2024, 6, 21, 6, 0, 0)
    end_date = datetime(2024, 6, 21, 18, 0, 0)

    sim_data = {
        "name": f"Validation Simulation {'With' if with_shading else 'Without'} Shading",
        "description": "Algorithm validation simulation",
        "system_id": system_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "time_resolution": "hourly",
        "weather_source": "nasa_sse",
        "include_shading": with_shading,
        "include_soiling": False,
        "include_degradation": False,
        "shading_factor": 0.0,
        "soiling_loss": 0.0,
        "degradation_rate": 0.0,
        "electricity_price": 0.5,
        "inflation_rate": 0.03,
        "discount_rate": 0.08
    }

    print(f"Creating simulation (shading={with_shading})...")
    return api_request('POST', '/simulations/', sim_data)

def wait_for_simulation(sim_id, timeout=300):
    """等待仿真完成"""
    start_time = time.time()
    last_progress = -1

    while time.time() - start_time < timeout:
        result = api_request('GET', f'/simulations/{sim_id}')
        status = result.get('status', 'unknown')
        progress = result.get('progress', 0)

        if progress != last_progress:
            print(f"  Progress: {progress:.1f}% - Status: {status}")
            last_progress = progress

        if status == 'completed':
            return result
        elif status == 'failed':
            raise Exception(f"Simulation failed: {result}")

        time.sleep(2)

    raise TimeoutError(f"Simulation timed out after {timeout}s")

def get_simulation_results(sim_id):
    """获取仿真结果"""
    response = api_request('GET', f'/simulations/{sim_id}/results')
    # 结果可能在 response['results'] 中
    if isinstance(response, dict) and 'results' in response:
        return response['results']
    return response

def get_shading_results(sim_id):
    """获取遮挡分析结果"""
    try:
        return api_request('GET', f'/simulations/{sim_id}/shading')
    except:
        return None

def analyze_results(results_no_shading, results_with_shading, terrain_data):
    """分析对比结果"""
    print()
    print("=" * 70)
    print("   SIMULATION RESULTS ANALYSIS")
    print("=" * 70)
    print()

    # 分析地形数据
    tables = terrain_data.get('tables', [])
    slopes = [t.get('table_slope_deg', 0) for t in tables if t.get('table_slope_deg') is not None]

    high_slope_tables = [t for t in tables if t.get('table_slope_deg', 0) > 5]
    low_slope_tables = [t for t in tables if 0 <= t.get('table_slope_deg', 0) <= 2]

    print("Terrain Statistics:")
    print(f"  Total rows: {len(tables)}")
    print(f"  High slope (>5 deg): {len(high_slope_tables)}")
    print(f"  Low slope (0-2 deg): {len(low_slope_tables)}")
    if slopes:
        print(f"  Slope range: {min(slopes):.2f} - {max(slopes):.2f} deg")
        print(f"  Average slope: {sum(slopes)/len(slopes):.2f} deg")
    print()

    # 分析能量结果
    def calc_total_energy(results):
        if not results:
            return 0, 0
        total_energy = 0
        count = 0
        for r in results:
            if isinstance(r, dict):
                energy = r.get('energy_daily') or r.get('power_dc', 0) or 0
                if energy:
                    total_energy += float(energy)
                    count += 1
        return total_energy, count

    energy_no, count_no = calc_total_energy(results_no_shading)
    energy_with, count_with = calc_total_energy(results_with_shading)

    print("Energy Analysis:")
    print(f"  No backtracking: {energy_no:.2f} kWh ({count_no} data points)")
    print(f"  With backtracking: {energy_with:.2f} kWh ({count_with} data points)")

    if energy_no > 0 and energy_with > 0:
        diff = energy_with - energy_no
        pct_diff = (diff / energy_no) * 100 if energy_no > 0 else 0
        print(f"  Energy difference: {diff:.2f} kWh ({pct_diff:+.1f}%)")
    print()

    # 显示详细结果
    if results_with_shading:
        print("Detailed Results (with backtracking):")
        for i, r in enumerate(results_with_shading[:5]):
            if isinstance(r, dict):
                ts = r.get('timestamp', 'N/A')
                power = r.get('power_dc', 0) or 0
                energy = r.get('energy_daily', 0) or 0
                irr = r.get('irradiance_global', 0) or 0
                print(f"  {ts}: Power={power:.1f}W, Energy={energy:.3f}kWh, Irr={irr:.1f}W/m2")
    print()

    # 与论文对比
    print("Paper Benchmark Comparison:")
    print("  Expected energy loss (high slope, no backtrack): 35-40%")
    print("  Expected improvement from backtracking: 55-65%")
    print()

    return {
        "terrain_stats": {
            "total_rows": len(tables),
            "high_slope_count": len(high_slope_tables),
            "low_slope_count": len(low_slope_tables),
            "slope_range": [float(min(slopes)), float(max(slopes))] if slopes else [0, 0],
            "avg_slope": float(sum(slopes)/len(slopes)) if slopes else 0
        },
        "energy_analysis": {
            "total_energy_no_backtrack": energy_no,
            "total_energy_with_backtrack": energy_with,
            "data_points_no": count_no,
            "data_points_with": count_with
        }
    }

def run_validation():
    """运行完整验证流程"""
    print("=" * 70)
    print("   REAL SIMULATION VALIDATION")
    print("=" * 70)
    print()

    # 1. 获取地形数据
    print("[1] Loading terrain data...")
    terrain_data = get_terrain_data()
    print(f"    Loaded {len(terrain_data.get('tables', []))} rows")
    print()

    # 2. 创建PV系统
    print("[2] Creating PV system...")
    system = create_pv_system(terrain_data)
    system_id = system.get('id')
    print(f"    System ID: {system_id}")
    print(f"    Capacity: {system.get('capacity_kw')} kW")
    print()

    # 3. 创建无遮挡仿真（对照组）
    print("[3] Creating simulation WITHOUT backtracking...")
    sim_no_shading = create_simulation(system_id, with_shading=False)
    sim_id_no = sim_no_shading.get('id')
    print(f"    Simulation ID: {sim_id_no}")

    # 4. 创建有遮挡仿真（实验组）
    print("[4] Creating simulation WITH backtracking...")
    sim_with_shading = create_simulation(system_id, with_shading=True)
    sim_id_with = sim_with_shading.get('id')
    print(f"    Simulation ID: {sim_id_with}")
    print()

    # 5. 等待仿真完成
    print("[5] Waiting for simulations to complete...")
    print("  No backtracking simulation:")
    result_no = wait_for_simulation(sim_id_no)

    print("  With backtracking simulation:")
    result_with = wait_for_simulation(sim_id_with)
    print()

    # 6. 获取结果
    print("[6] Fetching results...")
    results_no = get_simulation_results(sim_id_no)
    results_with = get_simulation_results(sim_id_with)

    shading_data = get_shading_results(sim_id_with)
    print(f"    No backtracking: {len(results_no)} data points")
    print(f"    With backtracking: {len(results_with)} data points")
    if shading_data:
        print(f"    Shading data: Available")
    print()

    # 7. 分析结果
    print("[7] Analyzing results...")
    analysis = analyze_results(results_no, results_with, terrain_data)

    # 8. 保存结果
    output = {
        "generated_at": datetime.now().isoformat(),
        "method": "real_simulation",
        "system_id": system_id,
        "simulation_ids": {
            "no_backtrack": sim_id_no,
            "with_backtrack": sim_id_with
        },
        "analysis": analysis
    }

    output_file = "real_simulation_validation_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Results saved to: {output_file}")
    print()
    print("=" * 70)
    print("   VALIDATION COMPLETE!")
    print("=" * 70)

    return output

if __name__ == "__main__":
    run_validation()
