## 数据源概览

- **地形/桩位数据**：`带坡度地形数据.xlsx`
  - Sheet 默认工作表包含以 "PV area #..." 为标题的桩位表。
  - 第 1 行为项目描述；第 2 行给出字段标题；从第 3 行起为数据记录。
  - 表按 `Table` 分区（阵列行/子阵列），每行包含多个桩点（`Pile`）。

- **参考文献**：
  - `Modeling_Transposition_for_Single-Axis_Trackers_Using_Terrain-Aware_Backtracking_Strategies(2).pdf`
  - `Terrain_Aware_Backtracking_via_Forward_Ray_Tracing.pdf`

## 地形桩位表字段定义（依据第 2 行标题）

| 字段 | 说明 | 备注 |
| --- | --- | --- |
| `Table` | 阵列/分区编号 | 用于区分不同跟踪行或分区 |
| `Zone ID` | 分区标签 | 例如 `#1-1`，可用于匹配企业布置图中的子区域 |
| `Preset type` | 组件排布类型 | 如 `1x14`, `1x27` 等，表示单轴跟踪器每排组件数量 |
| `Pile` | 桩位序号 | 同一 Table 内按南北方向排列 |
| `X` | 投影坐标 X（米） | 结合 `Y` 构成平面坐标，可与地形网格统一坐标系 |
| `Y` | 投影坐标 Y（米） | — |
| `Lat` / `Long` | 桩位经纬度 | 与 GPS 数据一致，可用于可视化或验证 |
| `Z frame attach` | 框架连接点高程（米） | 组件支架顶部标高 |
| `Z terrain enter` | 地表高程（米） | 桩基进入地面的标高 |
| `Pile reveal length, m` | 桩露出长度（米） | `Z frame attach - Z terrain enter` 的派生量 |
| `Table slope, deg` | 表面坡度（度） | 沿跟踪轴方向的坡度估算 |
| `Slope delta, deg` | 坡度差（度） | 与设计坡度的偏差，部分记录为空 |
| `Table direction` | 阵列表面朝向 | 示例：`North facing`，用于确定初始朝向 |
| `Table fault` | 备注/告警 | 如空、或 `Filter out...` 等提示信息 |
| `Label` | 备注标识 | 少量记录出现 `XXXXXX` 等标签 |
| `Fill` | 施工说明 | 例如 `pile in the center of drainage`、`table slope beyond limit` |
| `Pile adjustment` | 调整建议 | （多数为空） |
| `Z frame attach (new)` / `Pile reveal length (new)` | 新方案数值 | 目前为空；若后续提供修正方案可填充 |
| `slope` / `slope delta` | 末尾统计列 | 当前未填值，可留作扩展 |

## 数据清洗与结构化计划

1. **跳过前两行非数据内容**，使用第 2 行作为列名。
2. **删除无用列**：`Unnamed: 21`, `slope`, `slope delta` 等为空列暂时不纳入模型。
3. **重命名核心字段**，例如：
   - `Table` → `table_id`
   - `Zone ID` → `zone_id`
   - `Preset type` → `preset_type`
   - `Pile` → `pile_index`
   - `X`/`Y` → `coord_x`/`coord_y`
   - `Z frame attach` → `z_top`
   - `Z terrain enter` → `z_ground`
   - `Pile reveal length, m` → `pile_reveal_m`
   - `Table slope, deg` → `table_slope_deg`
4. **按 `table_id` 分组**，将同一跟踪行的桩点排序后存入结构：
   ```json
   {
     "table_id": 1,
     "zone_id": "#1-1",
     "preset_type": "1x14",
     "piles": [
       {"index": 1, "x": 471280.719, "y": 716776.676, "z_top": 18.17906, "z_ground": 16.62868},
       ...
     ]
   }
   ```
5. **派生量**：
   - 计算桩间距、行方向向量用于遮挡分析。
   - 依据 `preset_type` 推导每行组件数量、跨度等几何参数。
6. **地形网格化**：
   - 若需转换为高度图，使用桩点 `(X, Y, Z terrain enter)` 插值生成规则网格。
   - 如企业后续提供完整 DEM，可直接替换。

## 待确认事项

- 是否存在多张 Sheet 或其他区域数据需要同步解析。
- 坐标系（`X/Y`）对应的具体投影（疑似新西兰坐标系，需向企业确认）。
- `Preset type` 对应的面板尺寸与排布规则是否固定，需要额外的尺寸参数表。
- `Table direction` 是否仅标记朝向，还是影响回溯算法初始姿态。


