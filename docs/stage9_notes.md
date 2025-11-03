# 阶段 9 问题分析笔记

## 1. 遮挡序列 & 数据状态

- 初始遮挡样本 `shading_1.json` 存在 `1970-01-01` 及秒级增量。
  - 原因：遮挡序列修正时混入 RangeIndex；保存 `SimulationResult` 时回落至 epoch。
  - 修复：`TerrainBacktrackingSolver` 统一索引、过滤邻居；`run_simulation_task` 使用 `times` 重建索引。最新 `stage9_shading_1.json` 首时间 `2025-11-01 00:00:00`，共 72 条。

- `power_ac` / `irradiance_global` 仍为空。
  - `poa_global` 已写入 `detailed_data`，但 `power_ac` 受逆变器模型影响仍返回 `None`；需在 9.4 中修复 Sandia 参数或改用其他模型。
- 已对天气/斜面辐射时间索引进行统一，避免 `Timestamp` 与 `int` 比较警告以及 144 vs 72 的长度错配。

## 2. 逆变器模型兼容性

- 错误：`pvlib.inverter.sandia()` 报 `unexpected keyword argument 'paco'`。
  - 可能原因：当前 pvlib 版本期望传入 Sandia 参数对象，而非显式关键字；或需使用 `pvlib.inverter.sandia(sandia_params, v_dc, p_dc)` 格式。
  - 回退：触发简化算法，不影响流程但失去精准度。
  - 修复建议：选择官方参数格式，或切换至 `pvlib.inverter.pvwatts`，统一逆变器效率模型。

## 3. 论文算法验证计划

| 论文指标 | 说明 | 项目数据来源 | 输出形式 |
| --- | --- | --- | --- |
| 遮挡裕量（Shading Margin） | `Terrain_Aware_Backtracking_via_Forward_Ray_Tracing` 中以角度衡量的安全余量 | `TerrainBacktrackingSolver` 返回的 `shading_margin`，需在求解器中导出 | 时序曲线 / 最小值表 |
| 跟踪角（Tracker Angle） | 与太阳几何、传统回溯角对比 | `compute_tracker_angles` 得到的 `tracker_angles`，需保存为每行时序 | 时序曲线，对比论文图 7/8 |
| 遮挡因子（Shading Factor） | 行间遮挡造成的有效辐照损失 | `shading_factor.mean(axis=1)` 已用于模拟 | 与论文示例场景的遮挡因子曲线对比 |
| 有效辐照度/功率提升 | 验证算法在实地数据下的利用率改善 | `SimulationResult` 中 `irradiance_*` / `power_ac`（含遮挡/不遮挡对比） | 条形图/统计表 |

### 验证案例挑选

1. **高坡度区域**：从企业数据中选择坡度>5°的行，验证论文强调的坡度敏感性。
2. **不规则邻距**：挑选邻距变化大的行对，测试遮挡裕量算法的自适应能力。
3. **边界行**：验证论文中“边界行必须考虑单侧遮挡”的处理，与求解器输出对照。

> 数据概览：`terrain_service` 当前解析出 403 条跟踪行，整体坡度约 0°～10.18°，示例行见 `backend/row_sample.json`。重点案例列表已输出至 `backend/case_candidates.json`（高坡度前 5 行：72/192/188/186/197；低坡度对照：22/184/214/331/373）。

### 数据准备

- 从 `terrain_service.load_layout()` 导出的 `tables` / `piles` 构造 `Case` 列表（含行ID、坡度、邻距、方位角）。
- 为每个案例选定代表日期（如春分/夏至/冬至）与全天小时序列，确保与论文测试条件匹配。
- 运行 `TerrainBacktrackingSolver` 并导出：`tracker_angles`、`shading_margin`、`shading_factor`；同时运行“不启用地形回溯”的基线获取对比数据。

### 输出与记录

- 在 `docs/stage9_report.md` 中新增“论文算法验证”章节，图表化呈现上述指标。
- 报告每个案例的最大遮挡裕量差、平均遮挡因子、AC 功率提升百分比，并附上与论文原图/表的对应说明。
- 若存在偏差，记录原因（数据尺度差异、论文假设不满足等）。
- 已生成首批对比数据：`backend/analysis/terrain_validation_angles.csv`，统计显示高坡度组平均遮挡因子约 0.69，低坡度对照约 0.91，满足“坡度越大遮挡越显著”的论文趋势。
  - 新增 `backend/scripts/analyze_shading_groups.py`，基于角度样本输出逐行遮挡摘要 `terrain_validation_shading_summary.json`，高坡度样本平均遮挡乘数 0.69、低坡度 0.91，加权平均约 0.80，提示需要按行归一化避免整体损失被少数行放大。
  - 功率回归脚本 `backend/scripts/run_terrain_validation_simulation.py` 支持多日重放（默认 2024-01-15～2024-01-17），最新结果：含地形遮挡 4.95 kWh，对照 7.81 kWh，行权重遮挡乘数 0.84（整场 field 均值 0.52）vs 1.00，三日损失约 36%～40%，并输出逐日能量/遮挡均值及单次运行耗时（约 11 s）。

## 3. 后续工作清单

- [x] 保留原索引并修正遮挡序列的索引运算。
- [x] 釐清遮挡乘数输出逻辑，补回 `poa` 数据（功率待逆变器修复）。
- [x] 改写逆变器模型调用，保证 pvlib 主路径可用（Sandia 失败时自动切换 pvwatts，并在输出为 0 时回退至效率模型）。
- [ ] 引入坡度修正、射线遮挡逻辑，替换现有线性剪裁。
- [ ] 性能评估与优化：记录算法在 403 行、三天模拟下的耗时，并考虑缓存。



