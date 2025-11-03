# 执行计划表

| 步骤编号 | 状态 | 描述 | 产出文件/接口 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | ✅ 已完成 | 梳理企业提供的地形/桩位表字段，并形成数据规范 | `docs/data_spec.md` | 明确字段含义、命名映射、清洗流程 |
| 2 | ✅ 已完成 | 构建地形数据解析服务与 API (`/api/v1/terrain/layout`) | `backend/app/services/terrain_service.py`<br>`backend/app/api/terrain.py` | 支持缓存刷新、返回结构化桩点列表 |
| 3 | ✅ 已完成 | 编写测试脚本验证地形 API，并输出跟踪行几何统计 | `backend/tests/test_terrain_api.py` | 自动打印总行数、桩数、首行几何信息 |
| 4 | ✅ 已完成 | 构建跟踪行几何数据结构 (`TrackerRow`)、轴线方位/倾角计算 | `backend/app/services/tracker_geometry.py` | 为回溯与遮挡算法提供基础几何描述 |
| 5 | ✅ 已完成 | 开发地形感知回溯与遮挡算法（阶段 1：行间距、邻接关系、遮挡判据） | `backend/app/services/tracker_analysis.py`<br>`backend/app/services/terrain_backtracking.py` | 输出跟踪行邻接、行距、遮挡裕量与遮挡系数，为动态阴影分析奠定基础 |
| 6 | ✅ 已完成 | 将回溯/遮挡结果集成到 `PVCalculator`，输出动态姿态与阴影系数 | `backend/app/services/pv_calculator.py`<br>`backend/app/api/simulations.py` | 接入地形遮挡系数、提供 `/api/v1/simulations/{id}/shading` 接口，前端详情页可视化遮挡摘要与时序 |
| 7 | ✅ 已完成 | 前端 3D 场景接入真实数据、展示动态跟踪和阴影诊断 | `frontend/analysis/components/ThreeD/SolarPanel3D.jsx` | 通过地形 API 加载真实桩位，自动聚焦行数/桩点信息；遮挡详情通过模拟页展示 |
| 8 | ✅ 已完成 | 端到端联调与性能评估 | `docs/stage8_e2e_plan.md`<br>`docs/stage8_report.md` | 完成示例模拟、遮挡接口验证与初步性能记录，形成联调报告；发现遮挡时间戳与逆变器兼容性问题待后续阶段优化 |
| 9 | ⏳ 进行中 | Terrain-aware 遮挡算法增强 | `docs/stage9_algorithm_enhancement.md`<br>`backend/app/services/terrain_backtracking.py` | 已完成高/低坡度对比与功率验证，输出 `docs/stage9_report.md`；后续推进性能调优与逆变器兼容 |
| 10 | ⏳ 待开始 | 3D 场景升级与遮挡可视化 | `frontend/analysis/components/ThreeD/SolarPanel3D.jsx` 等 | 生成地形 mesh / height map，播放真实 backtracking 轨迹，支持遮挡热力图/动画 |
| 11 | ⏳ 待开始 | 后端健壮性与安全性改造 | `backend/app/services/terrain_service.py`、`simulations.py` 等 | 加入缓存刷新锁、异常重试、无数据回退、API 鉴权与速率限制 |
| 12 | ⏳ 待开始 | 数据接口优化 | 新增聚合/分页接口 | 避免遮挡数据一次返回过大，支持抽样/分段查询供前端选择加载 |
| 13 | ⏳ 待开始 | 自动化测试体系完善 | 后端 Pytest & 前端单测 | 补充 backtracking、邻接分析、API 集成测试及前端组件可视化验证脚本 |

> 更新日期：2025-11-03


