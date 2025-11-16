# 算法验证展示组件

## 📋 功能说明

展示Terrain-Aware Backtracking算法的验证结果，对比有/无回溯的效果差异，验证与论文的一致性。

## 🎯 核心功能

### 1. 效果对比标签页
- 关键改进指标卡片（能量损失、遮挡时长、遮挡事件）
- 详细指标对比表格
- 可视化对比柱状图

### 2. 时间序列分析标签页
- 功率输出对比曲线（典型一天）
- 遮挡裕度对比

### 3. 论文验证标签页
- 能量损失验证
- 回溯算法效果验证
- GCR相关性验证
- 最终验证结论

## 🚀 集成方法

### 方法1：添加到主路由（推荐）

在 `frontend/analysis/App.jsx` 中添加路由：

```jsx
import AlgorithmValidation from './components/AlgorithmValidation';

// 在路由配置中添加
<Route path="/validation" element={<AlgorithmValidation />} />
```

### 方法2：添加到导航菜单

在主导航中添加菜单项：

```jsx
<Menu.Item key="validation" icon={<ExperimentOutlined />}>
  <Link to="/validation">算法验证</Link>
</Menu.Item>
```

### 方法3：作为独立页面

可以直接访问路由 `/validation` 查看。

## 📊 数据来源

所有验证数据来自**阶段9报告**（`docs/stage9_report.md`）：

- 能量损失对比：15.2% vs 37.8%
- 遮挡时长对比：3.2h vs 8.5h
- 回溯效果：减少60%
- 论文范围验证：所有指标均在论文范围内

## 🛠️ 技术栈

- **React**: 组件框架
- **Ant Design**: UI组件库（Table, Card, Tabs等）
- **Recharts**: 图表库（LineChart, BarChart, AreaChart）
- **CSS**: 自定义样式

## 📦 依赖项

确保已安装以下依赖：

```bash
npm install antd recharts @ant-design/icons
```

如果已有这些依赖，无需重复安装。

## 🎨 样式说明

组件包含完整的CSS样式文件 `styles.css`，包括：
- 响应式设计（移动端适配）
- 打印样式优化
- Ant Design主题定制

## 📱 响应式支持

- ✅ 桌面端：完整功能和布局
- ✅ 平板端：自适应布局
- ✅ 手机端：简化布局，关键信息优先

## 🖨️ 打印支持

组件支持直接打印，打印时会：
- 隐藏导出按钮和导航
- 优化页面布局
- 避免内容截断

## 🔧 自定义扩展

### 添加新场景

在 `VALIDATION_DATA.scenarios` 中添加：

```javascript
high_gcr: {
  id: 'high_gcr',
  name: '高GCR场景',
  config: { backtrack: true, gcr: 0.50, slope: 5.0 },
  metrics: { energy_loss: 22.4, ... },
  color: '#f59e0b'
}
```

### 连接真实API

将 `VALIDATION_DATA` 替换为API调用：

```javascript
useEffect(() => {
  const fetchData = async () => {
    const response = await fetch('/api/v1/validation/compare');
    const data = await response.json();
    setValidationData(data);
  };
  fetchData();
}, []);
```

### 添加导出功能

实现 PDF 或 PNG 导出：

```javascript
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';

const exportToPDF = async () => {
  const element = document.querySelector('.algorithm-validation');
  const canvas = await html2canvas(element);
  const imgData = canvas.toDataURL('image/png');
  const pdf = new jsPDF();
  pdf.addImage(imgData, 'PNG', 0, 0);
  pdf.save('algorithm-validation.pdf');
};
```

## 🎯 使用场景

1. **开发验证**：验证算法实现是否正确
2. **客户演示**：向客户展示算法价值
3. **研究分析**：分析不同参数的影响
4. **文档生成**：导出验证报告

## 📝 注意事项

1. **数据准确性**：当前使用阶段9的真实验证数据
2. **时间序列**：时间序列数据为模拟数据，反映实际趋势
3. **论文对比**：基准数据来自论文的参考范围

## 🔗 相关文档

- 阶段9报告：`docs/stage9_report.md`
- 算法文档：`docs/stage9_algorithm_enhancement.md`
- 功能设计：`docs/ALGORITHM_VALIDATION_FEATURE.md`

## ✅ 完成清单

- [x] 核心组件实现
- [x] 三个标签页（效果对比、时间序列、论文验证）
- [x] 样式文件
- [x] 响应式设计
- [x] 打印支持
- [x] 使用文档
- [ ] 集成到主应用（待用户操作）
- [ ] 导出功能（可选）
- [ ] API集成（可选）

## 🎉 快速预览

启动应用后访问：`http://localhost:5173/validation`

---

> **创建日期**：2025-11-05  
> **版本**：v1.0  
> **状态**：✅ 开发完成，待集成



