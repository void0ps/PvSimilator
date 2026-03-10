# AGENTS.md - PV Simulator Codebase Guide

Essential information for agentic coding agents working in this repository.

## Project Overview

Full-stack photovoltaic system simulation software with terrain-aware backtracking for single-axis trackers:
- **Backend**: FastAPI (Python) with SQLAlchemy ORM
- **Frontend**: React + Three.js + Ant Design
- **Database**: SQLite (dev) / PostgreSQL (prod)

## Build/Lint/Test Commands

### Backend (Python/FastAPI)

```bash
cd backend

# Development server
python main.py                    # Port 8001 with hot reload
uvicorn app.main:app --reload --port 8000

# Tests
python run_tests.py               # All tests with coverage
python run_tests.py quick         # Fast test, stops on first failure
python run_tests.py test_xxx.py   # Run specific test file

# Pytest commands
pytest tests/test_terrain_service.py::TestTerrainServiceRobustness -v  # Test class
pytest tests/test_terrain_service.py::TestTerrainServiceRobustness::test_method -v  # Test method
pytest tests/ -v -s               # Show print output
pytest tests/ --lf                # Run only failed tests
pytest tests/ --cov=app --cov-report=html --cov-report=term  # Coverage report

pip install -r requirements.txt   # Install dependencies
```

### Frontend (React/Vite)

```bash
cd frontend

npm install                       # Install dependencies
npm run dev                       # Development server (port 3000)
npm run build                     # Production build
npm run lint                      # Lint check
npm run lint:fix                  # Lint and auto-fix
```

### Docker

```bash
docker-compose up -d              # Start all services
docker-compose ps                 # View status
docker-compose down               # Stop services
```

## Code Style Guidelines

### Python (Backend)

#### Imports
Order: standard library → third-party → local (separated by blank lines)
```python
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String

from app.core.config import settings
from app.services.terrain_service import terrain_service
```

#### Naming
- **Classes**: PascalCase (`TerrainService`, `SimulationResponse`)
- **Functions/Variables**: snake_case (`load_layout`, `file_path`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`)
- **Private**: prefix underscore (`_cache_version`)

#### Type Hints
Always use type hints. Use `Optional[T]` for optional, `List[T]`, `Dict[K, V]` from typing.
```python
def load_layout(self, refresh: bool = False) -> Dict[str, Any]:
    ...
```

#### Docstrings
Triple-quoted with Args, Returns, Raises sections for public methods.

#### Error Handling
Use specific exceptions, log before raising HTTP exceptions:
```python
try:
    data = terrain_service.load_layout(refresh=refresh)
except FileNotFoundError as exc:
    raise HTTPException(status_code=404, detail=str(exc))
except Exception as exc:
    logger.exception("Failed: %s", exc)
    raise HTTPException(status_code=500, detail="Failed")
```

#### Logging
```python
logger = logging.getLogger(__name__)
logger.info(f"Message: {value}")
logger.exception("Error: %s", exc)  # Includes stack trace
```

#### Pydantic Schemas
Suffix: `Base`, `Create`, `Update`, `Response`. Use `Field` for validation.

### JavaScript/React (Frontend)

#### Imports
Order: React → third-party → local components/services
```javascript
import React, { useState, useEffect } from 'react'
import { Layout, Card } from 'antd'
import Header from './components/Layout/Header'
import { systemsApi } from './services/api'
```

#### Naming
- **Components/Files**: PascalCase (`Dashboard.jsx`)
- **Functions/Variables**: camelCase (`fetchSystems`)
- Group related API calls: `systemsApi.getSystems()`, `systemsApi.createSystem(data)`

#### Components
Functional components with hooks. Async/await for API calls.
```javascript
function App() {
  const [systems, setSystems] = useState([])
  useEffect(() => { fetchSystems() }, [])
  // ...
}
```

### Testing Conventions

- **Files**: `test_<module>.py` in `backend/tests/`
- **Classes**: `Test<FeatureName>`
- **Methods**: `test_<behavior>`
- Skip if data unavailable: `pytest.skip("File not found")`
- Use mocks: `@patch('app.services.module.Class.method')`

## Project Structure

```
PvSimilator/
├── backend/
│   ├── app/
│   │   ├── api/           # API route handlers
│   │   ├── core/          # Config, database
│   │   ├── models/        # SQLAlchemy ORM
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   ├── tests/
│   ├── main.py
│   └── run_tests.py
├── frontend/
│   ├── analysis/          # React app (components/, pages/, services/)
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
└── 带坡度地形数据.xlsx      # Terrain data file
```

## Key Patterns

1. **Service Layer**: Business logic in `services/`, not API routes
2. **Repository**: Database operations through SQLAlchemy models
3. **Schema Validation**: Pydantic for all API inputs/outputs
4. **Dependency Injection**: `get_db()` generator for sessions
5. **Caching**: Services implement caching with invalidation

## Notes

- Chinese comments used for business domain context
- Terrain file path resolved from project root or `WORKSPACE_ROOT` env var
- API endpoints support trailing slash variants
- Frontend Vite alias `@` maps to `./analysis`
