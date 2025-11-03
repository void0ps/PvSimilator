from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Location(Base):
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 位置信息
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, default=0.0)
    timezone = Column(String(50), default="UTC+8")
    
    # 地理信息
    country = Column(String(100))
    province = Column(String(100))
    city = Column(String(100))
    
    # 气象数据源
    weather_source = Column(String(50), default="nasa_sse")
    data_available = Column(Boolean, default=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    weather_data = relationship("WeatherData", back_populates="location")

class WeatherData(Base):
    __tablename__ = "weather_data"
    
    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    
    # 时间戳
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # 太阳辐射数据
    ghi = Column(Float)  # 水平面总辐射(W/m²)
    dni = Column(Float)  # 法向直接辐射(W/m²)
    dhi = Column(Float)  # 水平面散射辐射(W/m²)
    
    # 气象数据
    temperature = Column(Float)      # 温度(°C)
    humidity = Column(Float)         # 湿度(%)
    pressure = Column(Float)         # 气压(hPa)
    wind_speed = Column(Float)       # 风速(m/s)
    wind_direction = Column(Float)   # 风向(度)
    
    # 云量数据
    cloud_cover = Column(Float)     # 云量(0-1)
    precipitation = Column(Float)    # 降水量(mm)
    
    # 太阳位置数据
    solar_zenith = Column(Float)     # 太阳天顶角(度)
    solar_azimuth = Column(Float)    # 太阳方位角(度)
    
    # 数据质量
    data_source = Column(String(50), default="nasa_sse")
    quality_flag = Column(Integer, default=0)  # 数据质量标志
    
    # 关系
    location = relationship("Location", back_populates="weather_data")