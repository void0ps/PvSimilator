from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class PVSystem(Base):
    __tablename__ = "pv_systems"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # 系统参数
    capacity_kw = Column(Float, nullable=False)  # 系统容量(kW)
    tilt_angle = Column(Float, default=30.0)     # 倾角(度)
    azimuth = Column(Float, default=180.0)       # 方位角(度)
    
    # 位置信息
    latitude = Column(Float, nullable=False)     # 纬度
    longitude = Column(Float, nullable=False)    # 经度
    altitude = Column(Float, default=0.0)        # 海拔(m)
    
    # 系统配置
    module_count = Column(Integer, nullable=False)
    string_count = Column(Integer, nullable=False)
    pitch = Column(Float, default=4.1)  # 行间距(m)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    modules = relationship("PVModule", back_populates="system")
    inverters = relationship("Inverter", back_populates="system")
    batteries = relationship("Battery", back_populates="system")
    simulations = relationship("Simulation", back_populates="system")

class PVModule(Base):
    __tablename__ = "pv_modules"
    
    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, ForeignKey("pv_systems.id"))
    
    # 模块参数
    manufacturer = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    
    # 电气参数
    power_rated = Column(Float, nullable=False)  # 额定功率(W)
    voltage_mp = Column(Float)                   # 最大功率点电压(V)
    current_mp = Column(Float)                   # 最大功率点电流(A)
    voltage_oc = Column(Float)                   # 开路电压(V)
    current_sc = Column(Float)                   # 短路电流(A)
    
    # 温度系数
    temp_coeff_power = Column(Float, default=-0.004)  # 功率温度系数(%/°C)
    temp_coeff_voltage = Column(Float, default=-0.003) # 电压温度系数(%/°C)
    temp_coeff_current = Column(Float, default=0.0005) # 电流温度系数(%/°C)
    
    # 物理参数
    length = Column(Float)    # 长度(mm)
    width = Column(Float)     # 宽度(mm)
    height = Column(Float, nullable=True)    # 高度(mm)
    weight = Column(Float)    # 重量(kg)
    
    # 关系
    system = relationship("PVSystem", back_populates="modules")

class Inverter(Base):
    __tablename__ = "inverters"
    
    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, ForeignKey("pv_systems.id"))
    
    # 逆变器参数
    manufacturer = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    
    # 额定参数
    power_rated = Column(Float, nullable=False)  # 额定功率(W)
    voltage_dc_max = Column(Float)               # 最大直流电压(V)
    voltage_dc_min = Column(Float)               # 最小直流电压(V)
    current_dc_max = Column(Float)               # 最大直流电流(A)
    
    # 效率参数
    efficiency_max = Column(Float, default=0.98)  # 最大效率
    efficiency_euro = Column(Float, default=0.97) # 欧洲效率
    
    # 关系
    system = relationship("PVSystem", back_populates="inverters")

class Battery(Base):
    __tablename__ = "batteries"
    
    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, ForeignKey("pv_systems.id"))
    
    # 电池参数
    manufacturer = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    
    # 容量参数
    capacity_kwh = Column(Float, nullable=False)  # 容量(kWh)
    voltage_nominal = Column(Float, nullable=False) # 标称电压(V)
    
    # 充放电参数
    charge_rate_max = Column(Float)  # 最大充电率(C)
    discharge_rate_max = Column(Float) # 最大放电率(C)
    
    # 寿命参数
    cycle_life = Column(Integer)     # 循环寿命(次)
    depth_of_discharge = Column(Float, default=0.8) # 放电深度
    
    # 关系
    system = relationship("PVSystem", back_populates="batteries")