from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from statistics import mean
import logging
import asyncio
import pandas as pd

from app.core.database import get_db
from app.models.simulation import Simulation, SimulationResult
from app.models.pv_system import PVSystem
from app.schemas.simulation import SimulationCreate, SimulationResponse, SimulationUpdate
from app.services.pv_calculator import PVCalculator
from app.services.weather_service import WeatherService
from app.services.terrain_service import terrain_service
from app.services.tracker_geometry import build_tracker_rows
from app.services.tracker_analysis import find_row_neighbors
from app.services.terrain_backtracking import TerrainBacktrackingSolver

router = APIRouter()
logger = logging.getLogger(__name__)

async def run_simulation_task(simulation_id: int, db: Session):
    """后台运行模拟任务"""
    try:
        # 获取模拟配置
        simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not simulation:
            logger.error(f"模拟任务 {simulation_id} 不存在")
            return
        
        # 更新状态为运行中
        simulation.status = "running"
        simulation.progress = 10
        db.commit()
        
        # 获取光伏系统
        system = db.query(PVSystem).filter(PVSystem.id == simulation.system_id).first()
        if not system:
            simulation.status = "failed"
            db.commit()
            return
        
        # 创建计算器
        calculator = PVCalculator(
            latitude=system.latitude,
            longitude=system.longitude,
            altitude=system.altitude
        )
        
        # 获取天气数据
        weather_service = WeatherService()
        weather_df = await weather_service.get_weather_data(
            latitude=system.latitude,
            longitude=system.longitude,
            start_date=simulation.start_date.strftime("%Y-%m-%d"),
            end_date=simulation.end_date.strftime("%Y-%m-%d"),
            source=simulation.weather_source,
            time_resolution=simulation.time_resolution
        )
        
        # 检查是否使用了合成气象数据
        used_synthetic_data = False
        if weather_df is not None and not weather_df.empty:
            # 检查DataFrame属性中是否标记为使用了合成数据
            if hasattr(weather_df, 'attrs') and weather_df.attrs.get('used_synthetic_data', False):
                used_synthetic_data = True
        else:
            # 如果获取失败，使用合成数据
            logger.warning("气象数据获取失败，使用通用气象数据")
            weather_df = weather_service.generate_synthetic_data(
                latitude=system.latitude,
                longitude=system.longitude,
                start_date=simulation.start_date.strftime("%Y-%m-%d"),
                end_date=simulation.end_date.strftime("%Y-%m-%d")
            )
            used_synthetic_data = True
        
        # 如果使用了合成数据，更新模拟名称
        if used_synthetic_data and "（气象数据缺失）" not in simulation.name:
            simulation.name = f"{simulation.name}（气象数据缺失）"
            db.commit()
            logger.info(f"模拟任务 {simulation_id} 使用通用气象数据，已更新名称")
        
        simulation.progress = 30
        db.commit()
        
        # 准备时间序列
        times = pd.date_range(
            start=simulation.start_date,
            end=simulation.end_date,
            freq='H',
            tz='UTC'
        ).tz_convert(None)
        
        logger.info(f"时间序列长度: {len(times)}, 开始时间: {times[0]}, 结束时间: {times[-1]}")
        logger.info(f"原始天气数据长度: {len(weather_df)}")
        
        # 确保天气数据与时间序列匹配
        # 如果天气数据是日级的，需要转换为小时级
        weather_resolution = getattr(weather_df, 'attrs', {}).get('resolution') if hasattr(weather_df, 'attrs') else None

        if weather_resolution != 'hourly' and len(weather_df) < len(times):
            weather_df = weather_service.calculate_hourly_data(
                weather_df, 
                simulation.start_date.isoformat(), 
                simulation.end_date.isoformat(),
                simulation.time_resolution
            )
            logger.info(f"转换后天气数据长度: {len(weather_df)}")
        
        # 重新索引天气数据以匹配时间序列
        weather_df = weather_df.set_index('timestamp')
        if not isinstance(weather_df.index, pd.DatetimeIndex):
            weather_df.index = pd.to_datetime(weather_df.index)
        if weather_df.index.tz is not None:
            weather_df.index = weather_df.index.tz_convert(None)

        weather_df = weather_df.sort_index()
        weather_df = weather_df.reindex(times, method='ffill')
        logger.info(f"最终天气数据长度: {len(weather_df)}")
        
        # 计算太阳位置和辐射
        solar_position = calculator.calculate_solar_position(times)
        
        ghi_series = weather_df['ghi'] if 'ghi' in weather_df.columns else None
        dni_series = weather_df['dni'] if 'dni' in weather_df.columns else None
        dhi_series = weather_df['dhi'] if 'dhi' in weather_df.columns else None

        # 计算斜面辐射
        irradiance = calculator.calculate_irradiance(
            times=times,
            tilt=system.tilt_angle,
            azimuth=system.azimuth,
            ghi=ghi_series,
            dni=dni_series,
            dhi=dhi_series
        )

        irradiance = irradiance.copy()
        if not isinstance(irradiance.index, pd.DatetimeIndex):
            logger.warning("斜面辐射索引非DatetimeIndex，按模拟时间重建")
            irradiance.index = times[:len(irradiance)]
        elif irradiance.index.tz is not None:
            irradiance.index = irradiance.index.tz_convert(None)

        if irradiance.index.has_duplicates:
            logger.warning("斜面辐射时间索引存在重复，执行聚合")
            irradiance = irradiance.groupby(irradiance.index).mean()

        if len(irradiance) != len(times):
            logger.warning(f"斜面辐射数据长度({len(irradiance)})与时间序列({len(times)})不一致，执行重采样")
            irradiance = irradiance.reindex(times).interpolate(method='time').ffill().bfill()

        irradiance = irradiance.reindex(times).ffill().bfill()
        irradiance.index = times
        
        simulation.progress = 50
        db.commit()

        # 地形感知回溯遮挡分析
        shading_series = None
        shading_details = None
        if simulation.include_shading:
            try:
                layout = terrain_service.load_layout()
                tracker_rows = build_tracker_rows(layout)
                if tracker_rows:
                    neighbors = find_row_neighbors(tracker_rows)
                    solver = TerrainBacktrackingSolver(tracker_rows, neighbors)
                    backtracking_result = solver.compute_tracker_angles(
                        solar_position['apparent_zenith'],
                        solar_position['azimuth']
                    )
                    shading_df = backtracking_result.shading_factor
                    if not shading_df.empty:
                        weight_map = {
                            row.table_id: getattr(row, "span_length", None) or 1.0
                            for row in tracker_rows
                        }
                        common_columns = [col for col in shading_df.columns if col in weight_map]
                        if common_columns:
                            weights = pd.Series({col: weight_map[col] for col in common_columns})
                            shading_subset = shading_df[common_columns]
                            weighted_sum = shading_subset.mul(weights, axis=1).sum(axis=1)
                            weight_total = float(weights.sum()) if weights.sum() else None
                            if weight_total and weight_total > 0:
                                shading_series = weighted_sum / weight_total
                            else:
                                shading_series = shading_df.mean(axis=1)
                        else:
                            shading_series = shading_df.mean(axis=1)
                    else:
                        shading_series = pd.Series(1.0, index=irradiance.index)
                    shading_series = shading_series.reindex(irradiance.index).ffill().bfill().fillna(1.0)
                    shading_details = {
                        'mean_shading_multiplier': float(shading_series.mean()),
                        'min_shading_multiplier': float(shading_series.min()),
                        'max_shading_multiplier': float(shading_series.max()),
                        'tracker_row_count': len(tracker_rows)
                    }
                else:
                    logger.warning("Terrain layout未找到跟踪行，使用默认阴影配置。")
            except Exception as e:
                logger.error(f"地形感知遮挡计算失败，回退到默认阴影因子: {e}")
                shading_series = None
                shading_details = {
                    'error': str(e)
                }
        
        # 准备模块参数
        if system.modules:
            module = system.modules[0]  # 使用第一个模块
            module_params = {
                'pdc0': module.power_rated,
                'V_mp': module.voltage_mp or module.power_rated / (module.current_mp or 10),
                'I_mp': module.current_mp or module.power_rated / (module.voltage_mp or 40),
                'V_oc': module.voltage_oc or (module.voltage_mp or 40) * 1.2,
                'I_sc': module.current_sc or (module.current_mp or 10) * 1.1,
                'alpha_sc': module.temp_coeff_current,
                'beta_oc': module.temp_coeff_voltage,
                'gamma_pdc': module.temp_coeff_power,
                'cells_in_series': 72
            }
        else:
            # 使用默认参数
            module_params = {
                'pdc0': 400,
                'V_mp': 37.2,
                'I_mp': 10.75,
                'V_oc': 45.5,
                'I_sc': 11.35,
                'alpha_sc': 0.0005,
                'beta_oc': -0.003,
                'gamma_pdc': -0.004,
                'cells_in_series': 72
            }
        
        # 准备逆变器参数 - 使用pvlib兼容的SAPM格式
        if system.inverters:
            inverter = system.inverters[0]
            inverter_params = {
                'Paco': inverter.power_rated,  # 交流额定功率
                'Pdco': inverter.power_rated * 1.1,  # 直流额定功率
                'Vdco': inverter.voltage_dc_max or 400,  # 直流额定电压
                'Pso': inverter.power_rated * 0.02,  # 启动功率
                'C0': -0.000002,  # 曲线参数
                'C1': -0.0002,    # 曲线参数
                'C2': -0.005,     # 曲线参数
                'C3': 0.01,       # 曲线参数
                'Pnt': inverter.power_rated * 0.01  # 夜间功耗
            }
        else:
            inverter_params = {
                'Paco': 5000,     # 交流额定功率
                'Pdco': 5200,     # 直流额定功率
                'Vdco': 400,      # 直流额定电压
                'Pso': 100,       # 启动功率
                'C0': -0.000002,  # 曲线参数
                'C1': -0.0002,    # 曲线参数
                'C2': -0.005,     # 曲线参数
                'C3': 0.01,       # 曲线参数
                'Pnt': 50         # 夜间功耗50W
            }
        
        simulation.progress = 70
        db.commit()
        
        # 计算发电功率
        logger.info(f"准备计算发电功率: irradiance长度={len(irradiance)}, weather_df长度={len(weather_df)}")
        temperature_ambient = weather_df['temperature'] if 'temperature' in weather_df.columns else pd.Series(25.0, index=times)
        temperature_ambient = temperature_ambient.reindex(times).interpolate(method='time').ffill().bfill().fillna(25)
        
        power_data = calculator.calculate_pv_power(
            irradiance=irradiance,
            module_params=module_params,
            inverter_params=inverter_params,
            temperature_ambient=temperature_ambient,
            shading_factor=simulation.shading_factor if simulation.include_shading else 0.0,
            shading_factors=shading_series,
            soiling_loss=simulation.soiling_loss if simulation.include_soiling else 0.0,
            degradation_rate=simulation.degradation_rate if simulation.include_degradation else 0.0
        )

        power_data.index = times
        
        simulation.progress = 90
        db.commit()
        
        # 保存结果
        for pos, (timestamp, row) in enumerate(power_data.iterrows()):
            ts = times[pos] if pos < len(times) else timestamp
            if ts in temperature_ambient.index:
                temperature_value = temperature_ambient.loc[ts]
            else:
                temperature_value = temperature_ambient.iloc[-1] if len(temperature_ambient) > 0 else 25

            irradiance_row = irradiance.loc[ts] if ts in irradiance.index else None
            irradiance_global = float(irradiance_row['poa_global']) if irradiance_row is not None and pd.notna(irradiance_row['poa_global']) else None
            irradiance_direct = float(irradiance_row['poa_direct']) if irradiance_row is not None and pd.notna(irradiance_row['poa_direct']) else None
            irradiance_diffuse = float(irradiance_row['poa_diffuse']) if irradiance_row is not None and pd.notna(irradiance_row['poa_diffuse']) else None

            if hasattr(ts, 'to_pydatetime'):
                timestamp_datetime = ts.to_pydatetime()
            else:
                timestamp_datetime = pd.to_datetime(ts).to_pydatetime()
            
            result = SimulationResult(
                simulation_id=simulation_id,
                timestamp=timestamp_datetime,
                power_dc=float(row['dc_power']) if pd.notna(row['dc_power']) else None,
                power_ac=float(row['ac_power']) if pd.notna(row['ac_power']) else None,
                efficiency=row['efficiency'],
                irradiance_global=irradiance_global if irradiance_global is not None else 0,
                irradiance_direct=irradiance_direct if irradiance_direct is not None else None,
                irradiance_diffuse=irradiance_diffuse if irradiance_diffuse is not None else None,
                temperature_ambient=float(temperature_value) if pd.notna(temperature_value) else None,
                performance_ratio=row['efficiency'] * 100 if row['efficiency'] > 0 else 0
            )

            shading_multiplier_value = row.get('shading_multiplier', None)
            if shading_multiplier_value is not None and pd.notna(shading_multiplier_value):
                shading_multiplier_value = float(shading_multiplier_value)

            detailed_payload: Dict[str, Any] = {}
            if shading_multiplier_value is not None:
                detailed_payload['shading_multiplier'] = shading_multiplier_value
            if shading_series is not None and ts in shading_series.index:
                detailed_payload['terrain_shading_multiplier'] = float(shading_series.loc[ts])
            elif shading_multiplier_value is not None:
                detailed_payload['terrain_shading_multiplier'] = shading_multiplier_value
            if shading_details and pos == 0:
                detailed_payload['terrain_summary'] = shading_details
            if irradiance_global is not None:
                detailed_payload['poa_global'] = irradiance_global
            if irradiance_direct is not None:
                detailed_payload['poa_direct'] = irradiance_direct
            if irradiance_diffuse is not None:
                detailed_payload['poa_diffuse'] = irradiance_diffuse
            if pd.notna(row.get('ac_power')):
                detailed_payload['power_ac'] = float(row['ac_power'])

            if detailed_payload:
                result.detailed_data = detailed_payload
            db.add(result)
        
        # 更新模拟状态
        simulation.status = "completed"
        simulation.progress = 100
        db.commit()
        
        logger.info(f"模拟任务 {simulation_id} 完成")
        
    except Exception as e:
        logger.error(f"模拟任务 {simulation_id} 失败: {e}")
        simulation.status = "failed"
        db.commit()

@router.post("/", response_model=SimulationResponse)
async def create_simulation(
    simulation: SimulationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """创建模拟任务"""
    try:
        # 检查系统是否存在
        system = db.query(PVSystem).filter(PVSystem.id == simulation.system_id).first()
        if not system:
            raise HTTPException(status_code=404, detail="光伏系统不存在")
        
        db_simulation = Simulation(**simulation.dict())
        db.add(db_simulation)
        db.commit()
        db.refresh(db_simulation)
        
        # 在后台运行模拟
        background_tasks.add_task(run_simulation_task, db_simulation.id, db)
        
        return db_simulation
    except Exception as e:
        db.rollback()
        logger.error(f"创建模拟任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建模拟任务失败: {str(e)}")

@router.get("", response_model=List[SimulationResponse])
@router.get("/", response_model=List[SimulationResponse])
async def get_simulations(
    system_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取模拟任务列表"""
    query = db.query(Simulation)
    
    if system_id:
        query = query.filter(Simulation.system_id == system_id)
    
    simulations = query.offset(skip).limit(limit).all()
    return simulations

@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: int,
    db: Session = Depends(get_db)
):
    """获取特定模拟任务"""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="模拟任务不存在")
    return simulation

@router.get("/{simulation_id}/results")
async def get_simulation_results(
    simulation_id: int,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """获取模拟结果"""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="模拟任务不存在")
    
    results = db.query(SimulationResult).filter(
        SimulationResult.simulation_id == simulation_id
    ).offset(skip).limit(limit).all()
    
    return {
        "simulation": simulation,
        "results": results,
        "total_count": len(results)
    }


@router.get("/{simulation_id}/shading")
async def get_simulation_shading(
    simulation_id: int,
    db: Session = Depends(get_db),
    limit: Optional[int] = Query(None, description="返回记录数限制（分页）", ge=1, le=10000),
    offset: Optional[int] = Query(0, description="偏移量（分页）", ge=0),
    start_time: Optional[str] = Query(None, description="开始时间（ISO格式）"),
    end_time: Optional[str] = Query(None, description="结束时间（ISO格式）"),
    sample_rate: Optional[int] = Query(None, description="抽样率（每N条取1条）", ge=1, le=100)
):
    """获取模拟的遮挡数据，支持分页、时间过滤和抽样。
    
    Args:
        simulation_id: 模拟任务ID
        limit: 返回记录数限制（用于分页）
        offset: 偏移量（用于分页）
        start_time: 开始时间，ISO格式（如: 2025-11-01T00:00:00）
        end_time: 结束时间，ISO格式
        sample_rate: 抽样率，如sample_rate=5表示每5条取1条
        
    Returns:
        遮挡数据和摘要信息
    """
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="模拟任务不存在")

    if not simulation.include_shading:
        return {
            "simulation_id": simulation_id,
            "include_shading": False,
            "message": "该模拟未开启遮挡分析"
        }

    # 构建查询
    query = db.query(SimulationResult).filter(
        SimulationResult.simulation_id == simulation_id
    )
    
    # 时间范围过滤
    if start_time:
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            query = query.filter(SimulationResult.timestamp >= start_dt)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"start_time格式无效: {e}")
    
    if end_time:
        try:
            from datetime import datetime
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query = query.filter(SimulationResult.timestamp <= end_dt)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"end_time格式无效: {e}")
    
    # 获取总数（用于分页信息）
    total_count = query.count()
    
    # 应用排序
    query = query.order_by(SimulationResult.timestamp.asc())
    
    # 应用分页
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
    
    results = query.all()

    if not results:
        return {
            "simulation_id": simulation_id,
            "include_shading": True,
            "series": [],
            "summary": None,
            "pagination": {
                "total": total_count,
                "offset": offset or 0,
                "limit": limit,
                "returned": 0
            }
        }

    # 应用抽样（如果指定）
    if sample_rate and sample_rate > 1:
        results = [results[i] for i in range(0, len(results), sample_rate)]

    series: List[Dict[str, Any]] = []
    terrain_values: List[float] = []
    global_values: List[float] = []
    summary: Optional[Dict[str, Any]] = None

    for item in results:
        data = item.detailed_data or {}
        terrain_multiplier = data.get('terrain_shading_multiplier')
        general_multiplier = data.get('shading_multiplier')
        poa_global = data.get('poa_global', item.irradiance_global)
        power_ac = data.get('power_ac', item.power_ac)

        if terrain_multiplier is not None:
            terrain_values.append(float(terrain_multiplier))
        if general_multiplier is not None:
            global_values.append(float(general_multiplier))

        if summary is None and isinstance(data.get('terrain_summary'), dict):
            summary = data['terrain_summary']

        series.append({
            "timestamp": item.timestamp.isoformat(),
            "terrain_shading_multiplier": terrain_multiplier,
            "shading_multiplier": general_multiplier,
            "power_ac": float(power_ac) if power_ac is not None else None,
            "irradiance_global": float(poa_global) if poa_global is not None else None
        })

    if summary is None:
        summary = {}
        if terrain_values:
            summary["mean_terrain_shading"] = mean(terrain_values)
            summary["min_terrain_shading"] = min(terrain_values)
            summary["max_terrain_shading"] = max(terrain_values)
        if global_values:
            summary["mean_shading_multiplier"] = mean(global_values)
            summary["min_shading_multiplier"] = min(global_values)
            summary["max_shading_multiplier"] = max(global_values)

    return {
        "simulation_id": simulation_id,
        "include_shading": True,
        "series": series,
        "summary": summary,
        "count": len(series),
        "pagination": {
            "total": total_count,
            "offset": offset or 0,
            "limit": limit,
            "returned": len(series),
            "sample_rate": sample_rate
        }
    }

@router.get("/{simulation_id}/shading/aggregated")
async def get_shading_aggregated(
    simulation_id: int,
    db: Session = Depends(get_db),
    interval: str = Query("1H", description="聚合时间间隔（如: 1H=每小时, 1D=每天, 15T=每15分钟）"),
    metric: str = Query("mean", description="聚合指标（mean/min/max/median）")
):
    """获取聚合后的遮挡数据，适合大数据量场景。
    
    Args:
        simulation_id: 模拟任务ID
        interval: 时间聚合间隔（pandas frequency strings）
        metric: 聚合统计指标
        
    Returns:
        聚合后的遮挡数据
    """
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="模拟任务不存在")

    if not simulation.include_shading:
        return {
            "simulation_id": simulation_id,
            "include_shading": False,
            "message": "该模拟未开启遮挡分析"
        }

    # 获取所有结果
    results = db.query(SimulationResult).filter(
        SimulationResult.simulation_id == simulation_id
    ).order_by(SimulationResult.timestamp.asc()).all()

    if not results:
        return {
            "simulation_id": simulation_id,
            "include_shading": True,
            "series": [],
            "aggregation": {"interval": interval, "metric": metric}
        }

    # 转换为DataFrame进行聚合
    data_list = []
    for item in results:
        data = item.detailed_data or {}
        data_list.append({
            "timestamp": item.timestamp,
            "terrain_shading_multiplier": data.get('terrain_shading_multiplier'),
            "shading_multiplier": data.get('shading_multiplier'),
            "power_ac": data.get('power_ac', item.power_ac),
            "irradiance_global": data.get('poa_global', item.irradiance_global)
        })
    
    df = pd.DataFrame(data_list)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # 聚合
    metric_func = {
        'mean': 'mean',
        'min': 'min',
        'max': 'max',
        'median': 'median'
    }.get(metric, 'mean')
    
    try:
        aggregated = df.resample(interval).agg(metric_func)
        aggregated = aggregated.dropna(how='all')  # 移除全空行
        
        series = []
        for timestamp, row in aggregated.iterrows():
            series.append({
                "timestamp": timestamp.isoformat(),
                "terrain_shading_multiplier": float(row['terrain_shading_multiplier']) if pd.notna(row['terrain_shading_multiplier']) else None,
                "shading_multiplier": float(row['shading_multiplier']) if pd.notna(row['shading_multiplier']) else None,
                "power_ac": float(row['power_ac']) if pd.notna(row['power_ac']) else None,
                "irradiance_global": float(row['irradiance_global']) if pd.notna(row['irradiance_global']) else None
            })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"聚合失败: {str(e)}")
    
    return {
        "simulation_id": simulation_id,
        "include_shading": True,
        "series": series,
        "count": len(series),
        "aggregation": {
            "interval": interval,
            "metric": metric,
            "original_count": len(results),
            "reduction_ratio": f"{(1 - len(series)/len(results))*100:.1f}%"
        }
    }

@router.put("/{simulation_id}", response_model=SimulationResponse)
async def update_simulation(
    simulation_id: int,
    simulation_update: SimulationUpdate,
    db: Session = Depends(get_db)
):
    """更新模拟任务"""
    db_simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not db_simulation:
        raise HTTPException(status_code=404, detail="模拟任务不存在")
    
    try:
        update_data = simulation_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_simulation, field, value)
        
        db.commit()
        db.refresh(db_simulation)
        return db_simulation
    except Exception as e:
        db.rollback()
        logger.error(f"更新模拟任务失败: {e}")
        raise HTTPException(status_code=500, detail="更新模拟任务失败")

@router.delete("/{simulation_id}")
async def delete_simulation(
    simulation_id: int,
    db: Session = Depends(get_db)
):
    """删除模拟任务"""
    db_simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not db_simulation:
        raise HTTPException(status_code=404, detail="模拟任务不存在")
    
    try:
        # 删除相关结果
        db.query(SimulationResult).filter(
            SimulationResult.simulation_id == simulation_id
        ).delete()
        
        db.delete(db_simulation)
        db.commit()
        return {"message": "模拟任务删除成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除模拟任务失败: {e}")
        raise HTTPException(status_code=500, detail="删除模拟任务失败")