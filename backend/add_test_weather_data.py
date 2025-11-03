#!/usr/bin/env python3
"""
添加测试气象数据到数据库
"""

import sys
import os
from datetime import datetime, timedelta
import random

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.models.weather import WeatherData
from app.core.config import settings

def add_test_weather_data():
    """添加测试气象数据"""
    
    # 创建数据库引擎
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    
    # 创建会话
    with Session(engine) as session:
        
        # 生成过去30天的测试数据
        base_date = datetime.now()
        
        for i in range(30):
            # 每天生成24小时的数据
            for hour in range(24):
                timestamp = base_date - timedelta(days=i, hours=hour)
                
                # 生成随机气象数据
                temperature = round(random.uniform(15, 35), 1)  # 温度 15-35°C
                ghi = round(random.uniform(0, 1000), 1)  # 总辐射 0-1000 W/m²
                dni = round(random.uniform(0, 800), 1)  # 直接辐射 0-800 W/m²
                wind_speed = round(random.uniform(0, 10), 1)  # 风速 0-10 m/s
                
                # 创建气象数据记录
                weather_data = WeatherData(
                    location_id=1,  # 使用现有的位置ID
                    timestamp=timestamp,
                    temperature=temperature,
                    ghi=ghi,
                    dni=dni,
                    wind_speed=wind_speed,
                    solar_azimuth=round(random.uniform(0, 360), 2),  # 太阳方位角
                    solar_zenith=round(random.uniform(0, 90), 2),  # 太阳天顶角
                    data_source="test_data"  # 数据源标识
                )
                
                session.add(weather_data)
        
        # 提交事务
        session.commit()
        print(f"成功添加 {30 * 24} 条测试气象数据记录")

def check_existing_data():
    """检查现有数据"""
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    
    with Session(engine) as session:
        count = session.query(WeatherData).count()
        print(f"数据库中现有气象数据记录数: {count}")
        
        if count > 0:
            # 显示最新的5条记录
            latest_data = session.query(WeatherData).order_by(WeatherData.timestamp.desc()).limit(5).all()
            print("最新的5条记录:")
            for data in latest_data:
                print(f"  ID: {data.id}, 时间: {data.timestamp}, 温度: {data.temperature}°C, 总辐射: {data.ghi} W/m²")

if __name__ == "__main__":
    print("开始检查现有气象数据...")
    check_existing_data()
    
    print("\n开始添加测试气象数据...")
    add_test_weather_data()
    
    print("\n添加完成，检查最终数据...")
    check_existing_data()