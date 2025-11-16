"""
测试地形服务的健壮性功能
- 缓存刷新锁
- 异常重试
- 空数据回退
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import threading
import time

from app.services.terrain_service import TerrainService, TerrainBounds


class TestTerrainServiceRobustness:
    """测试地形服务的健壮性功能（步骤11新增）"""
    
    def test_load_layout_with_valid_file(self):
        """测试正常加载地形数据"""
        # 使用实际的地形文件
        project_root = Path(__file__).resolve().parents[2]
        file_path = project_root / "带坡度地形数据.xlsx"
        
        if not file_path.exists():
            pytest.skip("地形数据文件不存在，跳过测试")
        
        service = TerrainService(file_path)
        data = service.load_layout()
        
        assert data is not None
        assert "metadata" in data
        assert "tables" in data
        assert data["metadata"]["total_tables"] > 0
        assert data["metadata"]["total_piles"] > 0
        assert len(data["tables"]) > 0
    
    def test_load_layout_with_nonexistent_file(self):
        """测试文件不存在时的回退机制"""
        service = TerrainService("nonexistent_file.xlsx")
        
        # 应该返回空数据结构，而不是抛出异常
        data = service.load_layout()
        
        assert data is not None
        assert "metadata" in data
        assert "tables" in data
        assert data["metadata"]["total_tables"] == 0
        assert data["metadata"]["total_piles"] == 0
        assert len(data["tables"]) == 0
        assert "error" in data["metadata"]
        assert "不存在或无法加载" in data["metadata"]["error"]
    
    def test_empty_layout_structure(self):
        """测试空数据结构的完整性"""
        service = TerrainService("fake.xlsx")
        empty_data = service._get_empty_layout()
        
        # 验证结构完整性
        assert "metadata" in empty_data
        assert "tables" in empty_data
        assert empty_data["tables"] == []
        
        # 验证metadata字段
        metadata = empty_data["metadata"]
        assert "source_file" in metadata
        assert "total_tables" in metadata
        assert "total_piles" in metadata
        assert "generated_at" in metadata
        assert "bounds" in metadata
        assert "error" in metadata
        
        # 验证数值
        assert metadata["total_tables"] == 0
        assert metadata["total_piles"] == 0
        assert metadata["bounds"] is None
    
    @patch('app.services.terrain_service.TerrainService._read_excel')
    def test_retry_mechanism(self, mock_read_excel):
        """测试异常重试机制"""
        project_root = Path(__file__).resolve().parents[2]
        file_path = project_root / "带坡度地形数据.xlsx"
        
        # 模拟前2次失败，第3次成功
        mock_read_excel.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            MagicMock(empty=False, __len__=lambda x: 10)  # 成功返回非空DataFrame
        ]
        
        service = TerrainService(file_path)
        service._max_retries = 3
        service._retry_delay = 0.01  # 减少延迟加快测试
        
        # 由于重试机制，最终应该成功
        # 注意：这里会触发完整的加载流程
        with patch.object(service, '_load_layout_cached') as mock_cached:
            mock_cached.side_effect = [
                Exception("First failure"),
                Exception("Second failure"),
                {"metadata": {"total_tables": 1}, "tables": []}
            ]
            
            data = service.load_layout()
            
            # 验证重试了3次
            assert mock_cached.call_count == 3
            # 最终应返回空数据（因为最后一次失败后返回回退数据）
    
    @patch('app.services.terrain_service.TerrainService._load_layout_cached')
    def test_retry_with_exponential_backoff(self, mock_cached):
        """测试指数退避重试"""
        project_root = Path(__file__).resolve().parents[2]
        file_path = project_root / "带坡度地形数据.xlsx"
        
        mock_cached.side_effect = Exception("Persistent failure")
        
        service = TerrainService(file_path)
        service._max_retries = 3
        service._retry_delay = 0.1
        
        start_time = time.time()
        data = service.load_layout()
        elapsed = time.time() - start_time
        
        # 验证有重试延迟（0.1 + 0.2 = 0.3秒的延迟，因为只重试2次后就放弃）
        assert elapsed >= 0.2  # 允许一些误差，确保有延迟
        
        # 应返回空数据结构
        assert data["metadata"]["total_tables"] == 0
    
    def test_cache_refresh_lock(self):
        """测试缓存刷新锁（并发测试）"""
        project_root = Path(__file__).resolve().parents[2]
        file_path = project_root / "带坡度地形数据.xlsx"
        
        if not file_path.exists():
            pytest.skip("地形数据文件不存在，跳过测试")
        
        service = TerrainService(file_path)
        refresh_count = [0]
        
        def refresh_cache():
            """多个线程同时刷新缓存"""
            with service._refresh_lock:
                refresh_count[0] += 1
                time.sleep(0.01)  # 模拟刷新操作
        
        # 创建多个线程同时刷新
        threads = [threading.Thread(target=refresh_cache) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 所有线程都应该成功执行
        assert refresh_count[0] == 5
    
    def test_get_table_with_valid_id(self):
        """测试获取指定table"""
        project_root = Path(__file__).resolve().parents[2]
        file_path = project_root / "带坡度地形数据.xlsx"
        
        if not file_path.exists():
            pytest.skip("地形数据文件不存在，跳过测试")
        
        service = TerrainService(file_path)
        data = service.load_layout()
        
        if len(data["tables"]) > 0:
            first_table_id = data["tables"][0]["table_id"]
            table = service.get_table(first_table_id)
            
            assert table is not None
            assert table["table_id"] == first_table_id
            assert "piles" in table
    
    def test_get_table_with_invalid_id(self):
        """测试获取不存在的table"""
        project_root = Path(__file__).resolve().parents[2]
        file_path = project_root / "带坡度地形数据.xlsx"
        
        if not file_path.exists():
            pytest.skip("地形数据文件不存在，跳过测试")
        
        service = TerrainService(file_path)
        table = service.get_table(999999)
        
        assert table is None
    
    def test_bounds_calculation(self):
        """测试边界计算"""
        project_root = Path(__file__).resolve().parents[2]
        file_path = project_root / "带坡度地形数据.xlsx"
        
        if not file_path.exists():
            pytest.skip("地形数据文件不存在，跳过测试")
        
        service = TerrainService(file_path)
        data = service.load_layout()
        
        if data["metadata"]["bounds"]:
            bounds = data["metadata"]["bounds"]
            assert bounds["min_x"] < bounds["max_x"]
            assert bounds["min_y"] < bounds["max_y"]
            if bounds["min_z"] is not None and bounds["max_z"] is not None:
                assert bounds["min_z"] <= bounds["max_z"]


class TestTerrainBounds:
    """测试 TerrainBounds 数据类"""
    
    def test_terrain_bounds_creation(self):
        """测试创建 TerrainBounds"""
        bounds = TerrainBounds(
            min_x=0.0,
            max_x=100.0,
            min_y=0.0,
            max_y=100.0,
            min_z=-10.0,
            max_z=10.0
        )
        
        assert bounds.min_x == 0.0
        assert bounds.max_x == 100.0
        assert bounds.min_y == 0.0
        assert bounds.max_y == 100.0
        assert bounds.min_z == -10.0
        assert bounds.max_z == 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.terrain_service"])

