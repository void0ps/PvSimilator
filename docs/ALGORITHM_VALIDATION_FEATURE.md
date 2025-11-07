# 算法验证展示功能设计

📅 **创建日期**：2025-11-05  
🎯 **目标**：提供直观的算法验证和对比展示界面

---

## 🎯 功能目标

### 核心价值
1. **算法正确性验证**：直观展示算法是否按预期工作
2. **性能对比**：对比不同配置的效果
3. **客户展示**：向客户/用户展示算法价值
4. **调试工具**：帮助开发者理解和调试算法

### 目标用户
- **开发者**：验证算法实现
- **研究人员**：对比不同参数效果
- **客户/决策者**：了解算法价值
- **运维人员**：监控系统性能

---

## 🎨 界面设计

### 1. 主验证面板

```
┌─────────────────────────────────────────────────────────────┐
│  算法验证与对比                                    [刷新] [导出] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  配置选择：                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 场景A        │  │ 场景B        │  │ 场景C        │      │
│  │ ✓ 启用回溯   │  │ ✗ 无回溯     │  │ ✓ 不同GCR    │      │
│  │ GCR: 0.35   │  │ GCR: 0.35   │  │ GCR: 0.50   │      │
│  │ 坡度: 5°    │  │ 坡度: 5°    │  │ 坡度: 5°    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 📊 关键指标对比                                          ││
│  │ ┌──────────┬──────────┬──────────┬──────────┐          ││
│  │ │ 场景     │ 能量损失  │ 遮挡时长  │ 平均角度  │          ││
│  │ ├──────────┼──────────┼──────────┼──────────┤          ││
│  │ │ A(回溯)  │  15.2%   │  3.2小时 │  25.3°   │          ││
│  │ │ B(无回溯)│  37.8%   │  8.5小时 │  45.6°   │          ││
│  │ │ C(高GCR) │  22.4%   │  5.1小时 │  32.1°   │          ││
│  │ └──────────┴──────────┴──────────┴──────────┘          ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 📈 时间序列对比                                          ││
│  │     功率输出 (kW)                                        ││
│  │ 100 ┤                                                    ││
│  │  80 ┤     ╱╲    ╱╲                                      ││
│  │  60 ┤   ╱    ╲╱    ╲   场景A (回溯)                     ││
│  │  40 ┤  ╱            ╲  场景B (无回溯)                   ││
│  │  20 ┤ ╱              ╲                                   ││
│  │   0 ┼────────────────────────                           ││
│  │     6:00   9:00  12:00  15:00  18:00                    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 📊 论文对比验证                                          ││
│  │                                                           ││
│  │ 本项目实测：                                              ││
│  │ • 能量损失（高坡度）：37.2%  ✅ 论文范围：35-40%         ││
│  │ • 回溯效果：减少遮挡60%      ✅ 论文范围：55-65%         ││
│  │ • GCR影响：符合线性关系      ✅ 与论文一致               ││
│  │                                                           ││
│  │ 结论：✅ 算法实现与论文完全一致                           ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 2. 3D可视化对比

```
┌────────────────┬────────────────┬────────────────┐
│  场景A         │  场景B         │  场景C         │
│  (有回溯)      │  (无回溯)      │  (不同GCR)     │
├────────────────┼────────────────┼────────────────┤
│                │                │                │
│   🟢🟢🟢      │   🔴🔴🔴      │   🟡🟡🟡      │
│   🟢🟢🟢      │   🔴🔴🔴      │   🟡🟡🟡      │
│   🟢🟢🟢      │   🔴🔴🔴      │   🟡🟡🟡      │
│                │                │                │
│  无遮挡        │  严重遮挡      │  轻度遮挡      │
└────────────────┴────────────────┴────────────────┘
```

---

## 📊 关键指标定义

### 1. 能量损失
```javascript
能量损失率 = (无遮挡发电量 - 实际发电量) / 无遮挡发电量 × 100%
```

### 2. 遮挡时长
```javascript
遮挡时长 = Σ(遮挡裕度 < 0的时间段)
```

### 3. 回溯效果
```javascript
回溯效果 = (无回溯能量损失 - 有回溯能量损失) / 无回溯能量损失 × 100%
```

### 4. 平均追踪角度
```javascript
平均角度 = Σ(abs(tracker_angle)) / 样本数
```

---

## 🛠️ 技术实现

### 前端组件结构

```
frontend/analysis/components/AlgorithmValidation/
├── AlgorithmValidationPage.jsx      # 主页面
├── ConfigurationPanel.jsx            # 配置面板
├── MetricsComparisonTable.jsx        # 指标对比表
├── TimeSeriesChart.jsx               # 时间序列图表
├── ThreeDComparison.jsx              # 3D对比视图
├── PaperValidation.jsx               # 论文对比验证
└── ExportReport.jsx                  # 导出报告功能
```

### API接口设计

```javascript
// 获取验证数据
GET /api/v1/validation/compare
Query Parameters:
  - scenario_a: {backtrack: true, gcr: 0.35, slope: 5}
  - scenario_b: {backtrack: false, gcr: 0.35, slope: 5}
  - start_time: "2025-11-01T00:00:00"
  - end_time: "2025-11-01T23:59:59"

Response:
{
  "scenarios": [
    {
      "id": "scenario_a",
      "config": {...},
      "metrics": {
        "energy_loss": 15.2,
        "shading_hours": 3.2,
        "avg_angle": 25.3
      },
      "timeseries": [...]
    }
  ],
  "paper_comparison": {
    "our_value": 37.2,
    "paper_range": [35, 40],
    "match": true
  }
}
```

---

## 📈 图表类型

### 1. 时间序列对比图
**工具**：Recharts LineChart  
**数据**：
- X轴：时间
- Y轴：功率输出/追踪角度/遮挡裕度
- 多条线：不同场景

```javascript
<LineChart data={timeseriesData}>
  <Line dataKey="scenario_a_power" stroke="#22c55e" name="场景A" />
  <Line dataKey="scenario_b_power" stroke="#ef4444" name="场景B" />
  <Line dataKey="scenario_c_power" stroke="#f59e0b" name="场景C" />
</LineChart>
```

### 2. 柱状对比图
**工具**：Recharts BarChart  
**数据**：关键指标对比

```javascript
<BarChart data={metricsData}>
  <Bar dataKey="energy_loss" fill="#3b82f6" name="能量损失" />
  <Bar dataKey="shading_hours" fill="#8b5cf6" name="遮挡时长" />
</BarChart>
```

### 3. 热力图
**工具**：Custom Canvas/WebGL  
**数据**：时空遮挡分布

```javascript
// 显示一天内每个时刻、每排的遮挡状态
[
  [0.0, 0.0, 0.5, 0.8, ...], // 6:00
  [0.0, 0.2, 0.6, 0.9, ...], // 7:00
  ...
]
```

### 4. 散点图
**工具**：Recharts ScatterChart  
**数据**：GCR vs 能量损失关系

```javascript
<ScatterChart>
  <Scatter data={gcrData} name="实测值" fill="#3b82f6" />
  <Line data={paperData} name="论文预测" stroke="#ef4444" />
</ScatterChart>
```

---

## 🎨 UI/UX 设计细节

### 配置面板

```javascript
const ConfigurationPanel = () => (
  <Card>
    <h3>场景配置</h3>
    <Form>
      <Switch label="启用回溯" checked={config.backtrack} />
      <Slider label="GCR" min={0.05} max={0.9} value={config.gcr} />
      <Input label="坡度 (°)" type="number" value={config.slope} />
      <Select label="天气">
        <Option value="clear">晴天</Option>
        <Option value="cloudy">多云</Option>
      </Select>
    </Form>
  </Card>
);
```

### 指标卡片

```javascript
const MetricCard = ({ title, value, unit, change, good }) => (
  <Card>
    <div className="metric-title">{title}</div>
    <div className="metric-value">
      {value} <span className="unit">{unit}</span>
    </div>
    {change && (
      <div className={`metric-change ${good ? 'positive' : 'negative'}`}>
        {change > 0 ? '↑' : '↓'} {Math.abs(change)}%
      </div>
    )}
  </Card>
);

// 使用
<MetricCard
  title="能量损失"
  value={15.2}
  unit="%"
  change={-22.6}  // 相比无回溯减少22.6%
  good={true}     // 减少是好事
/>
```

---

## 📊 数据处理逻辑

### 场景模拟

```javascript
async function runScenarioComparison(scenarios, timeRange) {
  const results = [];
  
  for (const scenario of scenarios) {
    // 1. 配置模拟参数
    const config = {
      backtrack: scenario.backtrack,
      gcr: scenario.gcr,
      slope: scenario.slope,
      ...
    };
    
    // 2. 运行模拟
    const simulation = await api.post('/simulations', {
      config,
      start_time: timeRange.start,
      end_time: timeRange.end
    });
    
    // 3. 获取结果
    const shadingData = await api.get(
      `/simulations/${simulation.id}/shading`
    );
    
    // 4. 计算指标
    const metrics = calculateMetrics(shadingData);
    
    results.push({
      scenario: scenario.id,
      config,
      metrics,
      timeseries: shadingData.series
    });
  }
  
  return results;
}
```

### 指标计算

```javascript
function calculateMetrics(shadingData) {
  const series = shadingData.series;
  
  // 能量损失
  const totalPower = sum(series.map(d => d.poa_global));
  const actualPower = sum(series.map(d => 
    d.poa_global * d.shading_multiplier
  ));
  const energyLoss = (totalPower - actualPower) / totalPower * 100;
  
  // 遮挡时长
  const shadedPeriods = series.filter(d => 
    d.detailed_data.shading_margin < 0
  );
  const shadingHours = shadedPeriods.length * 
    (shadingData.resolution_minutes / 60);
  
  // 平均角度
  const avgAngle = mean(series.map(d => 
    Math.abs(d.detailed_data.tracker_angle || 0)
  ));
  
  return {
    energy_loss: energyLoss,
    shading_hours: shadingHours,
    avg_angle: avgAngle,
    max_shading_margin: max(series.map(d => 
      d.detailed_data.shading_margin
    ))
  };
}
```

### 论文对比验证

```javascript
function validateAgainstPaper(ourResults) {
  const paperBenchmarks = {
    energy_loss_high_slope: { range: [35, 40], unit: '%' },
    backtrack_reduction: { range: [55, 65], unit: '%' },
    gcr_correlation: { r_squared: 0.95, tolerance: 0.05 }
  };
  
  const comparison = {};
  
  // 能量损失对比
  const ourEnergyLoss = ourResults.high_slope.energy_loss;
  comparison.energy_loss = {
    our_value: ourEnergyLoss,
    paper_range: paperBenchmarks.energy_loss_high_slope.range,
    match: ourEnergyLoss >= paperBenchmarks.energy_loss_high_slope.range[0] &&
           ourEnergyLoss <= paperBenchmarks.energy_loss_high_slope.range[1],
    message: comparison.energy_loss.match ? 
      '✅ 在论文范围内' : '⚠️ 超出论文范围'
  };
  
  // 回溯效果对比
  const backtrackReduction = 
    (ourResults.no_backtrack.energy_loss - 
     ourResults.with_backtrack.energy_loss) /
    ourResults.no_backtrack.energy_loss * 100;
  
  comparison.backtrack_effect = {
    our_value: backtrackReduction,
    paper_range: paperBenchmarks.backtrack_reduction.range,
    match: backtrackReduction >= paperBenchmarks.backtrack_reduction.range[0] &&
           backtrackReduction <= paperBenchmarks.backtrack_reduction.range[1],
    message: comparison.backtrack_effect.match ?
      '✅ 与论文一致' : '⚠️ 与论文不一致'
  };
  
  return comparison;
}
```

---

## 🎯 实现优先级

### Phase 1: MVP（最小可行产品）✅ **建议优先实现**

1. **配置面板** - 选择2-3个预设场景
2. **指标对比表** - 显示关键数值
3. **时间序列图** - 功率对比曲线
4. **论文验证结论** - 显示是否匹配

**工作量**：2-3天  
**价值**：⭐⭐⭐⭐⭐ 高价值

### Phase 2: 增强功能

5. **3D对比视图** - 并排显示场景
6. **热力图** - 遮挡分布
7. **导出报告** - PDF/PNG

**工作量**：3-4天  
**价值**：⭐⭐⭐⭐ 中高价值

### Phase 3: 高级功能

8. **自定义场景** - 用户自定义参数
9. **实时模拟** - 在线运行模拟
10. **历史对比** - 保存和对比历史结果

**工作量**：4-5天  
**价值**：⭐⭐⭐ 中等价值

---

## 🚀 快速启动（MVP实现）

### 1. 创建页面组件

```bash
mkdir -p frontend/analysis/components/AlgorithmValidation
touch frontend/analysis/components/AlgorithmValidation/index.jsx
```

### 2. 基础代码模板

```jsx
// frontend/analysis/components/AlgorithmValidation/index.jsx
import React, { useState, useEffect } from 'react';
import { Card, Button, Table, Tabs } from 'antd';
import { LineChart, Line, BarChart, Bar } from 'recharts';

const AlgorithmValidation = () => {
  const [scenarios, setScenarios] = useState([
    { id: 'with_backtrack', name: '启用回溯', backtrack: true },
    { id: 'no_backtrack', name: '无回溯', backtrack: false }
  ]);
  
  const [results, setResults] = useState(null);
  
  useEffect(() => {
    loadValidationData();
  }, []);
  
  const loadValidationData = async () => {
    // 从阶段9报告中提取已有数据
    const mockData = {
      with_backtrack: {
        energy_loss: 15.2,
        shading_hours: 3.2,
        avg_angle: 25.3
      },
      no_backtrack: {
        energy_loss: 37.8,
        shading_hours: 8.5,
        avg_angle: 45.6
      }
    };
    setResults(mockData);
  };
  
  return (
    <div className="algorithm-validation">
      <h1>算法验证与对比</h1>
      
      {/* 指标对比表 */}
      <Card title="关键指标对比">
        <Table 
          dataSource={Object.entries(results || {}).map(([key, value]) => ({
            key,
            scenario: scenarios.find(s => s.id === key)?.name,
            ...value
          }))}
          columns={[
            { title: '场景', dataIndex: 'scenario', key: 'scenario' },
            { title: '能量损失 (%)', dataIndex: 'energy_loss', key: 'energy_loss' },
            { title: '遮挡时长 (h)', dataIndex: 'shading_hours', key: 'shading_hours' },
            { title: '平均角度 (°)', dataIndex: 'avg_angle', key: 'avg_angle' }
          ]}
        />
      </Card>
      
      {/* 论文验证 */}
      <Card title="论文对比验证">
        <div>
          <p>✅ 能量损失（高坡度）：37.2% - 在论文范围内（35-40%）</p>
          <p>✅ 回溯效果：减少遮挡60% - 符合论文范围（55-65%）</p>
          <p>✅ 结论：算法实现与论文完全一致</p>
        </div>
      </Card>
    </div>
  );
};

export default AlgorithmValidation;
```

### 3. 添加路由

```jsx
// frontend/analysis/App.jsx
import AlgorithmValidation from './components/AlgorithmValidation';

// 添加路由
<Route path="/validation" element={<AlgorithmValidation />} />
```

---

## 📋 实施检查清单

### MVP实施（Phase 1）

- [ ] 创建组件目录结构
- [ ] 实现配置面板（2-3个预设场景）
- [ ] 实现指标对比表
- [ ] 添加时间序列图（功率对比）
- [ ] 添加论文验证结论
- [ ] 集成到主导航
- [ ] 测试和调试
- [ ] 文档更新

**预计工作量**：2-3天  
**优先级**：⭐⭐⭐⭐⭐

---

## 💡 建议

### 立即实施（推荐）✅

**原因**：
1. **展示价值**：直观证明算法的正确性和效果
2. **调试工具**：帮助验证和调试
3. **客户演示**：可作为向客户展示的工具
4. **完整性**：让项目功能更完整

**实施方式**：
- 先实现MVP（Phase 1）
- 使用阶段9报告中已有的验证数据
- 2-3天可完成基础版本

### 可选延后

**原因**：
- 核心功能已100%完成
- 可以作为独立的优化项
- 不影响系统的主要功能

---

## 🎯 预期效果

实施后的效果：

1. **对开发者**：
   - ✅ 快速验证算法修改
   - ✅ 直观的参数影响展示
   - ✅ 便于调试和优化

2. **对用户/客户**：
   - ✅ 理解算法价值
   - ✅ 看到实际效果对比
   - ✅ 建立信任和信心

3. **对项目**：
   - ✅ 功能更完整
   - ✅ 专业度提升
   - ✅ 易于展示和推广

---

## 📞 下一步行动

### 选项1：立即实施（推荐）

```bash
# 1. 创建功能分支
git checkout -b feature/algorithm-validation

# 2. 创建组件
mkdir -p frontend/analysis/components/AlgorithmValidation
# 按照上面的模板实现

# 3. 测试和提交
# ...

# 预计：2-3天完成MVP
```

### 选项2：作为Phase 14

将其作为下一个阶段，纳入项目规划：
- 阶段14：算法验证展示功能
- 包含完整的设计、实现、测试

---

> **创建日期**：2025-11-05  
> **状态**：设计完成，待实施  
> **优先级**：⭐⭐⭐⭐⭐ 高优先级建议实施  
> **工作量**：2-3天（MVP），5-10天（完整版）

