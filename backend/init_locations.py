#!/usr/bin/env python3
"""
初始化位置数据到数据库
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.weather import Location

def init_locations():
    """初始化位置数据"""
    
    # 创建会话
    db: Session = SessionLocal()
    
    try:
        # 检查是否已有数据
        existing_count = db.query(Location).count()
        if existing_count > 0:
            print(f"数据库中已有 {existing_count} 个位置，跳过初始化")
            return
        
        # 创建示例位置数据
        locations_data = [
            {
                "name": "北京",
                "latitude": 39.9042,
                "longitude": 116.4074,
                "altitude": 43.5,
                "timezone": "Asia/Shanghai",
                "country": "中国",
                "province": "北京",
                "city": "北京",
                "weather_source": "nasa_sse",
                "data_available": True
            },
            {
                "name": "上海",
                "latitude": 31.2304,
                "longitude": 121.4737,
                "altitude": 4.5,
                "timezone": "Asia/Shanghai",
                "country": "中国",
                "province": "上海",
                "city": "上海",
                "weather_source": "nasa_sse",
                "data_available": True
            },
            {
                "name": "广州",
                "latitude": 23.1291,
                "longitude": 113.2644,
                "altitude": 43.0,
                "timezone": "Asia/Shanghai",
                "country": "中国",
                "province": "广东",
                "city": "广州",
                "weather_source": "nasa_sse",
                "data_available": True
            },
            {
                "name": "深圳",
                "latitude": 22.5431,
                "longitude": 114.0579,
                "altitude": 18.0,
                "timezone": "Asia/Shanghai",
                "country": "中国",
                "province": "广东",
                "city": "深圳",
                "weather_source": "nasa_sse",
                "data_available": True
            },
            {
                "name": "杭州",
                "latitude": 30.2741,
                "longitude": 120.1551,
                "altitude": 41.7,
                "timezone": "Asia/Shanghai",
                "country": "中国",
                "province": "浙江",
                "city": "杭州",
                "weather_source": "nasa_sse",
                "data_available": True
            }
        ]
        
        # 添加位置数据
        for loc_data in locations_data:
            location = Location(**loc_data)
            db.add(location)
        
        # 提交事务
        db.commit()
        print(f"成功初始化 {len(locations_data)} 个位置数据")
        
        # 验证
        count = db.query(Location).count()
        print(f"数据库中现在有 {count} 个位置")
        
    except Exception as e:
        db.rollback()
        print(f"初始化位置数据失败: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_locations()

