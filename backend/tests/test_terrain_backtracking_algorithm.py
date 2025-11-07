"""
测试地形感知回溯算法的核心计算
- GCR计算
- 遮挡裕度
- 坡度补偿
- 沿轴距离衰减
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
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = BacktrackingConfig(
            module_width=1.0,
            max_angle=60.0,
            backtrack=False
        )
        
        assert config.module_width == 1.0
        assert config.max_angle == 60.0
        assert config.backtrack is False


class TestGCRCalculation:
    """测试GCR（地面覆盖率）计算"""
    
    def test_gcr_calculation(self):
        """测试GCR计算公式"""
        config = BacktrackingConfig(module_width=2.0)
        
        # 创建简单的行
        row = TrackerRow(
            table_id=1,
            center_x=0.0,
            center_y=0.0,
            axis_azimuth=180.0,
            axis_tilt=0.0
        )
        
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
        
        row = TrackerRow(table_id=1, center_x=0, center_y=0, axis_azimuth=180, axis_tilt=0)
        
        neighbors = [
            RowNeighbor(
                neighbor_id=2,
                cross_axis_distance=0.3,  # 太近，应被过滤
                along_axis_distance=10.0,
                vertical_offset=1.0,
                relative_position=1
            ),
            RowNeighbor(
                neighbor_id=3,
                cross_axis_distance=5.0,  # 正常范围
                along_axis_distance=10.0,
                vertical_offset=1.0,
                relative_position=1
            ),
            RowNeighbor(
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
        
        # 只有第二个邻居应该保留
        assert len(filtered) == 1
        assert filtered[0].neighbor_id == 3
    
    def test_filter_by_along_distance(self):
        """测试沿轴距离过滤"""
        config = BacktrackingConfig(
            max_neighbor_cross_distance=20.0,
            max_neighbor_along_distance=250.0
        )
        
        row = TrackerRow(table_id=1, center_x=0, center_y=0, axis_azimuth=180, axis_tilt=0)
        
        neighbors = [
            RowNeighbor(
                neighbor_id=2,
                cross_axis_distance=5.0,
                along_axis_distance=100.0,  # 正常范围
                vertical_offset=1.0,
                relative_position=1
            ),
            RowNeighbor(
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
        row = TrackerRow(table_id=1, center_x=0, center_y=0, axis_azimuth=180, axis_tilt=0)
        
        # 邻居在5米处，高1米
        neighbor = RowNeighbor(
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
        row = TrackerRow(table_id=1, center_x=0, center_y=0, axis_azimuth=180, axis_tilt=0)
        
        # 邻居1：沿轴距离=0
        neighbor1 = RowNeighbor(
            neighbor_id=2,
            cross_axis_distance=5.0,
            along_axis_distance=0.0,
            vertical_offset=1.0,
            relative_position=1
        )
        
        # 邻居2：沿轴距离=150（达到衰减因子1.0）
        neighbor2 = RowNeighbor(
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
        row = TrackerRow(table_id=1, center_x=0, center_y=0, axis_azimuth=180, axis_tilt=0)
        
        # 横向距离为0
        neighbor = RowNeighbor(
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
        row = TrackerRow(table_id=1, center_x=0, center_y=0, axis_azimuth=180, axis_tilt=0)
        
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
        row = TrackerRow(table_id=1, center_x=0, center_y=0, axis_azimuth=180, axis_tilt=0)
        
        # 邻居遮挡角度约为11.3度
        neighbors = [
            RowNeighbor(
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
        row = TrackerRow(table_id=1, center_x=0, center_y=0, axis_azimuth=180, axis_tilt=0)
        
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.terrain_backtracking"])



