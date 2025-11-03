from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import pandas as pd
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.weather import Location, WeatherData
from app.schemas.weather import LocationCreate, LocationResponse, WeatherDataResponse, LocationUpdate
from app.services.weather_service import WeatherService
from app.services.pv_calculator import PVCalculator

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/locations/", response_model=LocationResponse)
async def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db)
):
    """创建位置信息"""
    try:
        db_location = Location(**location.dict())
        db.add(db_location)
        db.commit()
        db.refresh(db_location)
        return db_location
    except Exception as e:
        db.rollback()
        logger.error(f"创建位置失败: {e}")
        raise HTTPException(status_code=500, detail="创建位置失败")

@router.get("/locations/", response_model=List[LocationResponse])
async def get_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取位置列表"""
    locations = db.query(Location).offset(skip).limit(limit).all()
    return locations

@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: int,
    db: Session = Depends(get_db)
):
    """获取特定位置信息"""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="位置不存在")
    return location

@router.put("/locations/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: int,
    location_update: LocationUpdate,
    db: Session = Depends(get_db)
):
    """更新位置信息"""
    try:
        # 获取现有位置
        db_location = db.query(Location).filter(Location.id == location_id).first()
        if not db_location:
            raise HTTPException(status_code=404, detail="位置不存在")
        
        # 更新字段
        update_data = location_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_location, field, value)
        
        db.commit()
        db.refresh(db_location)
        return db_location
    except Exception as e:
        db.rollback()
        logger.error(f"更新位置失败: {e}")
        raise HTTPException(status_code=500, detail="更新位置失败")

@router.delete("/locations/{location_id}")
async def delete_location(
    location_id: int,
    db: Session = Depends(get_db)
):
    """删除位置信息"""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="位置不存在")
    
    try:
        db.delete(location)
        db.commit()
        return {"message": "位置删除成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除位置失败: {e}")
        raise HTTPException(status_code=500, detail="删除位置失败")

@router.get("/data/")
async def get_weather_data(
    location_id: Optional[int] = Query(None, description="位置ID"),
    latitude: Optional[float] = Query(None, description="纬度", ge=-90, le=90),
    longitude: Optional[float] = Query(None, description="经度", ge=-180, le=180),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    source: str = Query("nasa_sse", description="数据源: nasa_sse, meteonorm, synthetic"),
    resolution: str = Query("daily", description="时间分辨率: daily, hourly"),
    limit: Optional[int] = Query(None, description="返回数据条数限制"),
    db: Session = Depends(get_db)
):
    """获取气象数据"""
    try:
        # 如果没有提供位置信息，返回数据库中存储的气象数据
        if location_id is None and latitude is None and longitude is None:
            # 查询数据库中的气象数据
            query = db.query(WeatherData)
            
            # 应用日期过滤
            if start_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(WeatherData.timestamp >= start_dt)
            if end_date:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                query = query.filter(WeatherData.timestamp <= end_dt)
            
            # 按时间倒序排列
            query = query.order_by(WeatherData.timestamp.desc())
            
            # 应用条数限制
            if limit:
                query = query.limit(limit)
            
            weather_data_records = query.all()
            
            # 转换为字典格式
            weather_data = []
            for record in weather_data_records:
                weather_data.append({
                    "id": record.id,
                    "location_id": record.location_id,
                    "timestamp": record.timestamp.isoformat(),
                    "temperature": record.temperature,
                    "ghi": record.ghi,
                    "dni": record.dni,
                    "dhi": record.dhi,
                    "humidity": record.humidity,
                    "pressure": record.pressure,
                    "wind_speed": record.wind_speed,
                    "wind_direction": record.wind_direction,
                    "cloud_cover": record.cloud_cover,
                    "precipitation": record.precipitation,
                    "solar_zenith": record.solar_zenith,
                    "solar_azimuth": record.solar_azimuth,
                    "data_source": record.data_source
                })
            
            return {
                "data_count": len(weather_data),
                "weather_data": weather_data
            }
        
        # 如果提供了位置信息，从外部API获取实时气象数据
        weather_service = WeatherService()
        
        # 如果提供了location_id，从数据库获取位置信息
        if location_id:
            location = db.query(Location).filter(Location.id == location_id).first()
            if not location:
                raise HTTPException(status_code=404, detail="位置不存在")
            latitude = location.latitude
            longitude = location.longitude
        
        # 检查必需的参数
        if latitude is None or longitude is None:
            raise HTTPException(status_code=400, detail="需要提供位置信息（location_id或经纬度）")
        
        # 设置默认日期范围（最近30天）
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 获取气象数据
        weather_df = await weather_service.get_weather_data(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            source=source,
            time_resolution=resolution
        )
        
        data_resolution = getattr(weather_df, 'attrs', {}).get('resolution') if hasattr(weather_df, 'attrs') else None

        if resolution == "hourly" and data_resolution != 'hourly':
            weather_df = weather_service.calculate_hourly_data(
                weather_df,
                start_date,
                end_date,
                time_resolution=resolution
            )
        
        # 转换为字典格式返回
        weather_data = weather_df.to_dict('records')
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "source": source,
            "resolution": resolution,
            "data_count": len(weather_data),
            "weather_data": weather_data
        }
        
    except Exception as e:
        logger.error(f"获取气象数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取气象数据失败: {str(e)}")

@router.get("/solar-position/")
async def get_solar_position(
    latitude: float = Query(..., description="纬度", ge=-90, le=90),
    longitude: float = Query(..., description="经度", ge=-180, le=180),
    date: str = Query(..., description="日期 (YYYY-MM-DD)"),
    time: Optional[str] = Query(None, description="时间 (HH:MM:SS)"),
    timezone: str = Query('Asia/Shanghai', description="时区")
):
    """计算太阳位置"""
    try:
        from app.services.pv_calculator import PVCalculator
        
        calculator = PVCalculator(latitude=latitude, longitude=longitude, timezone=timezone)
        
        if time:
            datetime_str = f"{date} {time}"
            times = pd.DatetimeIndex([pd.to_datetime(datetime_str)]).tz_localize(timezone)
        else:
            # 计算全天的太阳位置
            times = pd.date_range(
                start=f"{date} 00:00:00",
                end=f"{date} 23:59:59",
                freq='H'
            ).tz_localize(timezone)
        
        solar_position = calculator.calculate_solar_position(times)
        
        # 转换为字典格式
        result = []
        for idx, (timestamp, row) in enumerate(solar_position.iterrows()):
            # 确保太阳高度角为正数，使用apparent_elevation字段
            solar_elevation = row.get('apparent_elevation', 90 - row['zenith'])
            
            result.append({
                "timestamp": timestamp.isoformat(),
                "solar_zenith": row['zenith'],
                "solar_azimuth": row['azimuth'],
                "solar_elevation": solar_elevation,
                "sunrise": row['sunrise'] if 'sunrise' in row else None,
                "sunset": row['sunset'] if 'sunset' in row else None
            })
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "date": date,
            "solar_positions": result
        }
        
    except Exception as e:
        logger.error(f"计算太阳位置失败: {e}")
        raise HTTPException(status_code=500, detail=f"计算太阳位置失败: {str(e)}")

@router.get("/irradiance/")
async def calculate_irradiance(
    latitude: float = Query(..., description="纬度", ge=-90, le=90),
    longitude: float = Query(..., description="经度", ge=-180, le=180),
    tilt: float = Query(30.0, description="倾角(度)", ge=0, le=90),
    azimuth: float = Query(180.0, description="方位角(度)", ge=0, le=360),
    date: str = Query(..., description="日期 (YYYY-MM-DD)")
):
    """计算斜面辐射"""
    try:
        from app.services.pv_calculator import PVCalculator
        
        calculator = PVCalculator(latitude=latitude, longitude=longitude)
        
        # 创建时间序列
        times = pd.date_range(
            start=f"{date} 00:00:00",
            end=f"{date} 23:59:59",
            freq='H'
        )
        
        # 计算斜面辐射
        irradiance = calculator.calculate_irradiance(
            times=times,
            tilt=tilt,
            azimuth=azimuth
        )
        
        # 转换为字典格式
        result = []
        for idx, (timestamp, row) in enumerate(irradiance.iterrows()):
            result.append({
                "timestamp": timestamp.isoformat(),
                "poa_global": row['poa_global'],
                "poa_direct": row['poa_direct'],
                "poa_diffuse": row['poa_diffuse']
            })
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "tilt": tilt,
            "azimuth": azimuth,
            "date": date,
            "irradiance_data": result
        }
        
    except Exception as e:
        logger.error(f"计算斜面辐射失败: {e}")
        raise HTTPException(status_code=500, detail=f"计算斜面辐射失败: {str(e)}")