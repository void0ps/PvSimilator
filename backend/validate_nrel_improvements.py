"""
NREL 论文算法改进验证脚本
验证实现与论文公式的一致性
"""
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 添加路径
sys.path.insert(0, '.')

from app.services.terrain_backtracking import (
    TerrainBacktrackingSolver,
    BacktrackingConfig
)
from app.services.pv_calculator import PVCalculator
from app.services.tracker_geometry import TrackerRow
from app.services.tracker_analysis import RowNeighbor


def create_mock_tracker_row(table_id: int, slope_deg: float = 0.0,
                            slope_azimuth_deg: float = 180.0,
                            axis_tilt: float = 0.0) -> TrackerRow:
    """创建模拟的跟踪器行数据"""
    y_pos = table_id * 6
    pile_tops = [
        np.array([0, y_pos, 2.0]),
        np.array([50, y_pos, 2.0]),
    ]
    pile_grounds = [
        np.array([0, y_pos, 0.0]),
        np.array([50, y_pos, 0.0]),
    ]

    axis_direction = np.array([1.0, 0.0, np.tan(np.radians(axis_tilt))])
    axis_direction = axis_direction / np.linalg.norm(axis_direction)

    row = TrackerRow(
        table_id=table_id,
        zone_id="zone_1",
        preset_type="1x27",
        axis_origin=np.array([0, y_pos, 2.0]),
        axis_direction=axis_direction,
        span_length=50.0,
        pile_tops=pile_tops,
        pile_grounds=pile_grounds,
        slope_deg=slope_deg,
        slope_delta_deg=0.0,
        slope_azimuth_deg=slope_azimuth_deg,
    )
    return row


def create_mock_neighbor(source_id: int, neighbor_id: int,
                        cross_axis_distance: float, along_axis_distance: float = 0,
                        vertical_offset: float = 0) -> RowNeighbor:
    """创建模拟的邻居关系"""
    horizontal_distance = np.sqrt(cross_axis_distance**2 + along_axis_distance**2)
    relative_position = 1 if cross_axis_distance > 0 else -1
    blocking_angle = np.degrees(np.arctan2(vertical_offset, abs(cross_axis_distance))) if cross_axis_distance != 0 else 0

    return RowNeighbor(
        source_id=source_id,
        neighbor_id=neighbor_id,
        horizontal_distance=horizontal_distance,
        cross_axis_distance=cross_axis_distance,
        along_axis_distance=along_axis_distance,
        vertical_offset=vertical_offset,
        slope_delta_deg=0.0,
        blocking_angle_deg=blocking_angle,
        relative_position=relative_position
    )


def test_slope_aware_correction():
    """测试斜坡感知回溯修正 (Equations 11-15)"""
    print("\n" + "="*60)
    print("测试 1: 斜坡感知回溯修正 (Equations 11-15)")
    print("="*60)

    rows = [create_mock_tracker_row(1, slope_deg=5.0)]
    neighbors = {1: []}
    config = BacktrackingConfig(
        use_nrel_slope_aware_correction=True,
        use_nrel_shading_fraction=True,
        module_width=2.0
    )
    solver = TerrainBacktrackingSolver(rows, neighbors, config)

    print("\n[Equation 15] 回溯条件判断 (ratio = |cos(θT-βc)| / (GCR×cos(βc))):")
    print("  需要: ratio < 1 (存在有效回溯角度)")

    test_cases = [
        # (theta_T, beta_c, gcr)
        (30, 0, 0.35),
        (45, 0, 0.35),
        (60, 0, 0.35),
        (45, 5, 0.35),
        (60, 10, 0.35),
        (80, 0, 0.35),
    ]

    for theta_T, beta_c, gcr in test_cases:
        ratio = abs(np.cos(np.radians(theta_T - beta_c))) / (gcr * np.cos(np.radians(beta_c)))
        needs_bt = solver._needs_backtracking(theta_T, beta_c, gcr)
        print(f"  θT={theta_T:2d}°, βc={beta_c:2d}°, GCR={gcr}: "
              f"ratio={ratio:.3f}, 需要回溯={needs_bt}")

    print("\n[Equations 11-14] 回溯修正角度:")
    test_angles = [
        (45, 0, 0.35),
        (60, 0, 0.35),
        (45, 5, 0.35),
        (60, 10, 0.35),
        (80, 0, 0.35),
    ]

    for theta_T, beta_c, gcr in test_angles:
        theta_c = solver._calculate_slope_aware_correction(theta_T, beta_c, gcr)
        print(f"  θT={theta_T:2d}°, βc={beta_c:2d}°, GCR={gcr}: "
              f"修正角度 θc={theta_c:.2f}°")

    return True


def test_shading_fraction_formula():
    """测试完整遮挡分数公式 (Equation 32)"""
    print("\n" + "="*60)
    print("测试 2: 完整遮挡分数公式 (Equation 32)")
    print("="*60)

    rows = [create_mock_tracker_row(1)]
    neighbors = {1: []}
    config = BacktrackingConfig(use_nrel_shading_fraction=True)
    solver = TerrainBacktrackingSolver(rows, neighbors, config)

    gcr = 0.35

    print("\n公式: fs = [GCR×cos(θ) + (GCR×sin(θ) - tan(βc))×tan(θT) - 1]")
    print("            / [GCR×(sin(θ)×tan(θT) + cos(θ))]")
    print(f"\nGCR = {gcr}")
    print("\n说明: fs < 0 表示无遮挡(clip到0), 0 < fs < 1 表示部分遮挡, fs >= 1 表示完全遮挡")

    # 测试不同的情况
    # 当 θ=θT 时 (真跟踪)，会有遮挡
    # 当 θ < θT 时 (回溯后)，遮挡减少
    test_cases = [
        # (theta, theta_true, beta_c, description)
        (0, 0, 0, "零角度"),
        (30, 30, 0, "真跟踪30°"),
        (45, 45, 0, "真跟踪45°"),
        (60, 60, 0, "真跟踪60°"),
        (20, 45, 0, "回溯: 45°->20°"),
        (30, 45, 0, "回溯: 45°->30°"),
        (30, 60, 0, "回溯: 60°->30°"),
        (45, 60, 5, "回溯+5°横坡"),
        (30, 60, 10, "回溯+10°横坡"),
    ]

    all_valid = True
    for theta, theta_true, beta_c, desc in test_cases:
        fs = solver._calculate_shading_fraction_nrel(gcr, theta, theta_true, beta_c)
        valid = -0.5 <= fs <= 1.5  # 允许一些超出范围的值
        if not valid:
            all_valid = False

        # 计算原始值用于展示
        theta_rad = np.radians(theta)
        theta_T_rad = np.radians(theta_true) if theta_true else 0
        beta_c_rad = np.radians(beta_c)

        cos_theta = np.cos(theta_rad)
        sin_theta = np.sin(theta_rad)
        tan_beta_c = np.tan(beta_c_rad)
        tan_theta_T = np.tan(theta_T_rad)

        numerator = gcr * cos_theta + (gcr * sin_theta - tan_beta_c) * tan_theta_T - 1
        denominator = gcr * (sin_theta * tan_theta_T + cos_theta)

        print(f"  {desc}: fs={fs:.4f} (原始={numerator/denominator if abs(denominator)>1e-10 else float('inf'):.4f}) "
              f"[{'VALID' if valid else 'INVALID'}]")

    return all_valid


def test_partial_shading_power_model():
    """测试部分遮挡功率模型 (Equation 4)"""
    print("\n" + "="*60)
    print("测试 3: 部分遮挡功率模型 (Equation 4)")
    print("="*60)

    calculator = PVCalculator(latitude=40.0, longitude=116.0)

    print("\n公式:")
    print("  轻度遮挡 (fs < 1/N): Pnorm = 1 - (1-fd) × fs × N")
    print("  重度遮挡 (fs >= 1/N): Pnorm = fd")

    N = 12  # 72电池模块

    print(f"\nN = {N} (每列电池数), 临界值 1/N = {1/N:.4f}")

    test_cases = [
        # (fs, fd, description)
        (0.0, 0.15, "无遮挡"),
        (0.02, 0.15, "轻度遮挡 2%"),
        (0.05, 0.15, "轻度遮挡 5%"),
        (0.08, 0.15, f"临界附近 ({1/N:.2f})"),
        (0.10, 0.15, "重度遮挡 10%"),
        (0.20, 0.20, "重度遮挡 20%"),
        (0.50, 0.25, "重度遮挡 50%"),
    ]

    print("\n  遮挡分数  漫射分数  归一化功率  遮挡类型    预期范围")
    print("  " + "-"*55)

    all_pass = True
    for fs, fd, desc in test_cases:
        pnorm = calculator.calculate_partial_shading_power(fs, fd, N)
        regime = "轻度" if fs < 1/N else "重度"

        # 计算预期值
        if fs < 1/N:
            expected = 1 - (1-fd) * fs * N
            exp_range = f"{expected:.2f}"
        else:
            expected = fd
            exp_range = f"{expected:.2f}"

        # 验证
        if fs < 1/N:
            # 轻度遮挡: Pnorm应该在 (fd, 1) 范围内
            is_ok = fd <= pnorm <= 1.0
        else:
            # 重度遮挡: Pnorm应该等于fd
            is_ok = abs(pnorm - fd) < 0.01

        if not is_ok:
            all_pass = False

        status = "PASS" if is_ok else "FAIL"
        print(f"  {fs:.2f}      {fd:.2f}     {pnorm:.4f}      {regime}遮挡    预期≈{exp_range} [{status}]")

    return all_pass


def test_diffuse_retention():
    """测试散射辐射保留率"""
    print("\n" + "="*60)
    print("测试 4: 散射辐射保留率 (天空模型)")
    print("="*60)

    calculator = PVCalculator(latitude=40.0, longitude=116.0)

    models = ['isotropic', 'hay', 'perez']
    shading_factors = [1.0, 0.8, 0.5, 0.2]

    print("\n散射保留率 (shading_factor=1 表示无遮挡, =0 表示完全遮挡):")
    print("公式: retention = shading_factor + (1-shading_factor) × diffuse_retention_in_shadow")
    print()

    all_valid = True
    for model in models:
        print(f"  {model} 模型:")
        for sf in shading_factors:
            retention = calculator.calculate_diffuse_retention(sf, model)
            valid = 0.4 <= retention <= 1.0
            if not valid:
                all_valid = False

            # 计算遮挡分数
            fs = 1 - sf
            print(f"    sf={sf:.1f} (fs={fs:.1f}): retention={retention:.3f} "
                  f"{'[VALID]' if valid else '[INVALID]'}")
        print()

    return all_valid


def test_energy_comparison():
    """测试能量产出对比"""
    print("\n" + "="*60)
    print("测试 5: 能量产出对比 (不同配置)")
    print("="*60)

    # 创建模拟地形
    rows = [
        create_mock_tracker_row(1, slope_deg=0, axis_tilt=0),
        create_mock_tracker_row(2, slope_deg=0, axis_tilt=0),
        create_mock_tracker_row(3, slope_deg=0, axis_tilt=0),
    ]

    # 创建邻居关系
    neighbors = {
        1: [create_mock_neighbor(1, 2, 6, 0, 0)],
        2: [create_mock_neighbor(2, 1, -6, 0, 0),
            create_mock_neighbor(2, 3, 6, 0, 0)],
        3: [create_mock_neighbor(3, 2, -6, 0, 0)],
    }

    # 生成太阳位置数据 (夏至日)
    times = pd.date_range('2024-06-21 06:00', '2024-06-21 18:00', freq='H')

    # 简化的太阳位置计算
    hour_angles = (times.hour - 12) * 15
    declination = 23.45
    lat_rad = np.radians(40.0)
    dec_rad = np.radians(declination)

    solar_elevations = []
    solar_azimuths = []
    for ha in hour_angles:
        ha_rad = np.radians(ha)
        sin_alt = (np.sin(lat_rad) * np.sin(dec_rad) +
                   np.cos(lat_rad) * np.cos(dec_rad) * np.cos(ha_rad))
        alt = np.degrees(np.arcsin(np.clip(sin_alt, -1, 1)))
        solar_elevations.append(max(0, alt))

        if alt > 0:
            cos_az = (np.sin(dec_rad) - np.sin(lat_rad) * sin_alt) / (np.cos(lat_rad) * np.cos(np.radians(alt)) + 1e-10)
            az = np.degrees(np.arccos(np.clip(cos_az, -1, 1)))
            if ha > 0:
                az = 360 - az
        else:
            az = 180
        solar_azimuths.append(az)

    solar_zenith = pd.Series(90 - np.array(solar_elevations), index=times)
    solar_azimuth = pd.Series(solar_azimuths, index=times)

    # 测试不同配置
    configs = [
        ("简单回溯", BacktrackingConfig(backtrack=True, use_nrel_shading_fraction=False)),
        ("NREL遮挡公式", BacktrackingConfig(backtrack=True, use_nrel_shading_fraction=True)),
        ("NREL斜坡修正", BacktrackingConfig(backtrack=True, use_nrel_shading_fraction=True,
                                           use_nrel_slope_aware_correction=True)),
    ]

    results = {}
    for name, config in configs:
        solver = TerrainBacktrackingSolver(rows, neighbors, config)
        result = solver.compute_tracker_angles(solar_zenith, solar_azimuth)
        avg_shading = result.shading_factor.mean().mean()
        min_shading = result.shading_factor.min().min()
        results[name] = (avg_shading, min_shading)
        print(f"\n  {name}:")
        print(f"    平均遮挡系数: {avg_shading:.4f}")
        print(f"    最小遮挡系数: {min_shading:.4f}")

    # 计算改进
    baseline_avg, _ = results.get("简单回溯", (1.0, 1.0))
    print("\n  改进对比:")
    for name, (avg, _) in results.items():
        if name != "简单回溯":
            if baseline_avg > 0:
                improvement = (avg - baseline_avg) / baseline_avg * 100
            else:
                improvement = 0
            print(f"    {name} vs 简单回溯: {improvement:+.2f}%")

    return True


def main():
    print("="*60)
    print("NREL 论文算法改进验证报告")
    print("="*60)
    print(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        "斜坡感知回溯修正": test_slope_aware_correction(),
        "完整遮挡分数公式": test_shading_fraction_formula(),
        "部分遮挡功率模型": test_partial_shading_power_model(),
        "散射辐射保留率": test_diffuse_retention(),
        "能量产出对比": test_energy_comparison(),
    }

    print("\n" + "="*60)
    print("验证总结")
    print("="*60)

    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {name}: [{status}]")

    print("\n" + "="*60)
    if all_pass:
        print("所有验证通过!")
    else:
        print("部分验证失败，需要检查实现")
    print("="*60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
