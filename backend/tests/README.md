# 后端测试指南

## 📋 测试文件列表

### 新增测试（阶段13）
1. **test_terrain_service.py** - 地形服务健壮性测试
   - 缓存刷新锁
   - 异常重试机制
   - 空数据回退
   - 并发测试

2. **test_terrain_backtracking_algorithm.py** - 遮挡算法核心测试
   - GCR计算
   - 邻居过滤
   - 遮挡角度计算
   - 坡度补偿
   - 沿轴距离衰减（20%）
   - 遮挡裕度计算

3. **test_api_shading_enhancements.py** - API增强功能测试
   - 分页功能
   - 时间过滤
   - 数据抽样
   - 聚合接口
   - 错误处理

### 现有测试
4. **test_terrain_api.py** - 地形API基础测试
5. **test_pv_calculator_shading.py** - PV计算器遮挡测试

## 🚀 运行测试

### 方法1：使用测试脚本（推荐）

```bash
cd backend

# 运行所有测试（带覆盖率报告）
python run_tests.py

# 快速测试（无覆盖率，遇错即停）
python run_tests.py quick

# 运行特定测试文件
python run_tests.py test_terrain_service.py

# 查看覆盖率报告（浏览器打开）
python run_tests.py coverage
```

### 方法2：直接使用pytest

```bash
cd backend

# 运行所有测试
pytest tests/ -v

# 带覆盖率报告
pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# 运行特定测试文件
pytest tests/test_terrain_service.py -v

# 运行特定测试类
pytest tests/test_terrain_service.py::TestTerrainServiceRobustness -v

# 运行特定测试方法
pytest tests/test_terrain_service.py::TestTerrainServiceRobustness::test_load_layout_with_valid_file -v

# 显示print输出
pytest tests/ -v -s

# 遇到第一个失败就停止
pytest tests/ -v -x

# 只运行失败的测试
pytest tests/ --lf

# 并行运行（需要安装pytest-xdist）
pytest tests/ -n auto
```

## 📊 测试覆盖率

### 目标
- **总体覆盖率**: ≥ 80%
- **核心模块覆盖率**: ≥ 90%
  - terrain_service.py
  - terrain_backtracking.py
  - simulations.py (遮挡相关接口)

### 查看覆盖率报告

```bash
# 命令行查看
pytest tests/ --cov=app --cov-report=term

# 生成HTML报告
pytest tests/ --cov=app --cov-report=html

# 在浏览器中打开
python run_tests.py coverage
# 或直接打开 htmlcov/index.html
```

## 🛠️ 测试环境设置

### 安装依赖

```bash
# 确保已安装测试依赖
pip install pytest pytest-cov pytest-asyncio

# 或从requirements.txt安装
pip install -r requirements.txt
```

### 数据准备

某些测试需要真实的地形数据文件：
- 文件路径：`带坡度地形数据.xlsx`（项目根目录）
- 如果文件不存在，相关测试会自动跳过

## 📝 测试编写指南

### 测试命名规范

```python
class TestFeatureName:
    """测试类：Test + 功能名"""
    
    def test_specific_behavior(self):
        """测试方法：test_ + 具体行为"""
        pass
```

### Fixture使用

```python
import pytest

@pytest.fixture
def sample_data():
    """测试数据fixture"""
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

### Mock使用

```python
from unittest.mock import Mock, patch

@patch('app.services.terrain_service.TerrainService._read_excel')
def test_with_mock(mock_read_excel):
    mock_read_excel.return_value = Mock()
    # 测试逻辑
```

## 🐛 常见问题

### Q1: 测试运行很慢？
A: 使用 `python run_tests.py quick` 进行快速测试

### Q2: 某些测试被跳过？
A: 检查是否缺少必要的测试数据文件（如地形数据xlsx）

### Q3: 数据库冲突？
A: 每个测试函数都使用独立的测试数据库，自动清理

### Q4: 如何调试失败的测试？
A: 使用 `-v -s` 参数查看详细输出和print语句

```bash
pytest tests/test_xxx.py::test_method -v -s
```

## 📚 相关文档

- [Pytest官方文档](https://docs.pytest.org/)
- [pytest-cov文档](https://pytest-cov.readthedocs.io/)
- [项目执行计划](../../docs/execution_plan.md)
- [阶段13报告](../../docs/stage13_report.md)（测试完成后生成）

## ✅ 测试清单

### 地形服务测试
- [x] 正常加载数据
- [x] 文件不存在回退
- [x] 异常重试机制
- [x] 缓存刷新锁
- [x] 空数据结构验证

### 遮挡算法测试
- [x] GCR计算正确性
- [x] 邻居过滤（横向/沿轴）
- [x] 遮挡角度计算
- [x] 坡度补偿
- [x] 20%沿轴衰减
- [x] 遮挡裕度计算

### API功能测试
- [x] 分页功能
- [x] 时间过滤
- [x] 数据抽样
- [x] 聚合接口（小时/天）
- [x] 错误处理
- [x] 参数验证

---
> 更新日期：2025-11-05  
> 测试覆盖率目标：≥ 80%  
> 状态：✅ 测试套件已完成



