"""优化的遮挡数据API - 支持分页和聚合"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel
import pandas as pd
import numpy as np
import pvlib

from app.core.database import get_db
from app.schemas.pagination import (
    PaginationParams,
    PaginatedResponse,
    TimeSeriesAggregationParams,
    ShadingDataAggregation,
    BaySummary,
    DetailedShadingData
)
from app.services.terrain_service import terrain_service
from app.services.tracker_geometry import build_tracker_rows
from app.services.tracker_analysis import find_row_neighbors
from app.services.bay_extractor import extract_all_bays
from app.services.terrain_backtracking import TerrainBacktrackingSolver, BacktrackingConfig

router = APIRouter()


class RealtimeTrackingRequest(BaseModel):
    """实时追踪请求"""
    latitude: float = 35.0
    longitude: float = -120.0
    timezone: float = -8.0
    datetime_utc: str  # ISO格式时间
    enable_backtracking: bool = True
    use_nrel_shading_fraction: bool = True


class RealtimeTrackingResponse(BaseModel):
    """实时追踪响应"""
    timestamp: str
    sun_position: Dict[str, float]
    tracking_data: Dict[str, Dict[str, float]]
    statistics: Dict[str, float]


@router.post("/realtime/tracking", response_model=RealtimeTrackingResponse)
async def get_realtime_tracking(request: RealtimeTrackingRequest):
    """
    实时获取追踪角度和遮挡数据（供Unity前端调用）

    后端做精确计算，前端做3D可视化
    """
    try:
        # 解析时间
        dt = pd.to_datetime(request.datetime_utc)
        times = pd.DatetimeIndex([dt])

        # 计算太阳位置
        solpos = pvlib.solarposition.get_solarposition(
            times, request.latitude, request.longitude
        )
        solar_zenith = solpos['apparent_zenith'].iloc[0]
        solar_azimuth = solpos['azimuth'].iloc[0]
        solar_elevation = 90 - solar_zenith

        # 加载地形数据
        layout = terrain_service.load_layout()
        rows = build_tracker_rows(layout)
        neighbors = find_row_neighbors(rows)

        # 配置回溯参数
        config = BacktrackingConfig(
            module_width=2.0,
            backtrack=request.enable_backtracking,
            use_nrel_shading_fraction=request.use_nrel_shading_fraction,
        )

        # 计算追踪角度
        solver = TerrainBacktrackingSolver(rows, neighbors, config)
        result = solver.compute_tracker_angles(
            pd.Series([solar_zenith]),
            pd.Series([solar_azimuth])
        )

        # 构建响应数据
        tracking_data = {}
        total_sf = 0
        min_sf = 1.0
        shaded_count = 0

        for table_id in result.angles.keys():
            angle = result.angles[table_id].iloc[0]
            sf = result.shading_factor[table_id].iloc[0]
            margin = result.shading_margin[table_id].iloc[0]

            tracking_data[str(table_id)] = {
                "angle": float(angle),
                "shading_factor": float(sf),
                "shading_margin": float(margin)
            }

            total_sf += sf
            if sf < min_sf:
                min_sf = sf
            if sf < 1.0:
                shaded_count += 1

        count = len(tracking_data)
        avg_sf = total_sf / count if count > 0 else 1.0

        return RealtimeTrackingResponse(
            timestamp=request.datetime_utc,
            sun_position={
                "zenith": float(solar_zenith),
                "azimuth": float(solar_azimuth),
                "elevation": float(solar_elevation)
            },
            tracking_data=tracking_data,
            statistics={
                "average_shading_factor": float(avg_sf),
                "min_shading_factor": float(min_sf),
                "shaded_row_count": shaded_count,
                "total_row_count": count,
                "energy_loss_percent": float((1 - avg_sf) * 100)
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实时追踪计算失败: {str(e)}")


@router.get("/realtime/tracking/current", response_model=RealtimeTrackingResponse)
async def get_current_tracking(
    latitude: float = Query(35.0, description="纬度"),
    longitude: float = Query(-120.0, description="经度"),
    enable_backtracking: bool = Query(True, description="是否启用回溯"),
    use_nrel_shading_fraction: bool = Query(True, description="是否使用NREL遮挡公式")
):
    """
    获取当前时刻的追踪数据（使用服务器当前时间）
    """
    request = RealtimeTrackingRequest(
        latitude=latitude,
        longitude=longitude,
        timezone=-8.0,
        datetime_utc=datetime.utcnow().isoformat(),
        enable_backtracking=enable_backtracking,
        use_nrel_shading_fraction=use_nrel_shading_fraction
    )
    return await get_realtime_tracking(request)


@router.get("/bays/summary", response_model=List[BaySummary])
async def get_bays_summary(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    db: Session = Depends(get_db)
):
    """
    获取Bay摘要列表（轻量级）
    
    返回所有bay的基本信息，不包含时间序列数据
    适用于初始加载和列表展示
    """
    try:
        # 加载地形数据
        layout = terrain_service.load_layout()
        rows = build_tracker_rows(layout)
        
        # 提取bays
        bays = extract_all_bays(rows)
        
        # 应用分页
        total = len(bays)
        paginated_bays = bays[skip:skip + limit]
        
        # 构建摘要
        summaries = [
            BaySummary(
                bay_id=bay.bay_id,
                table_id=bay.table_id,
                module_count=bay.module_count,
                avg_shading_factor=None  # 可以后续计算
            )
            for bay in paginated_bays
        ]
        
        return summaries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Bay摘要失败: {str(e)}")


@router.get("/bays/{bay_id}/details")
async def get_bay_details(
    bay_id: str,
    start_time: Optional[datetime] = Query(None, description="起始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db)
):
    """
    获取指定Bay的详细时间序列数据
    
    支持时间范围过滤，按需加载数据
    """
    try:
        # TODO: 从数据库或缓存中加载bay的时间序列数据
        # 这里返回示例数据
        return {
            "bay_id": bay_id,
            "message": "详细数据加载功能待实现",
            "start_time": start_time,
            "end_time": end_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Bay详情失败: {str(e)}")


@router.get("/shading/aggregated", response_model=List[ShadingDataAggregation])
async def get_aggregated_shading_data(
    aggregation: str = Query("hourly", description="聚合粒度: hourly, daily"),
    start_time: Optional[datetime] = Query(None, description="起始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db)
):
    """
    获取聚合的遮挡数据
    
    返回按时间聚合的遮挡统计数据，减少数据传输量
    适用于图表展示和趋势分析
    """
    try:
        # 读取验证数据作为示例
        import sys
        from pathlib import Path
        BACKEND_ROOT = Path(__file__).resolve().parents[2]
        angles_file = BACKEND_ROOT / "analysis" / "terrain_validation_angles.csv"
        
        if not angles_file.exists():
            raise HTTPException(
                status_code=404, 
                detail="遮挡数据文件不存在，请先运行验证脚本"
            )
        
        df = pd.read_csv(angles_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 时间范围过滤
        if start_time:
            df = df[df['timestamp'] >= start_time]
        if end_time:
            df = df[df['timestamp'] <= end_time]
        
        # 按聚合粒度分组
        if aggregation == "hourly":
            df['time_group'] = df['timestamp'].dt.floor('H')
        elif aggregation == "daily":
            df['time_group'] = df['timestamp'].dt.floor('D')
        else:
            df['time_group'] = df['timestamp'].dt.floor('H')
        
        # 聚合统计
        aggregated = df.groupby('time_group').agg({
            'shading_factor': ['mean', 'min', 'max'],
            'shading_margin_deg': 'mean',
            'table_id': 'count'
        }).reset_index()
        
        # 构建响应
        results = []
        for _, row in aggregated.iterrows():
            results.append(ShadingDataAggregation(
                timestamp=row['time_group'],
                mean_shading_factor=float(row[('shading_factor', 'mean')]),
                min_shading_factor=float(row[('shading_factor', 'min')]),
                max_shading_factor=float(row[('shading_factor', 'max')]),
                mean_shading_margin=float(row[('shading_margin_deg', 'mean')]),
                sample_count=int(row[('table_id', 'count')])
            ))
        
        return results
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聚合数据失败: {str(e)}")


@router.get("/shading/statistics")
async def get_shading_statistics(
    group_by: str = Query("slope", description="分组方式: slope, zone, hour"),
    db: Session = Depends(get_db)
):
    """
    获取遮挡统计摘要
    
    返回按不同维度聚合的统计数据
    适用于仪表板展示
    """
    try:
        import sys
        from pathlib import Path
        import json
        
        BACKEND_ROOT = Path(__file__).resolve().parents[2]
        summary_file = BACKEND_ROOT / "analysis" / "terrain_validation_shading_summary.json"
        
        if not summary_file.exists():
            raise HTTPException(
                status_code=404,
                detail="统计数据文件不存在"
            )
        
        with open(summary_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if group_by == "slope":
            # 按坡度分组
            return {
                "group_by": "slope",
                "groups": {
                    "high_slope": data.get("high", {}),
                    "low_slope": data.get("low", {})
                },
                "overall": {
                    "weighted_mean_shading_factor": data.get("weighted_mean_shading_factor"),
                    "total_table_count": data.get("total_table_count")
                }
            }
        else:
            return data
            
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")


@router.get("/performance/energy-loss")
async def get_energy_loss_summary(db: Session = Depends(get_db)):
    """
    获取能量损失摘要
    
    返回当前系统和Bay系统的能量损失对比
    """
    try:
        return {
            "baseline_system": {
                "energy_loss_pct": 9.85,
                "avg_shading_factor": 0.9015,
                "description": "当前修复后的基线系统（Row级别）"
            },
            "bay_system_weighted": {
                "energy_loss_pct": 6.60,
                "improvement_pct": 3.25,
                "recovery_rate": 33.0,
                "description": "Bay系统（加权平均模式）"
            },
            "bay_system_raytracing": {
                "energy_loss_pct": 3.64,
                "improvement_pct": 6.21,
                "recovery_rate": 63.0,
                "description": "Bay系统（加权平均+射线追踪）"
            },
            "time_of_day": {
                "midday": {"energy_loss_pct": 1.40, "period": "11:00-13:00"},
                "morning": {"energy_loss_pct": 21.86, "period": "<=08:00"},
                "evening": {"energy_loss_pct": 8.02, "period": ">=18:00"}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取能量损失数据失败: {str(e)}")

















