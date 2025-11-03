# 阶段 8 端到端联调与性能评估报告

## 1. 环境与输入

- 数据来源：`add_test_pv_systems.py` & `add_test_weather_data.py` 生成的示例系统/天气。
- 数据库：`C:/Users/sansi/Desktop/PvSimilator/backend/pv_simulator.db`（SQLite），通过 `.env` 指定。
- 测试模拟：
  - `system_id`: 1 (`测试光伏系统1`)
  - `start_date`: 2025-11-01 00:00
  - `end_date`: 2025-11-03 23:00
  - 分辨率：小时级；启用 terrain-aware 遮挡，其他损失关闭。
- 样例记录：`docs/stage8_samples.csv`、`docs/stage8_samples/shading_1.json`。

## 2. 后端执行

| 项目 | 结果 |
| --- | --- |
| 表结构初始化 | `python -c "import sys; sys.path.append('backend'); ... Base.metadata.create_all..."` |
| 生成测试数据 | `python backend/add_test_pv_systems.py`，`python backend/add_test_weather_data.py` |
| 运行模拟 | `python -c "... asyncio.run(run_simulation_task(1, db))"` |
| 遮挡接口样本 | `python -c "... client.get('/api/v1/simulations/1/shading') ..."` |

**执行情况**
- `Simulation` 状态：`completed`，进度 100%。
- `SimulationResult` 条目：144。
- 遮挡接口响应时间（TestClient）：~0.027 s。
- 遮挡摘要：平均乘数 ~0.410，范围 0.109–0.870，行数 403。

**注意事项**
- 遮挡接口的 `series` 包含大量 `power_ac` / `irradiance_global` 为 `null`，当前仅返回遮挡乘数；可作为后续数据接口优化的参考。
- 时间序列中出现 `1970-01-01` 及秒级时间戳，源于遮挡序列重建时与整数索引合并导致的占位值，需要在后续算法增强阶段修复。
- pvlib 计算过程中出现 RuntimeWarning（Timestamp vs int），同样源于索引类型混用；建议在遮挡算法增强时统一索引类型。
- Sandia 逆变器函数因参数不兼容触发回退逻辑，当前示例仍能完成模拟，但会影响与真实逆变器参数的对比，需要后续在算法增强阶段解决（匹配 pvlib 版本参数或统一逆变器模型）。

## 3. 前端侧验证

- 已在 `Simulations.jsx` 中展示遮挡摘要与前 10 条记录，遮挡 JSON 可直接渲染。
- 由于当前环境未运行 Vite/浏览器调试，未记录真实渲染性能；建议后续在实际浏览器中补充 Performance 报告。
- 提前发现的异常（1970 时间戳、缺少功率值）已记录在问题列表中，前端可根据最终数据接口调整展现。

## 4. 性能与准确性初步结论

- 后端遮挡接口：单次请求耗时 <0.03s（TestClient），符合预期。
- 数据量：144 条记录，JSON 约 30KB，尚可接受；若周期更长需加入分页或聚合。
- 遮挡乘数趋势符合预期（凌晨/黄昏接近 0.39，正午趋近 0.11~0.27），说明 terrain-aware backtracking 粗略有效；但需解决前述索引与空值问题，才能进行更细致的准确性对比。

## 5. 后续优化建议

1. **修正遮挡序列索引**：在回溯求解器中，避免与整数索引混合；确保返回的时间戳全为真实时刻，移除 1970 占位。
2. **补充功率/辐照度信息**：在 `shading_factor` 计算后，将对应时刻的 AC 功率/POA 值一并写入，便于前端展示与分析。
3. **逆变器模型兼容性**：更新 Sandia 参数或选择 pvlib 支持的逆变器模型，避免回退到简化功率估算。
4. **前端性能实测**：上线实际浏览器测量（Performance 录制），记录遮挡卡片首屏渲染时间、内存占用。
5. **数据量控制**：为遮挡接口添加 `limit`/`offset` 或时间段过滤，减少长周期请求的 JSON 体积。

## 6. 里程碑更新

- `M1`：完成测试配置与模拟运行 ✅
- `M2`：遮挡接口样本与初步性能统计 ✅（仍需真实浏览器性能数据）
- `M3`：形成联调报告草稿 ✅（本文件）

后续进入阶段 9 的遮挡算法增强时，应优先解决索引与空值问题，以防影响准确度评估。


