# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PvSimilator is a photovoltaic (PV) system simulation software implementing terrain-aware backtracking strategies for single-axis trackers. It features 3D visualization of solar panel arrays with real-time sun tracking simulation.

## Common Commands

### Docker (Recommended for Running)
```bash
docker-compose up -d          # Start all services (backend on :8000, frontend on :3000)
docker-compose down           # Stop services
docker-compose ps             # Check service status
```

### Backend Development (Python/FastAPI)
```bash
cd backend
python -m venv venv
venv\Scripts\activate         # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Development (React/Vite)
```bash
cd frontend
npm install
npm run dev                   # Development server
npm run build                 # Production build
npm run lint                  # ESLint check
```

### Testing (Backend)
```bash
cd backend
python run_tests.py                    # All tests with coverage
python run_tests.py quick              # Quick tests without coverage
python run_tests.py test_xxx.py        # Run specific test file
```

## Architecture

### Backend Structure (FastAPI)
- `app/api/` - API route handlers (terrain, pv_systems, simulations, shading_optimized, weather, users)
- `app/core/` - Configuration, database connection, resilience utilities
- `app/models/` - SQLAlchemy ORM models (pv_system, simulation, user, weather, bay)
- `app/schemas/` - Pydantic request/response schemas
- `app/services/` - Business logic layer:
  - `terrain_backtracking.py` - Core terrain-aware backtracking algorithm
  - `ray_tracing.py` - Forward ray tracing for shading calculations
  - `pv_calculator.py` - Solar position and irradiance calculations
  - `terrain_service.py` - Terrain data loading and processing

### Frontend Structure (React/Three.js)
- `frontend/src/` - React components and pages
- Uses React Three Fiber for 3D visualization of solar arrays
- Ant Design for UI components
- ECharts/Recharts for data visualization

### Key Data Flow
1. Terrain data (Excel) → `terrain_service.py` → Database
2. Simulation request → `simulations.py` API → `terrain_backtracking.py` algorithm
3. Frontend requests layout → `terrain.py` API → 3D visualization

## Terrain Data Format

Excel files must contain columns:
- `table_id` - Tracker row ID
- `pile_index` - Pile index within row
- `coord_x`, `coord_y` - Horizontal coordinates
- `z_top`, `z_ground` - Elevation data
- `preset_type` - Component configuration (e.g., "1x14", "1x27")

## Key API Endpoints

- `GET /api/v1/terrain/layout` - Get terrain layout for visualization
- `POST /api/v1/simulations/` - Create new simulation
- `GET /api/v1/simulations/{id}` - Get simulation results
- API documentation available at `/docs` when backend is running

## Algorithm Notes

The terrain-aware backtracking algorithm (`terrain_backtracking.py`) implements:
- Forward ray tracing for shade detection
- Ground Coverage Ratio (GCR) calculations
- Slope compensation for shading margins
- Neighbor filtering (lateral 0.5-20m, axial <=250m)
- 20% axial distance decay factor

## Unity Project (3D Visualization)

### Project Structure
```
unity/My project/
├── Assets/
│   ├── Scenes/SampleScene.unity
│   ├── Scripts/
│   │   ├── SolarPanel/
│   │   │   ├── SolarPanelGenerator.cs    # 生成太阳能板阵列
│   │   │   ├── SolarPanelController.cs   # 控制面板旋转跟踪
│   │   │   └── SolarPanelGroup.cs        # 单行跟踪器组
│   │   ├── Terrain/
│   │   │   └── TerrainMeshGenerator.cs   # 地形网格生成
│   │   └── UI/
│   │       └── SimulationUI.cs           # UI控制
│   ├── Prefabs/
│   │   └── SolarPanel 2.prefab           # 太阳能板预制体
│   └── SolarPanel/Assets/
│       └── Materials/                    # 面板材质
```

### Solar Panel Prefab Structure (SolarPanel 2.prefab)
```
SolarPanel 2 (root) - 位于 Y=0 (扭力管位置)
├── Panel/
│   └── Solar_Panel1 (localPosition: Y=1.34, localRotation.x: 34.695°)  # 面板网格
├── Structure/
│   ├── Assembly/        # 扭力管 - 跟随面板旋转
│   └── Pole/
│       ├── Pole1/       # 主支撑杆 - 保持垂直不旋转
│       ├── Polecap/     # 杆帽 - 保持垂直不旋转
│       ├── G_1_1/, G_2_1/  # 支撑结构 - 保持垂直不旋转
│       └── ... (其他部件)
└── Rail1-6, G_1-4, Beam_Clamp_*  # 其他组件
```

### Rotation Mechanism (关键机制)
面板围绕扭力管(Assembly)旋转,支撑结构(Pole, Polecap等)保持垂直:

1. **层级结构**:
   ```
   Row_X (行容器, 不旋转)
   ├── PanelContainer_X_Y (面板容器, 旋转)
   │   └── SolarPanel 2(Clone) (预制体实例, 向下偏移 panelYOffset)
   │       └── Structure/Assembly (扭力管, 跟随旋转)
   └── Pole_X_Y (杆子容器, 不旋转)
       └── Pole1, Polecap, G_1_1, G_2_1 (支撑结构, 保持垂直)
   ```

2. **位置计算**:
   - `panelYOffset` = Solar_Panel1 的本地 Y 位置 (约 1.34)
   - 预制体实例向下偏移 `panelYOffset`, 使面板网格中心在旋转原点
   - 杆子容器位置 = 面板容器位置 - panelYOffset (扭力管实际位置)

3. **代码位置**:
   - `SolarPanelGenerator.cs:144-152` - 面板 Y 偏移计算
   - `SolarPanelGenerator.cs:194-228` - 杆子移动逻辑
   - `SolarPanelGroup.cs:64-87` - 旋转应用

### Unity MCP Tools
使用 Unity MCP 进行 Unity 编辑器交互:
- `manage_scene` - 场景层级查询
- `manage_gameobject` - GameObject 操作
- `read_console` - 控制台日志
- `manage_camera` - 相机控制和截图

### Key Findings (重要发现)
1. **预制体 Y 偏移**: `Solar_Panel1` 在预制体中位于 Y=1.34, 有 34.7° 初始倾斜
2. **旋转中心**: 面板围绕扭力管(Assembly)旋转, 不是面板几何中心
3. **杆子分离**: 只有 Pole1 等支撑结构移到不旋转容器, Assembly 保留在旋转容器内
4. **角度限制**: `maxAngle = 60f` 限制旋转角度在 ±60° 范围内
