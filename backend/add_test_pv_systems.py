#!/usr/bin/env python3
"""
添加测试光伏系统数据到数据库
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.models.pv_system import PVSystem, PVModule, Inverter, Battery
from app.core.config import settings

def add_test_pv_systems():
    """添加测试光伏系统数据"""
    
    # 创建数据库引擎 - 使用当前配置
    database_url = settings.database_url
    engine = create_engine(database_url, pool_pre_ping=True)
    
    # 创建会话
    with Session(engine) as session:
        
        # 创建测试光伏系统
        test_system = PVSystem(
            name="测试光伏系统1",
            description="这是一个测试光伏系统",
            latitude=31.2304,
            longitude=121.4737,
            altitude=10.0,
            capacity_kw=50.0,  # 50kW
            tilt_angle=30.0,  # 30度倾角
            azimuth=180.0,  # 朝南
            module_count=100,  # 100块组件
            string_count=10,  # 10个组串
            pitch=4.1  # 行间距
        )
        session.add(test_system)
        session.commit()
        session.refresh(test_system)
        
        # 为系统添加光伏组件
        test_module = PVModule(
            system_id=test_system.id,
            manufacturer="测试厂商",
            model="TSM-500W",
            power_rated=500.0,  # 500W
            voltage_mp=41.0,
            current_mp=12.2,
            voltage_oc=50.0,
            current_sc=13.0,
            temp_coeff_power=-0.35,
            length=2000,
            width=1000,
            weight=25.0
        )
        session.add(test_module)
        
        # 添加逆变器
        test_inverter = Inverter(
            system_id=test_system.id,
            manufacturer="测试逆变器厂商",
            model="INV-50KW",
            power_rated=50000.0,  # 50kW
            voltage_dc_max=1000.0,
            voltage_dc_min=150.0,
            current_dc_max=100.0,
            efficiency_max=98.5,
            efficiency_euro=97.5
        )
        session.add(test_inverter)
        
        # 添加电池（可选）
        test_battery = Battery(
            system_id=test_system.id,
            manufacturer="测试电池厂商",
            model="BAT-100KWH",
            capacity_kwh=100.0,  # 100kWh
            voltage_nominal=400.0,
            charge_rate_max=0.5,  # 0.5C
            discharge_rate_max=0.5,  # 0.5C
            cycle_life=6000,
            depth_of_discharge=0.8
        )
        session.add(test_battery)
        
        # 提交所有更改
        session.commit()
        
        print(f"成功添加测试光伏系统，系统ID: {test_system.id}")
        print(f"添加了 1 块光伏组件模板")
        print(f"添加了 1 台逆变器")
        print(f"添加了 1 套电池系统")

def check_existing_systems():
    """检查现有光伏系统"""
    # 使用当前配置
    database_url = settings.database_url
    engine = create_engine(database_url, pool_pre_ping=True)
    
    with Session(engine) as session:
        systems_count = session.query(PVSystem).count()
        
        # 使用更安全的方法检查光伏组件数量
        modules_count = 0
        try:
            # 先检查pv_modules表是否存在
            from sqlalchemy import text
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='pv_modules';"))
            if result.fetchone():
                # 如果表存在，使用原始SQL查询数量，避免SQLAlchemy模型字段问题
                result = session.execute(text("SELECT COUNT(*) FROM pv_modules;"))
                modules_count = result.scalar()
        except:
            modules_count = 0
        
        inverters_count = session.query(Inverter).count()
        batteries_count = session.query(Battery).count()
        
        print(f"数据库中现有光伏系统数: {systems_count}")
        print(f"光伏组件数: {modules_count}")
        print(f"逆变器数: {inverters_count}")
        print(f"电池系统数: {batteries_count}")
        
        if systems_count > 0:
            systems = session.query(PVSystem).all()
            print("现有光伏系统:")
            for system in systems:
                print(f"  ID: {system.id}, 名称: {system.name}, 容量: {system.capacity_kw}kW")

if __name__ == "__main__":
    print("开始检查现有光伏系统数据...")
    check_existing_systems()
    
    print("\n开始添加测试光伏系统数据...")
    add_test_pv_systems()
    
    print("\n添加完成，检查最终数据...")
    check_existing_systems()