from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 位置相关模式

class LocationBase(BaseModel):
    name: str = Field(..., description="位置名称", max_length=255)
    latitude: float = Field(..., description="纬度", ge=-90, le=90)
    longitude: float = Field(..., description="经度", ge=-180, le=180)
    altitude: Optional[float] = Field(None, description="海拔高度(m)")
    timezone: str = Field("UTC", description="时区")
    country: Optional[str] = Field(None, description="国家", max_length=100)
    province: Optional[str] = Field(None, description="省份", max_length=100)
    city: Optional[str] = Field(None, description="城市", max_length=100)

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    altitude: Optional[float] = None
    timezone: Optional[str] = None
    country: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)

class LocationResponse(LocationBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# 天气数据模式

class WeatherDataBase(BaseModel):
    timestamp: datetime = Field(..., description="时间戳")
    location_id: int = Field(..., description="位置ID", gt=0)
    data_source: str = Field(..., description="数据源: nasa_sse, meteonorm, custom")
    
    # 气象参数
    temperature: Optional[float] = Field(None, description="温度(°C)")
    humidity: Optional[float] = Field(None, description="湿度(%)", ge=0, le=100)
    pressure: Optional[float] = Field(None, description="气压(hPa)")
    wind_speed: Optional[float] = Field(None, description="风速(m/s)", ge=0)
    wind_direction: Optional[float] = Field(None, description="风向(度)", ge=0, le=360)
    
    # 辐射参数
    ghi: Optional[float] = Field(None, description="水平面总辐射(W/m²)", ge=0)
    dni: Optional[float] = Field(None, description="法向直接辐射(W/m²)", ge=0)
    dhi: Optional[float] = Field(None, description="水平面散射辐射(W/m²)", ge=0)
    
    # 其他参数
    cloud_cover: Optional[float] = Field(None, description="云量(%)", ge=0, le=100)
    precipitation: Optional[float] = Field(None, description="降水量(mm)", ge=0)
    snow_depth: Optional[float] = Field(None, description="雪深(cm)", ge=0)

class WeatherDataCreate(WeatherDataBase):
    pass

class WeatherDataResponse(WeatherDataBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# 太阳位置计算模式

class SolarPositionRequest(BaseModel):
    latitude: float = Field(..., description="纬度", ge=-90, le=90)
    longitude: float = Field(..., description="经度", ge=-180, le=180)
    timestamp: datetime = Field(..., description="时间戳")
    timezone: str = Field("UTC", description="时区")

class SolarPositionResponse(BaseModel):
    azimuth: float = Field(..., description="方位角(度)", ge=0, le=360)
    elevation: float = Field(..., description="高度角(度)", ge=-90, le=90)
    zenith: float = Field(..., description="天顶角(度)", ge=0, le=180)
    sunrise: Optional[datetime] = Field(None, description="日出时间")
    sunset: Optional[datetime] = Field(None, description="日落时间")
    day_length: Optional[float] = Field(None, description="日照时长(小时)")

# 斜面辐射计算模式

class IrradianceRequest(BaseModel):
    latitude: float = Field(..., description="纬度", ge=-90, le=90)
    longitude: float = Field(..., description="经度", ge=-180, le=180)
    timestamp: datetime = Field(..., description="时间戳")
    tilt: float = Field(..., description="倾角(度)", ge=0, le=90)
    azimuth: float = Field(..., description="方位角(度)", ge=0, le=360)
    ghi: Optional[float] = Field(None, description="水平面总辐射(W/m²)")
    dni: Optional[float] = Field(None, description="法向直接辐射(W/m²)")
    dhi: Optional[float] = Field(None, description="水平面散射辐射(W/m²)")

class IrradianceResponse(BaseModel):
    poa_global: float = Field(..., description="斜面总辐射(W/m²)")
    poa_direct: float = Field(..., description="斜面直接辐射(W/m²)")
    poa_diffuse: float = Field(..., description="斜面散射辐射(W/m²)")
    poa_ground: float = Field(..., description="斜面地面反射辐射(W/m²)")
    incidence_angle: float = Field(..., description="入射角(度)")
    transposition_factor: float = Field(..., description="转换因子")