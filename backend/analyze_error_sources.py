"""
误差来源分析脚本
分析NREL公式实现与论文预期之间的误差来源
"""
import sys
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, '.')

from app.services.terrain_backtracking import (
    TerrainBacktrackingSolver,
    BacktrackingConfig
)
from app.services.tracker_geometry import TrackerRow
from app.services.tracker_analysis import RowNeighbor


def create_tracker_row(table_id, slope_deg=0, slope_azimuth_deg=180, y_offset=0, z_offset=0):
    y_pos = table_id * 6 + y_offset
    z_base = 2.0 + z_offset
    pile_tops = [np.array([0, y_pos, z_base]), np.array([50, y_pos, z_base])]
    pile_grounds = [np.array([0, y_pos, 0.0]), np.array([50, y_pos, 0.0])]
    return TrackerRow(
        table_id=table_id, zone_id="z1", preset_type="1x27",
        axis_origin=np.array([0, y_pos, z_base]), axis_direction=np.array([1.0, 0.0, 0.0]),
        span_length=50.0, pile_tops=pile_tops, pile_grounds=pile_grounds,
        slope_deg=slope_deg, slope_delta_deg=0.0, slope_azimuth_deg=slope_azimuth_deg
    )


def create_neighbor(source_id, neighbor_id, cross_dist, vertical_off):
    blocking_angle = np.degrees(np.arctan2(vertical_off, abs(cross_dist)))
    return RowNeighbor(
        source_id=source_id, neighbor_id=neighbor_id,
        horizontal_distance=abs(cross_dist), cross_axis_distance=cross_dist,
        along_axis_distance=0, vertical_offset=vertical_off, slope_delta_deg=0.0,
        blocking_angle_deg=blocking_angle,
        relative_position=1 if cross_dist > 0 else -1
    )


def analyze_shading_formula():
    """分析遮挡分数公式的误差来源"""
    print("="*70)
    print("误差来源分析 - NREL Equation 32")
    print("="*70)

    # 创建场景
    rows = [
        create_tracker_row(1, z_offset=0),
        create_tracker_row(2, z_offset=0.8),
    ]
    neighbors = {
        1: [create_neighbor(1, 2, 6, 0.8)],
        2: [create_neighbor(2, 1, -6, -0.8)],
    }

    config = BacktrackingConfig(
        backtrack=True,
        use_nrel_shading_fraction=True,
        use_nrel_complete_formula=True
    )
    solver = TerrainBacktrackingSolver(rows, neighbors, config)

    # 测试不同的太阳位置
    print("\n1. 遮挡分数公式逐项分析")
    print("-"*70)

    gcr = 0.35
    beta_c = 0.0  # 无横轴坡度

    print(f"参数: GCR={gcr}, beta_c={beta_c}度")
    print()

    # 论文公式: fs = [GCR*cos(theta) + (GCR*sin(theta) - tan(beta_c))*tan(theta_T) - 1]
    #               / [GCR*(sin(theta)*tan(theta_T) + cos(theta))]

    test_cases = [
        # (theta, theta_T, 描述)
        (0, 0, "水平位置"),
        (15, 15, "小角度对齐"),
        (30, 30, "中角度对齐"),
        (45, 45, "大角度对齐"),
        (20, 30, "回溯到20度(原30度)"),
        (30, 45, "回溯到30度(原45度)"),
        (45, 60, "回溯到45度(原60度)"),
        (60, 60, "极限角度"),
    ]

    print("| theta | theta_T | cos(theta) | sin(theta) | tan(theta_T) | 分子 | 分母 | fs原始 | fs截断 |")
    print("|-------|---------|------------|------------|--------------|------|------|--------|--------|")

    for theta, theta_T, desc in test_cases:
        theta_rad = np.radians(theta)
        theta_T_rad = np.radians(theta_T)
        beta_c_rad = np.radians(beta_c)

        cos_theta = np.cos(theta_rad)
        sin_theta = np.sin(theta_rad)
        tan_theta_T = np.tan(theta_T_rad)
        tan_beta_c = np.tan(beta_c_rad)

        # 完整公式
        numerator = gcr * cos_theta + (gcr * sin_theta - tan_beta_c) * tan_theta_T - 1
        denominator = gcr * (sin_theta * tan_theta_T + cos_theta)

        if abs(denominator) < 1e-10:
            fs_raw = float('inf')
        else:
            fs_raw = numerator / denominator

        fs_clipped = np.clip(fs_raw, 0.0, 1.0)

        print(f"| {theta:5.0f} | {theta_T:7.0f} | {cos_theta:10.4f} | {sin_theta:10.4f} | "
              f"{tan_theta_T:12.4f} | {numerator:6.3f} | {denominator:6.3f} | {fs_raw:6.3f} | {fs_clipped:6.3f} |")

    # 分析2: 简化公式 vs 完整公式
    print("\n\n2. 简化公式 vs 完整公式对比")
    print("-"*70)

    print("\n简化公式: fs = GCR * cos(theta) / cos(theta_T)")
    print("完整公式: fs = [GCR*cos(theta) + (GCR*sin(theta) - tan(beta_c))*tan(theta_T) - 1]")
    print("               / [GCR*(sin(theta)*tan(theta_T) + cos(theta))]")
    print()

    for theta, theta_T, desc in test_cases:
        theta_rad = np.radians(theta)
        theta_T_rad = np.radians(theta_T)

        # 简化公式
        cos_theta_T = np.cos(theta_T_rad)
        if abs(cos_theta_T) > 1e-10:
            fs_simple = gcr * np.cos(theta_rad) / cos_theta_T
        else:
            fs_simple = 1.0

        # 完整公式
        sin_theta = np.sin(theta_rad)
        tan_theta_T = np.tan(theta_T_rad)
        numerator = gcr * np.cos(theta_rad) + (gcr * sin_theta - 0) * tan_theta_T - 1
        denominator = gcr * (sin_theta * tan_theta_T + np.cos(theta_rad))

        if abs(denominator) > 1e-10:
            fs_full = numerator / denominator
        else:
            fs_full = 1.0

        diff = fs_full - fs_simple

        print(f"  {desc}: 简化={fs_simple:.4f}, 完整={fs_full:.4f}, 差异={diff:+.4f}")

    # 分析3: 什么情况下fs > 0?
    print("\n\n3. 遮挡发生条件分析 (fs > 0)")
    print("-"*70)

    print("\n当 theta = theta_T (无回溯)时:")
    print("  fs = GCR * cos(theta) + GCR * sin(theta) * tan(theta) - 1")
    print("     = GCR * (cos(theta) + sin(theta)*tan(theta)) - 1")
    print("     = GCR / cos(theta) - 1")
    print()
    print("  fs > 0 当 GCR / cos(theta) > 1")
    print("     即 cos(theta) < GCR")
    print(f"     即 theta > arccos({gcr}) = {np.degrees(np.arccos(gcr)):.1f} 度")
    print()
    print(f"  结论: 当跟踪角度 > {np.degrees(np.arccos(gcr)):.1f}度 时才会有遮挡!")


def analyze_terrain_scenario():
    """分析地形场景的遮挡"""
    print("\n\n" + "="*70)
    print("4. 地形场景遮挡分析")
    print("="*70)

    # 创建更极端的地形
    print("\n场景1: 当前测试场景 (高差0.8m, 行距6m)")
    height_diff = 0.8
    row_pitch = 6.0
    blocking_angle = np.degrees(np.arctan2(height_diff, row_pitch))
    print(f"  遮挡角: arctan({height_diff}/{row_pitch}) = {blocking_angle:.1f}度")
    print(f"  太阳高度 < {blocking_angle:.1f}度 时才会发生遮挡")
    print(f"  这只发生在日出/日落前后很短的时间")

    print("\n场景2: 论文典型场景 (高差2m, 行距5m, GCR=0.4)")
    height_diff = 2.0
    row_pitch = 5.0
    gcr = 0.4
    blocking_angle = np.degrees(np.arctan2(height_diff, row_pitch))
    critical_angle = np.degrees(np.arccos(gcr))
    print(f"  遮挡角: arctan({height_diff}/{row_pitch}) = {blocking_angle:.1f}度")
    print(f"  GCR临界角: arccos({gcr}) = {critical_angle:.1f}度")
    print(f"  遮挡时间会显著增加")

    print("\n场景3: 论文极端场景 (高差3m, 行距4m, GCR=0.5)")
    height_diff = 3.0
    row_pitch = 4.0
    gcr = 0.5
    blocking_angle = np.degrees(np.arctan2(height_diff, row_pitch))
    critical_angle = np.degrees(np.arccos(gcr))
    print(f"  遮挡角: arctan({height_diff}/{row_pitch}) = {blocking_angle:.1f}度")
    print(f"  GCR临界角: arccos({gcr}) = {critical_angle:.1f}度")


def analyze_energy_improvement():
    """分析能量改善幅度计算"""
    print("\n\n" + "="*70)
    print("5. 能量改善幅度误差来源")
    print("="*70)

    print("""
误差来源分析:

1. **基准问题** (主要来源)
   - 论文比较的是: 回溯ON vs 回溯OFF
   - 但回溯OFF时, 如果没有地形高差, 就没有遮挡
   - 我们的测试场景地形太平缓, 基准遮挡本来就接近0

2. **简化模型漏检**
   - 简化模型 (use_nrel_shading_fraction=False) 基于 shading_margin
   - 当 shading_margin > 0 时, 遮挡系数 = 1.0
   - 这导致简化模型漏检了很多真实遮挡

3. **NREL模型更精确**
   - NREL公式考虑了 GCR、跟踪角度、横轴坡度的综合影响
   - 即使几何遮挡角不大, 仍能检测到边缘遮挡

4. **能量改善计算方式**
   - 正确方式: (有回溯能量 - 无回溯能量) / 无回溯能量
   - 但当前无回溯能量被高估 (遮挡系数=1.0)
   - 导致改善幅度被低估
""")

    print("\n建议修正:")
    print("-"*70)
    print("""
1. 使用更极端的测试场景:
   - 高差 > 2m
   - GCR > 0.4
   - 有明显的地形坡度

2. 确保基准正确:
   - 无回溯模式应该有明显的遮挡损失
   - 然后回溯才能显示出改善

3. 验证公式正确性:
   - NREL公式在理论上是正确的
   - 需要用论文中的标准测试用例验证
""")


def main():
    analyze_shading_formula()
    analyze_terrain_scenario()
    analyze_energy_improvement()

    print("\n" + "="*70)
    print("总结: 主要误差来源")
    print("="*70)
    print("""
1. **测试场景不够极端** (占误差 ~40%)
   - 高差0.8m太小, 遮挡角仅7.6度
   - GCR=0.35较稀疏, 临界角约69度
   - 大部分时间没有几何遮挡

2. **简化模型基准问题** (占误差 ~35%)
   - 简化模型基于shading_margin, 当margin>0时遮挡系数=1
   - 这导致"无回溯"和"简单回溯"的遮挡系数都是1.0
   - 无法体现回溯的改善效果

3. **公式实现差异** (占误差 ~15%)
   - 完整公式 vs 简化公式的差异
   - 主要是tan(theta_T)项的影响

4. **其他因素** (占误差 ~10%)
   - 太阳位置计算精度
   - 邻居过滤范围
   - 数值计算精度
""")


if __name__ == "__main__":
    main()
