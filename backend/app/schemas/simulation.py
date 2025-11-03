from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 模拟相关模式

class SimulationBase(BaseModel):
    name: str = Field(..., description="模拟名称", max_length=255)
    description: Optional[str] = Field(None, description="模拟描述")
    system_id: int = Field(..., description="光伏系统ID", gt=0)
    start_date: datetime = Field(..., description="开始时间")
    end_date: datetime = Field(..., description="结束时间")
    time_resolution: str = Field("hourly", description="时间分辨率: hourly, daily, monthly")
    weather_source: str = Field("nasa_sse", description="气象数据源: nasa_sse, meteonorm, custom")
    
    # 模拟配置
    include_shading: bool = Field(False, description="是否包含阴影分析")
    include_soiling: bool = Field(False, description="是否包含污秽损失")
    include_degradation: bool = Field(False, description="是否包含衰减分析")
    
    # 高级参数
    shading_factor: float = Field(0.0, description="阴影损失系数", ge=0, le=1)
    soiling_loss: float = Field(0.0, description="污秽损失系数", ge=0, le=1)
    degradation_rate: float = Field(0.0, description="年衰减率", ge=0, le=0.1)
    obstacles: Optional[List[Dict[str, Any]]] = Field(None, description="障碍物配置")
    
    # 经济参数
    electricity_price: float = Field(0.5, description="电价(元/kWh)", ge=0)
    inflation_rate: float = Field(0.03, description="通胀率", ge=0, le=1)
    discount_rate: float = Field(0.08, description="贴现率", ge=0, le=1)
    capex: Optional[float] = Field(None, description="初始投资成本(元)", ge=0)
    opex_percentage: float = Field(0.02, description="运维成本比例", ge=0, le=1)

class SimulationCreate(SimulationBase):
    pass

class SimulationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, description="状态: pending, running, completed, failed")
    progress: Optional[float] = Field(None, description="进度(0-100)", ge=0, le=100)
    
    # 模拟配置
    include_shading: Optional[bool] = Field(None, description="是否包含阴影分析")
    include_soiling: Optional[bool] = Field(None, description="是否包含污秽损失")
    include_degradation: Optional[bool] = Field(None, description="是否包含衰减分析")
    
    # 高级参数
    shading_factor: Optional[float] = Field(None, description="阴影损失系数", ge=0, le=1)
    soiling_loss: Optional[float] = Field(None, description="污秽损失系数", ge=0, le=1)
    degradation_rate: Optional[float] = Field(None, description="年衰减率", ge=0, le=0.1)
    obstacles: Optional[List[Dict[str, Any]]] = Field(None, description="障碍物配置")
    
    # 经济参数
    electricity_price: Optional[float] = Field(None, description="电价(元/kWh)", ge=0)
    inflation_rate: Optional[float] = Field(None, description="通胀率", ge=0, le=1)
    discount_rate: Optional[float] = Field(None, description="贴现率", ge=0, le=1)
    capex: Optional[float] = Field(None, description="初始投资成本(元)", ge=0)
    opex_percentage: Optional[float] = Field(None, description="运维成本比例", ge=0, le=1)

class SimulationResponse(SimulationBase):
    id: int
    status: str
    progress: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# 模拟结果模式

class SimulationResultBase(BaseModel):
    timestamp: datetime = Field(..., description="时间戳")
    power_dc: Optional[float] = Field(None, description="直流功率(W)")
    power_ac: Optional[float] = Field(None, description="交流功率(W)")
    energy_daily: Optional[float] = Field(None, description="日发电量(kWh)")
    efficiency: Optional[float] = Field(None, description="系统效率")
    irradiance_global: Optional[float] = Field(None, description="总辐射(W/m²)")
    irradiance_direct: Optional[float] = Field(None, description="直接辐射(W/m²)")
    irradiance_diffuse: Optional[float] = Field(None, description="散射辐射(W/m²)")
    temperature_ambient: Optional[float] = Field(None, description="环境温度(°C)")
    temperature_module: Optional[float] = Field(None, description="组件温度(°C)")
    performance_ratio: Optional[float] = Field(None, description="性能比")
    capacity_factor: Optional[float] = Field(None, description="容量系数")
    detailed_data: Optional[Dict[str, Any]] = Field(None, description="附加详细数据，如遮挡系数、诊断信息")

class SimulationResultResponse(SimulationResultBase):
    id: int
    simulation_id: int
    
    class Config:
        from_attributes = True