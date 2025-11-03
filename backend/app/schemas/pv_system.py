from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# PV系统相关模式

class PVSystemBase(BaseModel):
    name: str = Field(..., description="系统名称", max_length=255)
    description: Optional[str] = Field(None, description="系统描述")
    capacity_kw: float = Field(..., description="系统容量(kW)", gt=0)
    tilt_angle: float = Field(30.0, description="倾角(度)", ge=0, le=90)
    azimuth: float = Field(180.0, description="方位角(度)", ge=0, le=360)
    latitude: float = Field(..., description="纬度", ge=-90, le=90)
    longitude: float = Field(..., description="经度", ge=-180, le=180)
    altitude: float = Field(0.0, description="海拔(m)", ge=0)
    module_count: int = Field(..., description="组件数量", gt=0)
    string_count: int = Field(..., description="组串数量", gt=0)
    pitch: float = Field(4.1, description="行间距(m)", gt=0)

class PVSystemCreate(PVSystemBase):
    pass

class PVSystemUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    capacity_kw: Optional[float] = Field(None, gt=0)
    tilt_angle: Optional[float] = Field(None, ge=0, le=90)
    azimuth: Optional[float] = Field(None, ge=0, le=360)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    altitude: Optional[float] = Field(None, ge=0)
    pitch: Optional[float] = Field(None, description="行间距(m)", gt=0)

class PVSystemResponse(PVSystemBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# PV组件相关模式

class PVModuleBase(BaseModel):
    manufacturer: str = Field(..., description="制造商", max_length=100)
    model: str = Field(..., description="型号", max_length=100)
    power_rated: float = Field(..., description="额定功率(W)", gt=0)
    voltage_mp: Optional[float] = Field(None, description="最大功率点电压(V)")
    current_mp: Optional[float] = Field(None, description="最大功率点电流(A)")
    voltage_oc: Optional[float] = Field(None, description="开路电压(V)")
    current_sc: Optional[float] = Field(None, description="短路电流(A)")
    temp_coeff_power: float = Field(-0.004, description="功率温度系数(%/°C)")
    temp_coeff_voltage: float = Field(-0.003, description="电压温度系数(%/°C)")
    temp_coeff_current: float = Field(0.0005, description="电流温度系数(%/°C)")
    length: Optional[float] = Field(None, description="长度(mm)")
    width: Optional[float] = Field(None, description="宽度(mm)")
    height: Optional[float] = Field(None, description="高度(mm)")
    weight: Optional[float] = Field(None, description="重量(kg)")

class PVModuleCreate(PVModuleBase):
    pass

class PVModuleResponse(PVModuleBase):
    id: int
    system_id: int
    
    class Config:
        from_attributes = True

class PVModuleUpdate(BaseModel):
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    power_rated: Optional[float] = Field(None, gt=0)
    voltage_mp: Optional[float] = Field(None)
    current_mp: Optional[float] = Field(None)
    voltage_oc: Optional[float] = Field(None)
    current_sc: Optional[float] = Field(None)
    temp_coeff_power: Optional[float] = Field(None)
    temp_coeff_voltage: Optional[float] = Field(None)
    temp_coeff_current: Optional[float] = Field(None)
    length: Optional[float] = Field(None)
    width: Optional[float] = Field(None)
    height: Optional[float] = Field(None)
    weight: Optional[float] = Field(None)

# 逆变器相关模式

class InverterBase(BaseModel):
    manufacturer: str = Field(..., description="制造商", max_length=100)
    model: str = Field(..., description="型号", max_length=100)
    power_rated: float = Field(..., description="额定功率(W)", gt=0)
    voltage_dc_max: Optional[float] = Field(None, description="最大直流电压(V)")
    voltage_dc_min: Optional[float] = Field(None, description="最小直流电压(V)")
    current_dc_max: Optional[float] = Field(None, description="最大直流电流(A)")
    efficiency_max: float = Field(0.98, description="最大效率", ge=0, le=1)
    efficiency_euro: float = Field(0.97, description="欧洲效率", ge=0, le=1)

class InverterCreate(InverterBase):
    pass

class InverterResponse(InverterBase):
    id: int
    system_id: int
    
    class Config:
        from_attributes = True

class InverterUpdate(BaseModel):
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    power_rated: Optional[float] = Field(None, gt=0)
    voltage_dc_max: Optional[float] = Field(None)
    voltage_dc_min: Optional[float] = Field(None)
    current_dc_max: Optional[float] = Field(None)
    efficiency_max: Optional[float] = Field(None, ge=0, le=1)
    efficiency_euro: Optional[float] = Field(None, ge=0, le=1)

# 电池相关模式

class BatteryBase(BaseModel):
    manufacturer: str = Field(..., description="制造商", max_length=100)
    model: str = Field(..., description="型号", max_length=100)
    capacity_kwh: float = Field(..., description="容量(kWh)", gt=0)
    voltage_nominal: float = Field(..., description="标称电压(V)", gt=0)
    charge_rate_max: Optional[float] = Field(None, description="最大充电率(C)")
    discharge_rate_max: Optional[float] = Field(None, description="最大放电率(C)")
    cycle_life: Optional[int] = Field(None, description="循环寿命(次)", gt=0)
    depth_of_discharge: float = Field(0.8, description="放电深度", ge=0, le=1)

class BatteryCreate(BatteryBase):
    pass

class BatteryResponse(BatteryBase):
    id: int
    system_id: int
    
    class Config:
        from_attributes = True

class BatteryUpdate(BaseModel):
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    capacity_kwh: Optional[float] = Field(None, gt=0)
    voltage_nominal: Optional[float] = Field(None, gt=0)
    charge_rate_max: Optional[float] = Field(None)
    discharge_rate_max: Optional[float] = Field(None)
    cycle_life: Optional[int] = Field(None, gt=0)
    depth_of_discharge: Optional[float] = Field(None, ge=0, le=1)