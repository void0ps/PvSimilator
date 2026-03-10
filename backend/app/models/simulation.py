from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, ForeignKey("pv_systems.id"))

    # 模拟参数
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 时间范围
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    time_resolution = Column(String(20), default="hourly")  # hourly, daily, monthly

    # 模拟配置
    weather_source = Column(String(50), default="nasa_sse")  # nasa_sse, meteonorm, custom
    include_shading = Column(Boolean, default=False)
    include_soiling = Column(Boolean, default=False)
    include_degradation = Column(Boolean, default=False)
    backtrack_enabled = Column(Boolean, default=True)  # 启用地形感知回溯算法

    # NREL 论文高级参数
    use_nrel_shading_fraction = Column(Boolean, default=False)  # 使用NREL论文遮挡公式 (Equation 32)
    use_nrel_slope_aware_correction = Column(Boolean, default=False)  # 使用NREL斜坡感知修正 (Equations 11-14)
    use_partial_shading_model = Column(Boolean, default=False)  # 使用NREL部分遮挡功率模型 (Equation 4)
    cells_per_column = Column(Integer, default=12)  # 每列电池数N (72电池模块N=12)
    sky_model = Column(String(20), default="isotropic")  # 天空模型: isotropic, hay, perez

    # 高级参数
    shading_factor = Column(Float, default=0.0)      # 阴影损失系数
    soiling_loss = Column(Float, default=0.0)        # 污秽损失系数
    degradation_rate = Column(Float, default=0.0)    # 年衰减率
    obstacles = Column(JSON)                         # 障碍物配置

    # 经济参数
    electricity_price = Column(Float, default=0.5)  # 电价(元/kWh)
    inflation_rate = Column(Float, default=0.03)    # 通胀率
    discount_rate = Column(Float, default=0.08)     # 贴现率
    capex = Column(Float)                           # 初始投资成本(元)
    opex_percentage = Column(Float, default=0.02)  # 运维成本比例

    # 状态
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)          # 进度(0-100)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # 关系
    system = relationship("PVSystem", back_populates="simulations")
    results = relationship("SimulationResult", back_populates="simulation")

class SimulationResult(Base):
    __tablename__ = "simulation_results"
    
    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    
    # 时间戳
    timestamp = Column(DateTime, nullable=False)
    
    # 发电数据
    power_dc = Column(Float)           # 直流功率(W)
    power_ac = Column(Float)           # 交流功率(W)
    energy_daily = Column(Float)       # 日发电量(kWh)
    efficiency = Column(Float)         # 系统效率
    
    # 环境数据
    irradiance_global = Column(Float)  # 总辐射(W/m²)
    irradiance_direct = Column(Float)  # 直接辐射(W/m²)
    irradiance_diffuse = Column(Float) # 散射辐射(W/m²)
    temperature_ambient = Column(Float) # 环境温度(°C)
    temperature_module = Column(Float) # 组件温度(°C)
    
    # 性能指标
    performance_ratio = Column(Float)  # 性能比
    capacity_factor = Column(Float)   # 容量系数
    
    # 详细数据(JSON格式存储)
    detailed_data = Column(JSON)      # 详细模拟数据
    
    # 关系
    simulation = relationship("Simulation", back_populates="results")