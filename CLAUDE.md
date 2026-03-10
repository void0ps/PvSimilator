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
