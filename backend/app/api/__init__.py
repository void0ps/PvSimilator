from fastapi import APIRouter

# 导入子路由
from .pv_systems import router as pv_systems_router
from .simulations import router as simulations_router
from .terrain import router as terrain_router
from .weather import router as weather_router
from .users import router as users_router

# 创建主路由
router = APIRouter()

# 包含子路由
router.include_router(pv_systems_router, prefix="/systems", tags=["光伏系统"])
router.include_router(simulations_router, prefix="/simulations", tags=["仿真模拟"])
router.include_router(terrain_router, prefix="/terrain", tags=["地形与布置"])
router.include_router(weather_router, prefix="/weather", tags=["气象数据"])
router.include_router(users_router, prefix="/users", tags=["用户管理"])