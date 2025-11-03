import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.terrain import TerrainLayoutResponse, TerrainTable
from app.services.terrain_service import terrain_service


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/layout", response_model=TerrainLayoutResponse)
async def get_terrain_layout(refresh: bool = Query(False, description="是否强制刷新缓存")):
    try:
        data = terrain_service.load_layout(refresh=refresh)
        return TerrainLayoutResponse(**data)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("获取地形布局失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取地形布局失败")


@router.get("/layout/{table_id}", response_model=TerrainTable)
async def get_terrain_table(table_id: int, refresh: bool = Query(False, description="是否强制刷新缓存")):
    try:
        table = terrain_service.get_table(table_id, refresh=refresh)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("获取地形桩位失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取地形桩位失败")

    if table is None:
        raise HTTPException(status_code=404, detail=f"未找到编号为 {table_id} 的跟踪行")

    return TerrainTable(**table)


