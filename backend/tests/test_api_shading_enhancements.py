"""
测试遮挡数据API的增强功能（步骤12）
- 分页功能
- 时间过滤
- 数据抽样
- 聚合接口
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.core.database import Base, get_db
from app.models.simulation import Simulation, SimulationResult
from app.api import simulations  # 导入simulations路由


# 创建测试用的FastAPI app
app = FastAPI()
app.include_router(simulations.router, prefix="/api/v1/simulations", tags=["simulations"])

# 测试数据库设置
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_shading.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """设置测试数据库"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_simulation_with_results(setup_database):
    """创建包含结果的示例模拟"""
    db = TestingSessionLocal()
    
    try:
        # 创建模拟
        simulation = Simulation(
            name="测试模拟",
            system_id=1,
            start_date=datetime(2025, 11, 1),
            end_date=datetime(2025, 11, 3),
            resolution_minutes=60,
            include_shading=True,
            status="completed"
        )
        db.add(simulation)
        db.commit()
        db.refresh(simulation)
        
        # 创建72小时的结果数据（每小时1条）
        start_time = datetime(2025, 11, 1, 0, 0)
        for i in range(72):
            timestamp = start_time + timedelta(hours=i)
            
            # 模拟遮挡系数变化
            hour_of_day = timestamp.hour
            if 6 <= hour_of_day <= 18:  # 白天
                terrain_multiplier = 0.5 + 0.3 * (abs(hour_of_day - 12) / 6)  # 正午最高
                shading_multiplier = 0.8 + 0.1 * (abs(hour_of_day - 12) / 6)
            else:  # 夜间
                terrain_multiplier = 0.0
                shading_multiplier = 0.0
            
            result = SimulationResult(
                simulation_id=simulation.id,
                timestamp=timestamp,
                power_ac=100.0 * terrain_multiplier if terrain_multiplier > 0 else 0.0,
                irradiance_global=800.0 if 6 <= hour_of_day <= 18 else 0.0,
                detailed_data={
                    "terrain_shading_multiplier": terrain_multiplier,
                    "shading_multiplier": shading_multiplier,
                    "poa_global": 800.0 if 6 <= hour_of_day <= 18 else 0.0
                }
            )
            db.add(result)
        
        db.commit()
        return simulation.id
        
    finally:
        db.close()


class TestShadingPagination:
    """测试分页功能"""
    
    def test_pagination_with_limit(self, sample_simulation_with_results):
        """测试limit参数"""
        sim_id = sample_simulation_with_results
        
        response = client.get(f"/api/v1/simulations/{sim_id}/shading?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 10
        assert len(data["series"]) == 10
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["returned"] == 10
        assert data["pagination"]["total"] == 72
    
    def test_pagination_with_offset(self, sample_simulation_with_results):
        """测试offset参数"""
        sim_id = sample_simulation_with_results
        
        response = client.get(f"/api/v1/simulations/{sim_id}/shading?limit=10&offset=20")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 10
        assert data["pagination"]["offset"] == 20
        assert data["pagination"]["limit"] == 10
    
    def test_pagination_last_page(self, sample_simulation_with_results):
        """测试最后一页"""
        sim_id = sample_simulation_with_results
        
        response = client.get(f"/api/v1/simulations/{sim_id}/shading?limit=20&offset=60")
        
        assert response.status_code == 200
        data = response.json()
        
        # 总共72条，offset 60后应该只剩12条
        assert data["count"] == 12
        assert data["pagination"]["returned"] == 12


class TestTimeFiltering:
    """测试时间过滤功能"""
    
    def test_filter_by_start_time(self, sample_simulation_with_results):
        """测试start_time过滤"""
        sim_id = sample_simulation_with_results
        
        response = client.get(
            f"/api/v1/simulations/{sim_id}/shading?start_time=2025-11-02T00:00:00"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该只返回11月2日和3日的数据（48小时）
        assert data["count"] == 48
        
        # 验证第一条记录的时间
        first_timestamp = datetime.fromisoformat(data["series"][0]["timestamp"])
        assert first_timestamp >= datetime(2025, 11, 2, 0, 0)
    
    def test_filter_by_end_time(self, sample_simulation_with_results):
        """测试end_time过滤"""
        sim_id = sample_simulation_with_results
        
        response = client.get(
            f"/api/v1/simulations/{sim_id}/shading?end_time=2025-11-01T23:59:59"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该只返回11月1日的数据（24小时）
        assert data["count"] == 24
    
    def test_filter_by_time_range(self, sample_simulation_with_results):
        """测试时间范围过滤"""
        sim_id = sample_simulation_with_results
        
        response = client.get(
            f"/api/v1/simulations/{sim_id}/shading"
            f"?start_time=2025-11-01T12:00:00&end_time=2025-11-02T12:00:00"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该返回11月1日12:00到11月2日12:00的数据（25小时）
        assert data["count"] == 25
    
    def test_invalid_time_format(self, sample_simulation_with_results):
        """测试无效时间格式"""
        sim_id = sample_simulation_with_results
        
        response = client.get(
            f"/api/v1/simulations/{sim_id}/shading?start_time=invalid-date"
        )
        
        assert response.status_code == 400
        assert "格式无效" in response.json()["detail"]


class TestDataSampling:
    """测试数据抽样功能"""
    
    def test_sample_rate_basic(self, sample_simulation_with_results):
        """测试基础抽样"""
        sim_id = sample_simulation_with_results
        
        # 每5条取1条
        response = client.get(f"/api/v1/simulations/{sim_id}/shading?sample_rate=5")
        
        assert response.status_code == 200
        data = response.json()
        
        # 72条数据，每5条取1条，应该约为14-15条
        assert data["count"] >= 14 and data["count"] <= 15
        assert data["pagination"]["sample_rate"] == 5
    
    def test_sample_rate_with_pagination(self, sample_simulation_with_results):
        """测试抽样与分页结合"""
        sim_id = sample_simulation_with_results
        
        response = client.get(
            f"/api/v1/simulations/{sim_id}/shading?limit=20&sample_rate=2"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 先取20条，再每2条取1条，应该约为10条
        assert data["count"] == 10


class TestAggregatedAPI:
    """测试聚合接口"""
    
    def test_aggregated_hourly(self, sample_simulation_with_results):
        """测试每小时聚合"""
        sim_id = sample_simulation_with_results
        
        response = client.get(
            f"/api/v1/simulations/{sim_id}/shading/aggregated?interval=1H&metric=mean"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 72小时数据，每小时聚合，应该还是72条
        assert data["count"] == 72
        assert data["aggregation"]["interval"] == "1H"
        assert data["aggregation"]["metric"] == "mean"
    
    def test_aggregated_daily(self, sample_simulation_with_results):
        """测试每日聚合"""
        sim_id = sample_simulation_with_results
        
        response = client.get(
            f"/api/v1/simulations/{sim_id}/shading/aggregated?interval=1D&metric=mean"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 3天数据，每天聚合，应该为3条
        assert data["count"] == 3
        assert data["aggregation"]["interval"] == "1D"
        assert data["aggregation"]["metric"] == "mean"
        assert data["aggregation"]["original_count"] == 72
    
    def test_aggregated_with_different_metrics(self, sample_simulation_with_results):
        """测试不同聚合指标"""
        sim_id = sample_simulation_with_results
        
        metrics = ["mean", "min", "max", "median"]
        
        for metric in metrics:
            response = client.get(
                f"/api/v1/simulations/{sim_id}/shading/aggregated"
                f"?interval=1D&metric={metric}"
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["aggregation"]["metric"] == metric
            assert data["count"] == 3
    
    def test_aggregated_reduction_ratio(self, sample_simulation_with_results):
        """测试数据压缩比例"""
        sim_id = sample_simulation_with_results
        
        response = client.get(
            f"/api/v1/simulations/{sim_id}/shading/aggregated?interval=1D&metric=mean"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 72条聚合为3条，压缩比例应该约为95.8%
        assert "reduction_ratio" in data["aggregation"]
        ratio_str = data["aggregation"]["reduction_ratio"]
        assert "95" in ratio_str or "96" in ratio_str
    
    def test_aggregated_invalid_interval(self, sample_simulation_with_results):
        """测试无效的聚合间隔"""
        sim_id = sample_simulation_with_results
        
        response = client.get(
            f"/api/v1/simulations/{sim_id}/shading/aggregated?interval=INVALID"
        )
        
        assert response.status_code == 400
        assert "聚合失败" in response.json()["detail"]


class TestAPIErrorHandling:
    """测试API错误处理"""
    
    def test_nonexistent_simulation(self):
        """测试不存在的模拟ID"""
        response = client.get("/api/v1/simulations/999999/shading")
        
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]
    
    def test_simulation_without_shading(self, setup_database):
        """测试未启用遮挡分析的模拟"""
        db = TestingSessionLocal()
        
        try:
            simulation = Simulation(
                name="无遮挡模拟",
                system_id=1,
                start_date=datetime(2025, 11, 1),
                end_date=datetime(2025, 11, 2),
                include_shading=False,  # 未启用遮挡
                status="completed"
            )
            db.add(simulation)
            db.commit()
            db.refresh(simulation)
            
            response = client.get(f"/api/v1/simulations/{simulation.id}/shading")
            
            assert response.status_code == 200
            data = response.json()
            assert data["include_shading"] is False
            assert "未开启遮挡分析" in data["message"]
            
        finally:
            db.close()
    
    def test_invalid_limit_parameter(self, sample_simulation_with_results):
        """测试无效的limit参数"""
        sim_id = sample_simulation_with_results
        
        # limit超出范围
        response = client.get(f"/api/v1/simulations/{sim_id}/shading?limit=20000")
        
        assert response.status_code == 422  # Validation error
    
    def test_negative_offset(self, sample_simulation_with_results):
        """测试负数offset"""
        sim_id = sample_simulation_with_results
        
        response = client.get(f"/api/v1/simulations/{sim_id}/shading?offset=-1")
        
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

