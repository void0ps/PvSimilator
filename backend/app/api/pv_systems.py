from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.models.pv_system import PVSystem, PVModule, Inverter, Battery
from app.schemas.pv_system import (
    PVSystemCreate, PVSystemResponse, PVSystemUpdate,
    PVModuleCreate, PVModuleResponse,
    InverterCreate, InverterResponse,
    BatteryCreate, BatteryResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)

# 光伏系统相关接口

@router.post("/", response_model=PVSystemResponse)
async def create_pv_system(
    system: PVSystemCreate,
    db: Session = Depends(get_db)
):
    """创建光伏系统"""
    try:
        db_system = PVSystem(**system.dict())
        db.add(db_system)
        db.commit()
        db.refresh(db_system)
        return db_system
    except Exception as e:
        db.rollback()
        logger.error(f"创建光伏系统失败: {e}")
        raise HTTPException(status_code=500, detail="创建光伏系统失败")

@router.get("/", response_model=List[PVSystemResponse])
async def get_pv_systems(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取光伏系统列表"""
    systems = db.query(PVSystem).offset(skip).limit(limit).all()
    return systems

@router.get("/{system_id}", response_model=PVSystemResponse)
async def get_pv_system(
    system_id: int,
    db: Session = Depends(get_db)
):
    """获取特定光伏系统"""
    system = db.query(PVSystem).filter(PVSystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="光伏系统不存在")
    return system

@router.put("/{system_id}", response_model=PVSystemResponse)
async def update_pv_system(
    system_id: int,
    system_update: PVSystemUpdate,
    db: Session = Depends(get_db)
):
    """更新光伏系统"""
    db_system = db.query(PVSystem).filter(PVSystem.id == system_id).first()
    if not db_system:
        raise HTTPException(status_code=404, detail="光伏系统不存在")
    
    try:
        update_data = system_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_system, field, value)
        
        db.commit()
        db.refresh(db_system)
        return db_system
    except Exception as e:
        db.rollback()
        logger.error(f"更新光伏系统失败: {e}")
        raise HTTPException(status_code=500, detail="更新光伏系统失败")

@router.delete("/{system_id}")
async def delete_pv_system(
    system_id: int,
    db: Session = Depends(get_db)
):
    """删除光伏系统"""
    db_system = db.query(PVSystem).filter(PVSystem.id == system_id).first()
    if not db_system:
        raise HTTPException(status_code=404, detail="光伏系统不存在")
    
    try:
        db.delete(db_system)
        db.commit()
        return {"message": "光伏系统删除成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除光伏系统失败: {e}")
        raise HTTPException(status_code=500, detail="删除光伏系统失败")

# 光伏组件相关接口

@router.post("/{system_id}/modules", response_model=PVModuleResponse)
async def create_pv_module(
    system_id: int,
    module: PVModuleCreate,
    db: Session = Depends(get_db)
):
    """为光伏系统添加组件"""
    # 检查系统是否存在
    system = db.query(PVSystem).filter(PVSystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="光伏系统不存在")
    
    try:
        db_module = PVModule(**module.dict(), system_id=system_id)
        db.add(db_module)
        db.commit()
        db.refresh(db_module)
        return db_module
    except Exception as e:
        db.rollback()
        logger.error(f"添加光伏组件失败: {e}")
        raise HTTPException(status_code=500, detail="添加光伏组件失败")

@router.get("/{system_id}/modules", response_model=List[PVModuleResponse])
async def get_pv_modules(
    system_id: int,
    db: Session = Depends(get_db)
):
    """获取光伏系统的组件列表"""
    system = db.query(PVSystem).filter(PVSystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="光伏系统不存在")
    
    return system.modules

# 逆变器相关接口

@router.post("/{system_id}/inverters", response_model=InverterResponse)
async def create_inverter(
    system_id: int,
    inverter: InverterCreate,
    db: Session = Depends(get_db)
):
    """为光伏系统添加逆变器"""
    system = db.query(PVSystem).filter(PVSystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="光伏系统不存在")
    
    try:
        db_inverter = Inverter(**inverter.dict(), system_id=system_id)
        db.add(db_inverter)
        db.commit()
        db.refresh(db_inverter)
        return db_inverter
    except Exception as e:
        db.rollback()
        logger.error(f"添加逆变器失败: {e}")
        raise HTTPException(status_code=500, detail="添加逆变器失败")

@router.get("/{system_id}/inverters", response_model=List[InverterResponse])
async def get_inverters(
    system_id: int,
    db: Session = Depends(get_db)
):
    """获取光伏系统的逆变器列表"""
    system = db.query(PVSystem).filter(PVSystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="光伏系统不存在")
    
    return system.inverters

# 电池相关接口

@router.post("/{system_id}/batteries", response_model=BatteryResponse)
async def create_battery(
    system_id: int,
    battery: BatteryCreate,
    db: Session = Depends(get_db)
):
    """为光伏系统添加电池"""
    system = db.query(PVSystem).filter(PVSystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="光伏系统不存在")
    
    try:
        db_battery = Battery(**battery.dict(), system_id=system_id)
        db.add(db_battery)
        db.commit()
        db.refresh(db_battery)
        return db_battery
    except Exception as e:
        db.rollback()
        logger.error(f"添加电池失败: {e}")
        raise HTTPException(status_code=500, detail="添加电池失败")

@router.get("/{system_id}/batteries", response_model=List[BatteryResponse])
async def get_batteries(
    system_id: int,
    db: Session = Depends(get_db)
):
    """获取光伏系统的电池列表"""
    system = db.query(PVSystem).filter(PVSystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="光伏系统不存在")
    
    return system.batteries