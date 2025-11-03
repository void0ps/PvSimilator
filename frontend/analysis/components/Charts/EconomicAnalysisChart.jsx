import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic } from 'antd'
import { 
  ThunderboltOutlined, 
  DollarOutlined, 
  RiseOutlined, 
  PieChartOutlined 
} from '@ant-design/icons'
import * as echarts from 'echarts'
import EChartsWrapper from './EChartsWrapper'

/**
 * 经济分析图表组件
 * 基于发电量数据计算经济指标和投资回报分析
 */
const EconomicAnalysisChart = ({ data = [], solarPanelConfig = {}, economicConfig = {} }) => {
  const [economicData, setEconomicData] = useState(null)
  
  // 合并默认经济参数配置
  const defaultEconomicConfig = {
    electricityPrice: 0.6, // 元/kWh
    systemCostPerWatt: 4.5, // 元/W
    discountRate: 0.08, // 折现率
    systemLifetime: 25, // 系统寿命
    degradationRate: 0.005, // 年衰减率
    maintenanceCostRate: 0.02, // 维护成本比例
    selfConsumptionRate: 0.3, // 自用比例
    installationCost: 0, // 安装费用
    feedInTariff: 0.4, // 上网电价
    inflationRate: 0.03, // 通货膨胀率
    taxRate: 0.25, // 所得税率
    hasSubsidy: true,
    subsidyAmount: 0.3,
    subsidyYears: 3
  }

  // 合并配置
  const mergedConfig = {
    ...defaultEconomicConfig,
    ...economicConfig
  }

  // 基于发电量数据计算经济指标
  useEffect(() => {
    if (!data || data.length === 0) {
      setEconomicData(null)
      return
    }

    // 处理数据，按时间排序
    const processedData = data
      .filter(item => item.timestamp && item.energy_daily)
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

    if (processedData.length === 0) return

    // 计算总发电量
    const totalEnergy = processedData.reduce((sum, item) => sum + item.energy_daily, 0)
    
    // 计算系统成本（基于光伏板配置）
    const systemCapacity = solarPanelConfig.totalCapacity || 8.64 // kW
    const systemCost = systemCapacity * 1000 * mergedConfig.systemCostPerWatt
    
    // 计算年度收益
    const dailyEnergyAvg = totalEnergy / processedData.length
    const yearlyEnergy = dailyEnergyAvg * 365
    const yearlyRevenue = yearlyEnergy * mergedConfig.electricityPrice
    const yearlyOperationCost = yearlyRevenue * mergedConfig.maintenanceCostRate
    const yearlyProfit = yearlyRevenue - yearlyOperationCost

    // 计算月度数据
    const monthlyData = []
    const months = ['1月', '2月', '3月', '4月', '5月', '6月', 
                   '7月', '8月', '9月', '10月', '11月', '12月']
    
    months.forEach((month, index) => {
      // 模拟月度变化（基于季节因素）
      const seasonFactor = 1 + Math.sin((index + 1) * Math.PI / 6) * 0.3
      const monthlyEnergy = dailyEnergyAvg * 30 * seasonFactor
      const monthlyRevenue = monthlyEnergy * mergedConfig.electricityPrice
      const monthlyCost = monthlyRevenue * mergedConfig.maintenanceCostRate
      const monthlyProfit = monthlyRevenue - monthlyCost
      
      monthlyData.push({
        month,
        revenue: Math.round(monthlyRevenue),
        cost: Math.round(monthlyCost),
        profit: Math.round(monthlyProfit),
        energy: Math.round(monthlyEnergy)
      })
    })

    // 计算投资回报指标
    const npv = calculateNPV(systemCost, yearlyProfit, mergedConfig)
    const lcoe = calculateLCOE(systemCost, yearlyEnergy, mergedConfig)
    const paybackPeriod = calculatePaybackPeriod(systemCost, yearlyProfit)
    const irr = calculateIRR(systemCost, yearlyProfit, mergedConfig)

    setEconomicData({
      monthlyRevenue: monthlyData,
      roiMetrics: {
        npv: Math.round(npv),
        irr: irr,
        paybackPeriod: paybackPeriod.toFixed(1),
        lcoe: lcoe.toFixed(2)
      },
      summary: {
        totalEnergy: Math.round(totalEnergy),
        systemCost: Math.round(systemCost),
        yearlyRevenue: Math.round(yearlyRevenue),
        yearlyProfit: Math.round(yearlyProfit),
        systemCapacity: systemCapacity
      }
    })
  }, [data, solarPanelConfig, economicConfig])

  // 计算净现值(NPV)
  const calculateNPV = (systemCost, yearlyProfit, config) => {
    let npv = -systemCost
    for (let year = 1; year <= config.systemLifetime; year++) {
      const profit = yearlyProfit * Math.pow(1 - config.degradationRate, year - 1)
      const discountedProfit = profit / Math.pow(1 + config.discountRate, year)
      npv += discountedProfit
    }
    return npv
  }

  // 计算平准化度电成本(LCOE)
  const calculateLCOE = (systemCost, yearlyEnergy, config) => {
    let totalEnergy = 0
    for (let year = 1; year <= config.systemLifetime; year++) {
      const energy = yearlyEnergy * Math.pow(1 - config.degradationRate, year - 1)
      totalEnergy += energy
    }
    return systemCost / totalEnergy
  }

  // 计算投资回收期
  const calculatePaybackPeriod = (systemCost, yearlyProfit) => {
    return yearlyProfit > 0 ? systemCost / yearlyProfit : Infinity
  }

  // 计算内部收益率(IRR)
  const calculateIRR = (systemCost, yearlyProfit, config) => {
    const npvFunc = (rate) => {
      let npv = -systemCost
      for (let year = 1; year <= config.systemLifetime; year++) {
        const profit = yearlyProfit * Math.pow(1 - config.degradationRate, year - 1)
        npv += profit / Math.pow(1 + rate, year)
      }
      return npv
    }

    // 使用二分法求解IRR
    let low = 0.0
    let high = 0.5
    for (let i = 0; i < 100; i++) {
      const mid = (low + high) / 2
      if (npvFunc(mid) > 0) {
        low = mid
      } else {
        high = mid
      }
      if (high - low < 1e-6) break
    }
    
    return ((low + high) / 2 * 100).toFixed(1) // 转换为百分比
  }

  // 计算年度现金流
  const calculateAnnualCashflow = (yearlyProfit, config) => {
    const cashflows = []
    for (let year = 1; year <= config.systemLifetime; year++) {
      const profit = yearlyProfit * Math.pow(1 - config.degradationRate, year - 1)
      cashflows.push(Math.round(profit))
    }
    return cashflows
  }

  // 计算累计现金流
  const calculateCumulativeCashflow = (yearlyProfit, config, systemCost) => {
    const cumulative = []
    let total = -systemCost
    for (let year = 1; year <= config.systemLifetime; year++) {
      const profit = yearlyProfit * Math.pow(1 - config.degradationRate, year - 1)
      total += profit
      cumulative.push(Math.round(total))
    }
    return cumulative
  }

  // 如果没有数据，显示空状态
  if (!economicData) {
    return (
      <div style={{ 
        height: '800px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        flexDirection: 'column',
        color: '#999'
      }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>💰</div>
        <div style={{ fontSize: '16px' }}>正在计算经济分析数据...</div>
        <div style={{ fontSize: '14px', marginTop: '8px' }}>请确保有发电量数据</div>
      </div>
    )
  }

  // 月度经济分析图表配置
  const revenueOption = {
    title: {
      text: '月度经济分析',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function (params) {
        const monthData = economicData.monthlyRevenue.find(item => item.month === params[0].name)
        return `
          <div style="text-align: left;">
            <div style="font-weight: bold; margin-bottom: 8px;">${params[0].name}</div>
            <div style="color: #1890ff;">● 发电量: ${monthData.energy.toLocaleString()} kWh</div>
            <div style="color: #1890ff;">● 收入: ${monthData.revenue.toLocaleString()} 元</div>
            <div style="color: #ff4d4f;">● 成本: ${monthData.cost.toLocaleString()} 元</div>
            <div style="color: #52c41a;">● 利润: ${monthData.profit.toLocaleString()} 元</div>
          </div>
        `
      }
    },
    legend: {
      data: ['收入', '成本', '利润'],
      top: '10%'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '20%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: economicData.monthlyRevenue.map(item => item.month)
    },
    yAxis: {
      type: 'value',
      name: '金额 (元)',
      axisLabel: {
        formatter: '{value}'
      }
    },
    series: [
      {
        name: '收入',
        type: 'bar',
        data: economicData.monthlyRevenue.map(item => item.revenue),
        itemStyle: {
          color: '#1890ff'
        }
      },
      {
        name: '成本',
        type: 'bar',
        data: economicData.monthlyRevenue.map(item => item.cost),
        itemStyle: {
          color: '#ff4d4f'
        }
      },
      {
        name: '利润',
        type: 'line',
        data: economicData.monthlyRevenue.map(item => item.profit),
        smooth: true,
        lineStyle: {
          width: 3,
          color: '#52c41a'
        },
        itemStyle: {
          color: '#52c41a'
        }
      }
    ]
  }

  // 投资回报指标雷达图配置
  const metricsOption = {
    title: {
      text: '投资回报指标',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function (params) {
        const value = params.data.value
        const name = params.data.name
        let unit = ''
        
        if (name.includes('收益率')) {
          unit = '%'
        } else if (name.includes('成本')) {
          unit = '元/kWh'
        } else if (name.includes('回收期')) {
          unit = '年'
        } else {
          unit = '元'
        }
        
        return `${name}: ${value}${unit}`
      }
    },
    radar: {
      indicator: [
        { name: '净现值(NPV)', max: 200000 },
        { name: '内部收益率(IRR)', max: 30 },
        { name: '投资回收期', max: 10 },
        { name: '度电成本(LCOE)', max: 1 }
      ],
      shape: 'circle',
      splitNumber: 5,
      axisName: {
        color: '#666',
        fontSize: 12
      }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: [
              economicData.roiMetrics.npv,
              parseFloat(economicData.roiMetrics.irr),
              parseFloat(economicData.roiMetrics.paybackPeriod),
              parseFloat(economicData.roiMetrics.lcoe)
            ],
            name: '经济指标',
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(24, 144, 255, 0.6)' },
                { offset: 1, color: 'rgba(24, 144, 255, 0.1)' }
              ])
            },
            lineStyle: {
              width: 2,
              color: '#1890ff'
            },
            itemStyle: {
              color: '#1890ff'
            }
          }
        ]
      }
    ]
  }

  // 现金流分析图表配置
  const cashflowOption = {
    title: {
      text: '现金流分析',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        const year = params[0].name
        const cumulative = params[0].value
        const annual = params[1].value
        return `
          <div style="text-align: left;">
            <div style="font-weight: bold;">第${year}年</div>
            <div style="color: #52c41a;">● 年度现金流: ${annual.toLocaleString()} 元</div>
            <div style="color: #1890ff;">● 累计现金流: ${cumulative.toLocaleString()} 元</div>
          </div>
        `
      }
    },
    legend: {
      data: ['累计现金流', '年度现金流'],
      top: '10%'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '20%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: Array.from({length: economicConfig.systemLifetime}, (_, i) => `${i + 1}`)
    },
    yAxis: {
      type: 'value',
      name: '金额 (元)',
      axisLabel: {
        formatter: '{value}'
      }
    },
    series: [
      {
        name: '累计现金流',
        type: 'line',
        data: calculateCumulativeCashflow(economicData.summary.yearlyProfit, economicConfig, economicData.summary.systemCost),
        smooth: true,
        lineStyle: {
          width: 3,
          color: '#1890ff'
        },
        itemStyle: {
          color: '#1890ff'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(24, 144, 255, 0.6)' },
            { offset: 1, color: 'rgba(24, 144, 255, 0.1)' }
          ])
        }
      },
      {
        name: '年度现金流',
        type: 'bar',
        data: calculateAnnualCashflow(economicData.summary.yearlyProfit, economicConfig),
        itemStyle: {
          color: '#52c41a'
        }
      }
    ]
  }



  return (
    <div>
      {/* 系统概览卡片 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="系统容量"
              value={economicData.summary.systemCapacity}
              suffix="kW"
              prefix={<ThunderboltOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="系统成本"
              value={economicData.summary.systemCost.toLocaleString()}
              suffix="元"
              prefix={<DollarOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="年收益"
              value={economicData.summary.yearlyRevenue.toLocaleString()}
              suffix="元"
              prefix={<RiseOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="年利润"
              value={economicData.summary.yearlyProfit.toLocaleString()}
              suffix="元"
              prefix={<PieChartOutlined />}
            />
          </Col>
        </Row>
      </Card>

      {/* 月度经济分析图表 */}
      <EChartsWrapper 
        option={revenueOption} 
        style={{ height: '400px', marginBottom: '24px' }}
      />
      
      {/* 投资回报指标图表 */}
      <EChartsWrapper 
        option={metricsOption} 
        style={{ height: '400px', marginBottom: '24px' }}
      />
      
      {/* 现金流分析图表 */}
      <EChartsWrapper 
        option={cashflowOption} 
        style={{ height: '400px' }}
      />
    </div>
  )
}

export default EconomicAnalysisChart