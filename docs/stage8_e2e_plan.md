# 阶段 8：端到端联调与性能评估计划

## 目标

1. 使用企业提供的真实地形、布置和气象数据运行完整模拟，验证遮挡链路的准确性与稳定性。
2. 测量后端遮挡接口及前端遮挡展示的性能瓶颈，形成调优建议。

## 任务分解

| 序号 | 任务 | 负责人 | 产出 | 备注 |
| --- | --- | --- | --- | --- |
| 8.1 | 准备代表性模拟配置（时间范围 ≥ 72h，包含遮挡显著时段） | 后端 | `docs/stage8_samples.csv` | 记录系统 ID、时间段、备注 |
| 8.2 | 运行 `run_simulation_task` 并采集日志 | 后端 | 原始日志、执行耗时、遮挡处理警告 | 需要保留 `/api/v1/simulations/{id}/shading` 响应样例 |
| 8.3 | 前端联调遮挡展示并评估渲染性能 | 前端 | 浏览器 Performance 报告、关键截图/录屏 | 重点关注遮挡摘要、列表、3D 场景表现 |
| 8.4 | 汇总问题与调优建议 | 全栈 | `docs/stage8_report.md` | 包含问题列表、建议、责任人、计划完成时间 |

## 操作步骤

1. **数据准备**
   - 在 `docs/stage8_samples.csv` 中填写测试用模拟配置：系统 ID、开始/结束时间、遮挡特征说明。
   - 确认地形 Excel、PV 参数、天气数据均在最新状态。

2. **运行模拟**
   - 使用以下命令触发模拟任务，记录开始/结束时间：
     ```bash
     curl -X POST http://localhost:8000/api/v1/simulations -H "Content-Type: application/json" -d @payload.json
     ```
   - 监控后台日志，收集遮挡相关信息（`TerrainBacktrackingSolver`、`shading_multiplier` 等）。
   - 调用遮挡接口获取样例：
     ```bash
     curl http://localhost:8000/api/v1/simulations/{id}/shading > docs/stage8_samples/shading_{id}.json
     ```

3. **前端联调**
   - 在 `Simulations` 页面加载目标模拟，开启浏览器 Performance 录制（至少 10s）。
   - 验证遮挡摘要、前 10 条记录、3D 场景加载是否正确；截取关键界面。

4. **性能评估**
   - 记录 API 响应时间（平均/最大），前端遮挡卡片渲染耗时（首次加载 + 切换）。
   - 对比是否存在长尾请求、渲染卡顿、内存过载等问题。

5. **报告编制**
   - 在 `docs/stage8_report.md` 中整理：
     - 测试环境、输入场景列表
     - 遮挡准确性观察（包括误判样例截图）
     - 性能数据（表格 + 简述）
     - 优化建议及优先级
   - 更新执行计划及 TODO（标记完成项）。

## 资源/依赖

- 后端服务：`uvicorn main:app --reload`
- 前端服务：`npm run dev`（或部署环境）
- 浏览器：Chrome DevTools Performance 面板
- 数据目录：`docs/stage8_samples/`（需创建）

## 里程碑

- **M1**：完成 8.1~8.2，产出模拟结果与遮挡样例。
- **M2**：完成 8.3，生成前端性能记录。
- **M3**：完成 8.4，提交联调报告并更新 `docs/execution_plan.md`。


