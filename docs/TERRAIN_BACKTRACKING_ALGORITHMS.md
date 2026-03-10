# 地形感知回溯算法论文要点总结

本文档总结了项目中参考的四篇核心论文的所有算法要点和公式。

---

## 论文来源

1. **NREL/CP-5K00-76023** (2020) - Maximizing Yield with Improved Single-Axis Backtracking on Cross-Axis Slopes
2. **NREL/TP-5K00-76626** (2020) - Slope-Aware Backtracking for Single-Axis Trackers
3. **IEEE PVSC 2022** - Terrain Aware Backtracking via Forward Ray Tracing
4. **IEEE PVSC 2023** - Modeling Transposition for Single-Axis Trackers Using Terrain-Aware Backtracking Strategies

---

## 一、NREL核心公式体系

### 1.1 太阳位置坐标转换 (Equation 1)

将太阳方位角和高度角转换为笛卡尔坐标：

```
┌ sx ┐   ┌ cos(βs) × sin(γs) ┐
│ sy │ = │ cos(βs) × cos(γs) │
└ sz ┘   ┌ sin(βs)           ┘
```

**参数说明：**
- `sx, sy, sz` - 太阳在全局坐标系中的笛卡尔坐标
- `βs` - 太阳高度角 (Solar elevation angle)
- `γs` - 太阳方位角 (Solar azimuth, 从北顺时针，0°-360°)

---

### 1.2 全局坐标到跟踪器坐标转换 (Equation 4)

```
┌ sx' ┐   ┌ sx×cos(γa) - sy×sin(γa)                                    ┐
│ sy' │ = │ sx×sin(γa)×cos(βa) + sy×cos(βa)×cos(γa) - sz×sin(βa)       │
└ sz' ┘   ┌ sx×sin(γa)×sin(βa) + sy×sin(βa)×cos(γa) + sz×cos(βa)       ┘
```

**参数说明：**
- `γa` - 跟踪器轴方位角 (Axis azimuth)
- `βa` - 轴倾斜角 (Axis tilt)

---

### 1.3 真跟踪角度 (Equation 5)

```
θT = atan2(sx', sz')
```

**参数说明：**
- `θT` - 真跟踪角度 (True-tracking angle)
- `sx', sz'` - 太阳在跟踪器坐标系中的投影坐标
- `atan2` - 四象限反正切函数，范围 (-180°, 180°]

**物理意义：**
使模块法向量与太阳直射辐照度之间的入射角最小化的旋转角度。

---

### 1.4 标准回溯修正角度 (Equation 2)

```
cos(T) × cos(c) = -1 / GCR
```

**参数说明：**
- `T` - 真跟踪角度
- `c` - 回溯修正角度
- `GCR` - 地面覆盖率比 = 模块宽度 ℓ / 行间距 p

**物理意义：**
平坦地形上的标准回溯公式，假设相邻行之间没有垂直偏移。

---

### 1.5 斜坡感知回溯修正角度 (Equation 11-14)

**核心公式 (Equation 11):**

```
              cos(θT - βc)
cos(θc) = ─────────────────────
           GCR × cos(βc)
```

**完整实现 (Equation 14):**

```
                              │cos(θT - βc)│
θc = -sign(θT) × arccos( ───────────────────── )
                            GCR × cos(βc)
```

**参数说明：**
- `θc` - 回溯修正角度 (Backtracking correction angle)
- `θT` - 真跟踪角度 (True-tracking angle)
- `βc` - 横轴坡度角 (Cross-axis slope angle)
- `GCR` - 地面覆盖率比

**符号约定：**
- `sign(θT)` - 取真跟踪角度的符号，确保回溯方向与跟踪方向相反

---

### 1.6 回溯条件判断 (Equation 15)

```
│cos(θT - βc)│
───────────── < 1  → 需要回溯
 GCR × cos(βc)

│cos(θT - βc)│
───────────── ≥ 1  → 不需要回溯，θc = 0
 GCR × cos(βc)
```

---

### 1.7 最终回溯角度 (Equation 16)

```
θB = θT + θc
```

**参数说明：**
- `θB` - 最终回溯角度 (Backtracking rotation)
- `θT` - 真跟踪角度
- `θc` - 回溯修正角度

---

### 1.8 轴倾斜角计算 (Equation 19)

```
βa = arctan(tan(βg) × cos(Δγ))
```

**参数说明：**
- `βa` - 轴倾斜角 (Axis tilt)
- `βg` - 坡度角 (Grade slope angle)
- `Δγ` - 方位角差 = γa - γg

---

### 1.9 横轴坡度向量计算 (Equation 22)

```
┌ vx ┐   ┌ sin(Δγ) × cos(βa) × cos(βg)                      ┐
│ vy │ = │ sin(βa) × sin(βg) + cos(Δγ) × cos(βa) × cos(βg)   │
└ vz ┘   ┌ -sin(Δγ) × sin(βg) × cos(βa)                     ┘
```

**参数说明：**
- `v` - 横轴坡度向量 (Cross-axis slope vector)
- `βg` - 坡度角
- `βa` - 轴倾斜角
- `Δγ` - 方位角差

---

### 1.10 横轴坡度角计算 (Equation 26)

```
                                     (vx×cos(Δγ) - vy×sin(Δγ))×sin(βa) + vz×cos(βa)
βc = arcsin( ───────────────────────────────────────────────────────────── )
                                      │v│
```

**简化版本 (当坡度方向与跟踪器轴垂直时):**

```
βc = βg × sin(γg - γa)
```

**参数说明：**
- `βc` - 横轴坡度角 (Cross-axis slope angle)
- `γg` - 坡度方位角 (Grade azimuth)
- `γa` - 跟踪器轴方位角 (Axis azimuth)

---

### 1.11 遮挡分数计算 (Equation 32)

```
fs = max(0, min(
    GCR×cos(θ) + (GCR×sin(θ) - tan(βc))×tan(θT) - 1
    ───────────────────────────────────────────── ,
              GCR×(sin(θ)×tan(θT) + cos(θ))
    1))
```

**简化版本 (当真跟踪角度可用时):**

```
         GCR × cos(θ)
fs = ─────────────────
       cos(θT_true)
```

**参数说明：**
- `fs` - 遮挡分数 (Shaded fraction)，范围 [0, 1]
- `θ` - 当前跟踪器角度
- `θT` - 真跟踪角度
- `βc` - 横轴坡度角
- `GCR` - 地面覆盖率比

**物理意义：**
被前排阴影覆盖的模块面积比例。

---

## 二、部分遮挡功率损失模型 (NREL论文)

### 2.1 分段遮挡模型 (Equation 4)

```
         ┌ 1 - (1-fd)×fs×N,  fs < 1/N
Pnorm = │
         └ fd,               fs ≥ 1/N
```

**参数说明：**
- `Pnorm` - 归一化输出功率 (相对于无遮挡情况)
- `fd` - 漫射辐照度分数 (Diffuse fraction)
- `fs` - 遮挡分数 (Shaded fraction)
- `N` - 每列电池数 (标准72电池模块 N=12)

**物理意义：**
- 当底部电池行仅部分遮挡时 (fs < 1/N)，功率损失与遮挡面积成正比
- 当底部电池行完全遮挡时 (fs ≥ 1/N)，功率仅等于漫射分量

---

## 三、前向光线追踪算法 (IEEE PVSC 2022)

**论文文件:** `Terrain_Aware_Backtracking_via_Forward_Ray_Tracing.pdf`

### 3.1 算法核心思想

**传统后向光线追踪：**
- 从"相机"发出光线 → 经过屏幕像素 → 进入场景 → 到达光源

**前向光线追踪 (本文方法)：**
- 移除相机和屏幕对象
- 从光源 (太阳) 直接发出光线
- 检测光线是否与模块平面相交

### 3.2 遮挡分数计算 (Shaded Fraction)

```
         GCR × cos(θ)
fs = ─────────────────────
       cos(θT_true) + ε
```

**参数说明：**
- `fs` - 遮挡分数 (0 = 无遮挡, 1 = 完全遮挡)
- `θ` - 当前跟踪器旋转角度
- `θT_true` - 真跟踪角度 (太阳直射角度)
- `GCR` - 地面覆盖率比
- `ε` - 小偏移量，避免除零错误

### 3.3 几何定义

**Bay (模块组) 定义：**
- 由一个点和一个法向量定义的平面
- 表示具有相同扭矩管轴倾斜角的模块组

**光线定义：**
- 原点：太阳方向单位向量
- 方向：对应于模块角落

### 3.4 相交测试算法

```
对于每个时间步:
    对于每个跟踪器中的每个 bay:
        生成一组光线 (对应于 bay 的角落)
        对于每个可能被遮挡的 bay:
            执行光线-平面相交测试
            如果检测到遮挡:
                两个跟踪器都回溯 1 度
                重复测试直到无遮挡
```

### 3.5 光线-平面相交检测

```
P(t) = O + t×D

其中:
- P(t) - 光线上的点
- O - 光线原点
- D - 光线方向向量
- t - 参数 (t ≥ 0 为有效相交)

相交条件:
|P(t) - PlaneCenter| ≤ PlaneSize/2  (在平面范围内)
```

### 3.6 优化策略

1. **减少相交测试：** 只选择可能阻挡直射辐照度的合理对象
2. **并行处理：** 光线追踪进程并行运行
3. **空间分割：** 使用边界框快速剔除不相交的对象

---

## 四、地形感知回溯建模 (IEEE PVSC 2023)

**论文文件:** `Modeling_Transposition_for_Single-Axis_Trackers_Using_Terrain-Aware_Backtracking_Strategies.pdf`

### 4.1 多Bay加权平均 (Weighted Average Transposition)

```
POA = Σ (ni/N) × POAi

其中:
- N = Σ ni (总模块数)
- ni = 第 i 个 bay 的模块数
- POAi = 第 i 个 bay 的平面阵列辐照度
```

**示例：** 3-bay 跟踪器，分别有 1, 2, 5 个模块：
```
POA = 1/8 × POA1 + 2/8 × POA2 + 5/8 × POA3
```

### 4.2 阴影Bay的有效辐照度

**被遮挡 bay 的贡献：**
```
POA_shaded = DNI × (1 - fs) × cos(AOI) + DHI

其中:
- fs = 遮挡分数
- AOI = 入射角
- DNI = 直射法向辐照度
- DHI = 漫射水平辐照度
```

**电气失配模拟：**
- 当遮挡分数超过阈值时，整个 bay 可能停止贡献
- 粗略模拟旁路二极管效应

### 4.3 逆向转置方法 (Retro-Transposition)

**目的：** 使不支持自定义跟踪角度的软件 (如 PVSyst) 能够建模地形感知回溯

**步骤：**
```
1. 使用地形感知算法计算 POA 辐照度
2. 使用 pvlib.gti_dirint 函数逆向转置
3. 反求解所需的水平辐照度分量:
   GHI = POA / (cos(AOI) + diffuse_correction)
4. 将调整后的气象数据输入 PVSyst
```

**验证结果：** R² = 0.9998 (与直接计算高度一致)

### 4.4 产能损失分解

```
总损失 = 转置损失 + 遮挡损失 + 失配损失

其中:
- 转置损失 ≈ 2-3% (地形导致的角度误差)
- 遮挡损失 ≈ 1-2% (阴影覆盖)
- 失配损失 ≈ 0.5-1% (电气不匹配)
```

### 4.5 地形统计参考值

| 参数 | 最小值 | 平均值 | 最大值 | 标准差 |
|------|--------|--------|--------|--------|
| N/S 扭矩管轴倾斜 | -3.36° | -1.07° | 3.51° | 1.75° |
| 横轴坡度 | -3.98° | -1.31° | 1.41° | 0.90° |
| 轴倾斜失配 | -0.96° | 0.00° | 1.13° | 0.20° |

### 4.6 关键发现

1. **轴倾斜对转置损失的贡献：** 约 13.4% 的总转置损失
2. **回溯时间占比：** 约白天时间的 20%，但仅贡献 16% 的总 POA 辐照度
3. **角度平均与辐照度平均的差异：** 仅 0.18%，在转置建模不确定性范围内

---

## 五、性能基准数据

### 5.1 回溯策略性能对比

| 算法 | 相对于平整场地的损失 | 损失恢复率 | 年产能量 (kWh/m²) |
|------|---------------------|------------|-------------------|
| Standard GCR (36%) | 6.7% | - | ~2000 |
| Artificial GCR (42%) | 4.2% | 33% | ~2040 |
| Geometry Engine | 2.4% | 63% | 2068.23 |
| 平整场地 (参考) | 0% | 100% | 2108.79 |

### 5.2 地形统计 (测试站点)

| 参数 | 最小值 | 平均值 | 最大值 | 标准差 |
|------|--------|--------|--------|--------|
| N/S 扭矩管轴倾斜 | -3.36° | -1.07° | 3.51° | 1.75° |
| 横轴坡度 | -3.98° | -1.31° | 1.41° | 0.90° |
| 轴倾斜失配 | -0.96° | 0.00° | 1.13° | 0.20° |

### 5.3 关键发现

1. **轴倾斜对转置损失的贡献：** 约 13.4% 的总转置损失
2. **回溯时间占比：** 约白天时间的 20%，但仅贡献 16% 的总 POA 辐照度
3. **角度平均与辐照度平均的差异：** 仅 0.18%，在转置建模不确定性范围内

---

## 六、完整实现流程

### 步骤 1: 计算太阳位置
```
使用星历表或太阳位置算法计算:
- 太阳方位角 γs
- 太阳高度角 βs
```

### 步骤 2: 计算斜坡调整参数
```
βa = arctan(tan(βg) × cos(Δγ))           # 轴倾斜角
βc = sin⁻¹(...)                          # 横轴坡度角 (Equation 26)
```

### 步骤 3: 计算太阳投影和真跟踪角度
```
转换为笛卡尔坐标 (Equation 1)
转换为跟踪器坐标 (Equation 4)
θT = atan2(sx', sz')                     # 真跟踪角度
```

### 步骤 4: 计算回溯修正角度
```
如果需要回溯 (Equation 15):
    θc = -sign(θT) × arccos(...)         # (Equation 14)
否则:
    θc = 0
```

### 步骤 5: 计算最终角度
```
θB = θT + θc
```

---

## 七、参数定义汇总

| 符号 | 英文名称 | 中文名称 | 范围 |
|------|----------|----------|------|
| βa | Axis tilt | 轴倾斜角 | 0° ~ +90° |
| βc | Cross-axis slope | 横轴坡度角 | -90° ~ +90° |
| βs | Solar elevation | 太阳高度角 | 0° ~ +90° |
| βg | Grade slope | 坡度角 | 0° ~ +90° |
| γa | Axis azimuth | 轴方位角 | 0° ~ 360° |
| γg | Grade azimuth | 坡度方位角 | 0° ~ 360° |
| γs | Solar azimuth | 太阳方位角 | 0° ~ 360° |
| θB | Backtracking rotation | 回溯旋转角 | -180° ~ +180° |
| θc | Backtracking correction | 回溯修正角 | -180° ~ +180° |
| θT | True-tracking rotation | 真跟踪旋转角 | -180° ~ +180° |
| fs | Shaded fraction | 遮挡分数 | 0 ~ 1 |
| GCR | Ground coverage ratio | 地面覆盖率比 | 0 ~ 1 |
| h | Row offset | 行垂直偏移 | 任意 |
| ℓ | Collector width | 收集器宽度 | 正数 |
| p | Row pitch | 行间距 | 正数 |

---

## 八、参考文献

1. Anderson, K. (2020). "Maximizing Yield with Improved Single-Axis Backtracking on Cross-Axis Slopes" NREL/CP-5K00-76023
2. Anderson, K. and Mikofski, M. (2020). "Slope-Aware Backtracking for Single-Axis Trackers" NREL/TP-5K00-76626
3. Rhee, K. (2022). "Terrain Aware Backtracking via Forward Ray Tracing" IEEE PVSC 49
4. Rhee, K. (2023). "Modeling Transposition for Single-Axis Trackers Using Terrain-Aware Backtracking Strategies" IEEE PVSC 50
5. Lorenzo, E., Narvarte, L., and Muñoz, J. (2011). "Tracking and back-tracking." Progress in Photovoltaics
6. Marion, W. and Dobos, A. (2013). "Rotation Angle for the Optimum Tracking of One-Axis Trackers" NREL/TP-6A20-58891

---

*文档更新: 2026-03-10*
*基于 NREL 技术报告和 IEEE 论文整理*
