# 光伏仿真软件 (PV Simulator)

专业的光伏系统仿真软件，支持地形感知的单轴跟踪器回溯策略。

## 功能特性

- 🌞 **3D可视化**：支持大规模组件（18,000+）的实时3D渲染
- 📊 **地形感知回溯**：基于前向光线追踪的地形感知回溯算法
- 🗺️ **真实地形支持**：支持从Excel文件加载真实地形和桩位数据
- ⚡ **高性能**：优化的API响应时间和数据压缩
- 🐳 **Docker支持**：完整的Docker Compose部署方案

## 快速开始

### 使用Docker（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 停止服务
docker-compose down
```

访问：
- 前端：http://localhost:3000
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

### 本地开发

#### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 前端

```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
PvSimilator/
├── backend/          # FastAPI后端
│   ├── app/
│   │   ├── api/      # API路由
│   │   ├── models/   # 数据模型
│   │   ├── services/ # 业务逻辑
│   │   └── schemas/  # Pydantic模式
│   └── tests/        # 测试文件
├── frontend/         # React前端
│   └── analysis/     # 分析模块
├── docs/             # 项目文档
└── docker-compose.yml # Docker编排配置
```

## 数据准备

将地形数据Excel文件（`带坡度地形数据.xlsx`）放置在项目根目录。

文件应包含以下列：
- `table_id`: 跟踪器排ID
- `pile_index`: 桩位索引
- `coord_x`, `coord_y`: 坐标
- `z_top`, `z_ground`: 高程
- `preset_type`: 组件配置（如 "1x14", "1x27"）

## API文档

启动后端后，访问 http://localhost:8000/docs 查看完整的API文档。

主要端点：
- `GET /api/v1/terrain/layout` - 获取地形布局
- `GET /api/v1/simulations/` - 获取仿真列表
- `POST /api/v1/simulations/` - 创建新仿真

## 技术栈

- **后端**: FastAPI, SQLAlchemy, SQLite
- **前端**: React, Three.js, Ant Design
- **部署**: Docker, Docker Compose, Nginx

## 开发指南

### 运行测试

```bash
cd backend
python run_tests.py
```

### 代码规范

- Python: 遵循PEP 8
- JavaScript: 使用ESLint配置

## 许可证

[添加许可证信息]

## 贡献

欢迎提交Issue和Pull Request！

## 相关文档

- [Docker部署指南](DOCKER-SETUP.md)
- [故障排除](DOCKER-TROUBLESHOOTING.md)
- [完整文档](docs/)

