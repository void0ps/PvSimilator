"""
测试地形感知回溯算法的核心计算
- GCR计算
- 遮挡裕度
- 坡度补偿
- 沿轴距离衰减
- NREL论文公式
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from app.services.terrain_backtracking import (
    TerrainBacktrackingSolver,
    BacktrackingConfig
)
from app.services.tracker_geometry import TrackerRow
from app.services.tracker_analysis import RowNeighbor


def create_test_row(
    table_id: int = 1,
    axis_azimuth: float = 180.0,
    axis_tilt: float = 0.0,
    slope_deg: float = None,
    slope_azimuth_deg: float = None,
) -> TrackerRow:
    """创建用于测试的TrackerRow实例。

    Args:
        table_id: 行ID
        axis_azimuth: 轴方位角（度）
        axis_tilt: 轴倾斜角（度）
        slope_deg: 坡度（度）
        slope_azimuth_deg: 坡度方位角（度）

    Returns:
        TrackerRow实例
    """
    # 根据轴方位角和倾斜角计算轴方向向量
    azimuth_rad = np.radians(axis_azimuth)
    tilt_rad = np.radians(axis_tilt)

    # 计算水平方向
    horizontal_x = np.sin(azimuth_rad)
    horizontal_y = np.cos(azimuth_rad)

    # 计算轴方向（包含倾斜）
    axis_direction = np.array([
        horizontal_x * np.cos(tilt_rad),
        horizontal_y * np.cos(tilt_rad),
        np.sin(tilt_rad)
    ])

    # 创建简单的桩点
    pile_tops = [
        np.array([0.0, 0.0, 0.0]),
        np.array([10.0 * horizontal_x, 10.0 * horizontal_y, 10.0 * np.sin(tilt_rad)])
    ]
    pile_grounds = [
        np.array([0.0, 0.0, -1.0]),
        np.array([10.0 * horizontal_x, 10.0 * horizontal_y, -1.0 + 10.0 * np.sin(tilt_rad)])
    ]

    return TrackerRow(
        table_id=table_id,
        zone_id=None,
        preset_type=None,
        axis_origin=np.array([0.0, 0.0, 0.0]),
        axis_direction=axis_direction,
        span_length=10.0,
        pile_tops=pile_tops,
        pile_grounds=pile_grounds,
        slope_deg=slope_deg,
        slope_delta_deg=None,
        slope_azimuth_deg=slope_azimuth_deg,
    )


def create_test_neighbor(
    neighbor_id: int,
    cross_axis_distance: float,
    along_axis_distance: float,
    vertical_offset: float,
    relative_position: int,
    source_id: int = 1,
    slope_delta_deg: float = 0.0,
) -> RowNeighbor:
    """创建用于测试的RowNeighbor实例。

    Args:
        neighbor_id: 邻居ID
        cross_axis_distance: 横轴距离（米）
        along_axis_distance: 沿轴距离（米）
        vertical_offset: 垂直偏移（米）
        relative_position: 相对位置（1或-1）
        source_id: 源ID
        slope_delta_deg: 坡度差（度）

    Returns:
        RowNeighbor实例
    """
    horizontal_distance = np.sqrt(cross_axis_distance**2 + along_axis_distance**2)
    blocking_angle = np.degrees(np.arctan2(vertical_offset, abs(cross_axis_distance))) if abs(cross_axis_distance) > 0.01 else 0.0

    return RowNeighbor(
        source_id=source_id,
        neighbor_id=neighbor_id,
        horizontal_distance=horizontal_distance,
        cross_axis_distance=cross_axis_distance,
        along_axis_distance=along_axis_distance,
        vertical_offset=vertical_offset,
        slope_delta_deg=slope_delta_deg,
        blocking_angle_deg=blocking_angle,
        relative_position=relative_position,
    )


class TestBacktrackingConfig:
    """测试回溯配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = BacktrackingConfig()

        assert config.module_width == 2.0
        assert config.max_angle == 85.0
        assert config.backtrack is True
        assert config.shading_margin_limit == 10.0
        assert config.max_neighbor_cross_distance == 20.0
        assert config.max_neighbor_along_distance == 250.0
        assert config.cross_distance_epsilon == 0.5
        # 新增的NREL参数
        assert config.use_nrel_shading_fraction is False
        assert config.nrel_shading_limit_deg == 5.0

    def test_custom_config(self):
        """测试自定义配置"""
        config = BacktrackingConfig(
            module_width=1.0,
            max_angle=60.0,
            backtrack=False,
            use_nrel_shading_fraction=True,
            nrel_shading_limit_deg=3.0
        )

        assert config.module_width == 1.0
        assert config.max_angle == 60.0
        assert config.backtrack is False
        assert config.use_nrel_shading_fraction is True
        assert config.nrel_shading_limit_deg == 3.0


class TestCrossAxisTilt:
    """测试横轴坡度计算"""

    def test_zero_slope(self):
        """测试零坡度情况"""
        config = BacktrackingConfig()
        row = create_test_row(slope_deg=0.0)

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={},
            config=config
        )

        cross_axis_tilt = solver._calculate_cross_axis_tilt(row)
        assert cross_axis_tilt == 0.0

    def test_slope_with_same_azimuth(self):
        """测试坡度方位角与轴方位角相同的情况"""
        config = BacktrackingConfig()
        row = create_test_row(
            axis_azimuth=180.0,
            slope_deg=10.0,
            slope_azimuth_deg=180.0
        )

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={},
            config=config
        )

        cross_axis_tilt = solver._calculate_cross_axis_tilt(row)
        # 坡度方位角与轴方位角相同，相对方位角为0，sin(0)=0
        assert abs(cross_axis_tilt) < 0.1

    def test_slope_with_perpendicular_azimuth(self):
        """测试坡度方位角与轴方位角垂直的情况"""
        config = BacktrackingConfig()
        row = create_test_row(
            axis_azimuth=180.0,
            slope_deg=10.0,
            slope_azimuth_deg=270.0  # 垂直于轴方位角
        )

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={},
            config=config
        )

        cross_axis_tilt = solver._calculate_cross_axis_tilt(row)
        # 相对方位角为90度，sin(90)=1，横轴坡度应等于坡度
        assert abs(cross_axis_tilt - 10.0) < 0.5


class TestNRELShadingFraction:
    """测试NREL论文遮挡分数计算"""

    def test_zero_cross_axis_tilt(self):
        """测试零横轴坡度时的遮挡分数"""
        config = BacktrackingConfig()
        row = create_test_row(slope_deg=0.0)

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={},
            config=config
        )

        # 无横轴坡度时，遮挡分数应为0
        shading = solver._calculate_shading_fraction_nrel(
            gcr=0.35,
            theta=30.0,
            theta_true=None,
            beta_c=0.0
        )
        assert shading == 0.0

    def test_with_cross_axis_tilt(self):
        """测试有横轴坡度时的遮挡分数"""
        config = BacktrackingConfig()
        row = create_test_row(slope_deg=5.0, slope_azimuth_deg=270.0)

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={},
            config=config
        )

        # 有横轴坡度时，遮挡分数应大于0
        shading = solver._calculate_shading_fraction_nrel(
            gcr=0.35,
            theta=30.0,
            theta_true=None,
            beta_c=5.0
        )
        assert shading > 0.0
        assert shading <= 1.0

    def test_shading_fraction_bounds(self):
        """测试遮挡分数在有效范围内"""
        config = BacktrackingConfig()

        solver = TerrainBacktrackingSolver(
            rows=[create_test_row()],
            neighbors={},
            config=config
        )

        # 测试各种参数组合
        test_cases = [
            (0.35, 0.0, None, 0.0),
            (0.35, 45.0, None, 10.0),
            (0.5, 60.0, None, 15.0),
            (0.9, 85.0, None, 20.0),
        ]

        for gcr, theta, theta_true, beta_c in test_cases:
            shading = solver._calculate_shading_fraction_nrel(
                gcr=gcr,
                theta=theta,
                theta_true=theta_true,
                beta_c=beta_c
            )
            assert 0.0 <= shading <= 1.0, f"shading out of bounds: {shading}"


class TestGCRCalculation:
    """测试GCR（地面覆盖率）计算"""

    def test_gcr_calculation(self):
        """测试GCR计算公式"""
        config = BacktrackingConfig(module_width=2.0)

        row = create_test_row()

        # 模拟不同的行间距
        test_cases = [
            (3.0, 0.67),   # pitch=3m, GCR应约为0.67
            (4.0, 0.5),    # pitch=4m, GCR应为0.5
            (10.0, 0.2),   # pitch=10m, GCR应为0.2
        ]

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={},
            config=config
        )

        for pitch, expected_gcr in test_cases:
            gcr = np.clip(config.module_width / pitch, 0.05, 0.9)
            assert abs(gcr - expected_gcr) < 0.01, f"pitch={pitch}, expected GCR={expected_gcr}, got {gcr}"

    def test_gcr_clipping(self):
        """测试GCR限制在0.05-0.9范围内"""
        config = BacktrackingConfig(module_width=2.0)

        # 测试极端情况
        very_small_pitch = 1.0
        gcr_small = np.clip(config.module_width / very_small_pitch, 0.05, 0.9)
        assert gcr_small == 0.9  # 应该被限制在0.9

        very_large_pitch = 100.0
        gcr_large = np.clip(config.module_width / very_large_pitch, 0.05, 0.9)
        assert gcr_large == 0.05  # 应该被限制在0.05


class TestNeighborFiltering:
    """测试邻居过滤逻辑"""

    def test_filter_by_cross_distance(self):
        """测试横向距离过滤"""
        config = BacktrackingConfig(
            max_neighbor_cross_distance=20.0,
            max_neighbor_along_distance=250.0,
            cross_distance_epsilon=0.5
        )

        row = create_test_row()

        neighbors = [
            create_test_neighbor(
                neighbor_id=2,
                cross_axis_distance=5.0,  # 正常范围
                along_axis_distance=10.0,
                vertical_offset=1.0,
                relative_position=1
            ),
            create_test_neighbor(
                neighbor_id=3,
                cross_axis_distance=15.0,  # 正常范围
                along_axis_distance=10.0,
                vertical_offset=1.0,
                relative_position=1
            ),
            create_test_neighbor(
                neighbor_id=4,
                cross_axis_distance=25.0,  # 太远，应被过滤
                along_axis_distance=10.0,
                vertical_offset=1.0,
                relative_position=1
            ),
        ]

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={1: neighbors},
            config=config
        )

        filtered = solver._filter_neighbors(neighbors)

        # 前两个邻居应该保留（cross_distance在0.5-20范围内）
        assert len(filtered) == 2
        assert filtered[0].neighbor_id == 2
        assert filtered[1].neighbor_id == 3

    def test_filter_by_along_distance(self):
        """测试沿轴距离过滤"""
        config = BacktrackingConfig(
            max_neighbor_cross_distance=20.0,
            max_neighbor_along_distance=250.0
        )

        row = create_test_row()

        neighbors = [
            create_test_neighbor(
                neighbor_id=2,
                cross_axis_distance=5.0,
                along_axis_distance=100.0,  # 正常范围
                vertical_offset=1.0,
                relative_position=1
            ),
            create_test_neighbor(
                neighbor_id=3,
                cross_axis_distance=5.0,
                along_axis_distance=300.0,  # 超出范围
                vertical_offset=1.0,
                relative_position=1
            ),
        ]

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={1: neighbors},
            config=config
        )

        filtered = solver._filter_neighbors(neighbors)

        # 只有第一个邻居应该保留
        assert len(filtered) == 1
        assert filtered[0].neighbor_id == 2


class TestBlockingAngleCalculation:
    """测试遮挡角度计算（含坡度补偿和衰减）"""

    def test_basic_blocking_angle(self):
        """测试基础遮挡角度计算"""
        config = BacktrackingConfig()
        row = create_test_row()

        # 邻居在5米处，高1米
        neighbor = create_test_neighbor(
            neighbor_id=2,
            cross_axis_distance=5.0,
            along_axis_distance=0.0,
            vertical_offset=1.0,
            relative_position=1
        )

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={},
            config=config
        )

        blocking_angle = solver._neighbor_blocking_angle(row, neighbor)

        # 遮挡角度应约为 arctan(1/5) = 11.3度
        expected_angle = np.degrees(np.arctan2(1.0, 5.0))
        assert abs(blocking_angle - expected_angle) < 0.1

    def test_along_axis_decay(self):
        """测试沿轴距离衰减（20%衰减）"""
        config = BacktrackingConfig()
        row = create_test_row()

        # 邻居1：沿轴距离=0
        neighbor1 = create_test_neighbor(
            neighbor_id=2,
            cross_axis_distance=5.0,
            along_axis_distance=0.0,
            vertical_offset=1.0,
            relative_position=1
        )

        # 邻居2：沿轴距离=150（达到衰减因子1.0）
        neighbor2 = create_test_neighbor(
            neighbor_id=3,
            cross_axis_distance=5.0,
            along_axis_distance=150.0,
            vertical_offset=1.0,
            relative_position=1
        )

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={},
            config=config
        )

        angle1 = solver._neighbor_blocking_angle(row, neighbor1)
        angle2 = solver._neighbor_blocking_angle(row, neighbor2)

        # 邻居2的遮挡角度应该更小（因为高度被衰减20%）
        assert angle2 < angle1

        # 验证衰减效果：150米时，along_factor=1.0，高度衰减20%
        # angle1 = arctan(1.0 / 5.0)
        # angle2 = arctan(0.8 / 5.0)  # 高度衰减20%
        expected_angle1 = np.degrees(np.arctan2(1.0, 5.0))
        expected_angle2 = np.degrees(np.arctan2(0.8, 5.0))

        assert abs(angle1 - expected_angle1) < 0.1
        assert abs(angle2 - expected_angle2) < 0.1

    def test_cross_distance_epsilon(self):
        """测试横向距离过小时的处理"""
        config = BacktrackingConfig(cross_distance_epsilon=0.5)
        row = create_test_row()

        # 横向距离为0
        neighbor = create_test_neighbor(
            neighbor_id=2,
            cross_axis_distance=0.0,
            along_axis_distance=0.0,
            vertical_offset=1.0,
            relative_position=1
        )

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={},
            config=config
        )

        blocking_angle = solver._neighbor_blocking_angle(row, neighbor)

        # 应使用epsilon值（0.5）代替0
        expected_angle = np.degrees(np.arctan2(1.0, 0.5))
        assert abs(blocking_angle - expected_angle) < 0.1


class TestShadingMarginCalculation:
    """测试遮挡裕度计算"""

    def test_shading_margin_no_neighbors(self):
        """测试无邻居时的遮挡裕度"""
        config = BacktrackingConfig()
        row = create_test_row()

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={1: []},  # 无邻居
            config=config
        )

        # 创建太阳位置数据
        timestamps = pd.date_range('2025-01-01 12:00', periods=1, freq='H')
        solar_elevation = pd.Series([45.0], index=timestamps)
        solar_azimuth = pd.Series([180.0], index=timestamps)

        margin = solver._compute_shading_margin(row, solar_elevation, solar_azimuth)

        # 无邻居时，裕度应为无穷大
        assert margin.iloc[0] == np.inf

    def test_shading_margin_with_blocking(self):
        """测试有遮挡时的裕度计算"""
        config = BacktrackingConfig()
        row = create_test_row()

        # 邻居遮挡角度约为11.3度
        neighbors = [
            create_test_neighbor(
                neighbor_id=2,
                cross_axis_distance=5.0,
                along_axis_distance=0.0,
                vertical_offset=1.0,
                relative_position=1
            )
        ]

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={1: neighbors},
            config=config
        )

        timestamps = pd.date_range('2025-01-01 12:00', periods=1, freq='H')
        solar_elevation = pd.Series([20.0], index=timestamps)  # 太阳高度20度
        solar_azimuth = pd.Series([180.0], index=timestamps)

        margin = solver._compute_shading_margin(row, solar_elevation, solar_azimuth)

        # 遮挡裕度 = 太阳高度 - 遮挡角度
        # ≈ 20 - 11.3 = 8.7度
        assert margin.iloc[0] > 0  # 应该为正（无遮挡）
        assert margin.iloc[0] < 20  # 应该小于太阳高度


class TestTrackerAngleCalculation:
    """测试追踪角度计算和回溯限制"""

    def test_ideal_angle_without_backtracking(self):
        """测试理想追踪角度（无回溯）"""
        config = BacktrackingConfig(backtrack=False)
        row = create_test_row()

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={1: []},
            config=config
        )

        # 创建测试数据
        timestamps = pd.date_range('2025-01-01 12:00', periods=1, freq='H')
        solar_zenith = pd.Series([30.0], index=timestamps)  # 天顶角30度 = 高度角60度
        solar_azimuth = pd.Series([180.0], index=timestamps)  # 正南

        result = solver.compute_tracker_angles(solar_zenith, solar_azimuth)

        assert result.angles is not None
        assert len(result.angles) == 1
        assert 1 in result.angles.columns

    def test_with_nrel_shading_fraction(self):
        """测试使用NREL遮挡分数公式"""
        config = BacktrackingConfig(
            backtrack=True,
            use_nrel_shading_fraction=True,
            nrel_shading_limit_deg=5.0
        )
        row = create_test_row(slope_deg=10.0, slope_azimuth_deg=270.0)

        neighbors = [
            create_test_neighbor(
                neighbor_id=2,
                cross_axis_distance=5.0,
                along_axis_distance=0.0,
                vertical_offset=1.0,
                relative_position=1
            )
        ]

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={1: neighbors},
            config=config
        )

        timestamps = pd.date_range('2025-01-01 12:00', periods=3, freq='H')
        solar_zenith = pd.Series([60.0, 30.0, 60.0], index=timestamps)
        solar_azimuth = pd.Series([90.0, 180.0, 270.0], index=timestamps)

        result = solver.compute_tracker_angles(solar_zenith, solar_azimuth)

        assert result.angles is not None
        assert result.shading_factor is not None
        assert 1 in result.shading_factor.columns
        # 遮挡系数应在0-1范围内
        assert (result.shading_factor >= 0.0).all().all()
        assert (result.shading_factor <= 1.0).all().all()


class TestTerrainAwareSimpleModel:
    """测试地形感知简化模型"""

    def test_terrain_aware_model_enabled(self):
        """测试地形感知简化模型启用时的行为"""
        config = BacktrackingConfig(
            backtrack=True,
            use_nrel_shading_fraction=False,
            use_terrain_aware_simple_model=True,
            terrain_correction_threshold_deg=0.5,
        )
        # 10度坡度，坡度方位角与轴方位角垂直
        row = create_test_row(slope_deg=10.0, slope_azimuth_deg=270.0)

        neighbors = [
            create_test_neighbor(
                neighbor_id=2,
                cross_axis_distance=5.0,
                along_axis_distance=0.0,
                vertical_offset=1.0,
                relative_position=1
            )
        ]

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={1: neighbors},
            config=config
        )

        timestamps = pd.date_range('2025-01-01 12:00', periods=3, freq='H')
        solar_zenith = pd.Series([60.0, 30.0, 60.0], index=timestamps)
        solar_azimuth = pd.Series([90.0, 180.0, 270.0], index=timestamps)

        result = solver.compute_tracker_angles(solar_zenith, solar_azimuth)

        assert result.shading_factor is not None
        # 遮挡系数应在0-1范围内
        assert (result.shading_factor >= 0.0).all().all()
        assert (result.shading_factor <= 1.0).all().all()

    def test_terrain_aware_model_disabled(self):
        """测试地形感知简化模型禁用时的行为"""
        config = BacktrackingConfig(
            backtrack=True,
            use_nrel_shading_fraction=False,
            use_terrain_aware_simple_model=False,
        )
        row = create_test_row(slope_deg=10.0, slope_azimuth_deg=270.0)

        neighbors = [
            create_test_neighbor(
                neighbor_id=2,
                cross_axis_distance=5.0,
                along_axis_distance=0.0,
                vertical_offset=1.0,
                relative_position=1
            )
        ]

        solver = TerrainBacktrackingSolver(
            rows=[row],
            neighbors={1: neighbors},
            config=config
        )

        timestamps = pd.date_range('2025-01-01 12:00', periods=3, freq='H')
        solar_zenith = pd.Series([60.0, 30.0, 60.0], index=timestamps)
        solar_azimuth = pd.Series([90.0, 180.0, 270.0], index=timestamps)

        result = solver.compute_tracker_angles(solar_zenith, solar_azimuth)

        assert result.shading_factor is not None
        # 遮挡系数应在0-1范围内
        assert (result.shading_factor >= 0.0).all().all()
        assert (result.shading_factor <= 1.0).all().all()

    def test_terrain_correction_with_positive_margin(self):
        """测试正裕度时的地形修正"""
        config = BacktrackingConfig(
            use_terrain_aware_simple_model=True,
            terrain_correction_threshold_deg=0.5,
        )

        solver = TerrainBacktrackingSolver(
            rows=[create_test_row()],
            neighbors={},
            config=config
        )

        # 正裕度，有坡度
        sf = solver._calculate_terrain_adjusted_shading(
            shading_margin=5.0,  # 正裕度
            gcr=0.35,
            beta_c=5.0  # 5度坡度
        )

        # 有坡度时，即使正裕度，遮挡系数也应略低于1
        assert 0.9 <= sf <= 1.0

    def test_terrain_correction_with_negative_margin(self):
        """测试负裕度时的地形修正"""
        config = BacktrackingConfig(
            use_terrain_aware_simple_model=True,
            terrain_correction_threshold_deg=0.5,
            shading_margin_limit=10.0,
        )

        solver = TerrainBacktrackingSolver(
            rows=[create_test_row()],
            neighbors={},
            config=config
        )

        # 负裕度，有坡度
        sf = solver._calculate_terrain_adjusted_shading(
            shading_margin=-5.0,  # 负裕度（有遮挡）
            gcr=0.35,
            beta_c=5.0  # 5度坡度
        )

        # 负裕度时，遮挡系数应小于0.5
        assert 0.0 <= sf < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.terrain_backtracking"])
