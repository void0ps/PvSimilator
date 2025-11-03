import React from 'react'
import EChartsWrapper from './EChartsWrapper'

/**
 * 性能分析图表组件
 * 显示系统性能指标和效率分析
 */
const PerformanceAnalysisChart = ({ data = [] }) => {
  // 处理性能数据
  const performanceData = {
    // 效率分布数据
    efficiencyDistribution: [
      { range: '0-10%', count: 2 },
      { range: '10-20%', count: 5 },
      { range: '20-30%', count: 12 },
      { range: '30-40%', count: 25 },
      { range: '40-50%', count: 35 },
      { range: '50-60%', count: 28 },
      { range: '60-70%', count: 18 },
      { range: '70-80%', count: 8 },
      { range: '80-90%', count: 3 },
      { range: '90-100%', count: 1 }
    ],
    // 性能指标
    performanceMetrics: {
      averageEfficiency: 0.856,  // 平均效率
      performanceRatio: 0.892,   // 性能比
      capacityFactor: 0.184,     // 容量系数
      availability: 0.987       // 可用率
    },
    // 月度性能趋势
    monthlyPerformance: [
      { month: '1月', efficiency: 0.82, performanceRatio: 0.85, capacityFactor: 0.15 },
      { month: '2月', efficiency: 0.83, performanceRatio: 0.86, capacityFactor: 0.16 },
      { month: '3月', efficiency: 0.85, performanceRatio: 0.88, capacityFactor: 0.17 },
      { month: '4月', efficiency: 0.87, performanceRatio: 0.90, capacityFactor: 0.19 },
      { month: '5月', efficiency: 0.88, performanceRatio: 0.91, capacityFactor: 0.20 },
      { month: '6月', efficiency: 0.89, performanceRatio: 0.92, capacityFactor: 0.21 },
      { month: '7月', efficiency: 0.90, performanceRatio: 0.93, capacityFactor: 0.22 },
      { month: '8月', efficiency: 0.89, performanceRatio: 0.92, capacityFactor: 0.21 },
      { month: '9月', efficiency: 0.88, performanceRatio: 0.91, capacityFactor: 0.20 },
      { month: '10月', efficiency: 0.86, performanceRatio: 0.89, capacityFactor: 0.18 },
      { month: '11月', efficiency: 0.84, performanceRatio: 0.87, capacityFactor: 0.17 },
      { month: '12月', efficiency: 0.82, performanceRatio: 0.85, capacityFactor: 0.16 }
    ]
  }

  const efficiencyOption = {
    title: {
      text: '效率分布分析',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: '10%'
    },
    series: [
      {
        name: '效率分布',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '60%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 18,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: performanceData.efficiencyDistribution.map(item => ({
          value: item.count,
          name: item.range
        }))
      }
    ]
  }

  const trendOption = {
    title: {
      text: '月度性能趋势',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        const data = performanceData.monthlyPerformance.find(
          item => item.month === params[0].name
        )
        return `
          <div style="text-align: left;">
            <div>${data.month}</div>
            <div style="color: #1890ff;">● 系统效率: ${(data.efficiency * 100).toFixed(1)}%</div>
            <div style="color: #52c41a;">● 性能比: ${(data.performanceRatio * 100).toFixed(1)}%</div>
            <div style="color: #faad14;">● 容量系数: ${(data.capacityFactor * 100).toFixed(1)}%</div>
          </div>
        `
      }
    },
    legend: {
      data: ['系统效率', '性能比', '容量系数'],
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
      data: performanceData.monthlyPerformance.map(item => item.month)
    },
    yAxis: {
      type: 'value',
      name: '百分比 (%)',
      min: 0,
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [
      {
        name: '系统效率',
        type: 'line',
        data: performanceData.monthlyPerformance.map(item => item.efficiency * 100),
        smooth: true,
        lineStyle: {
          width: 3,
          color: '#1890ff'
        },
        itemStyle: {
          color: '#1890ff'
        }
      },
      {
        name: '性能比',
        type: 'line',
        data: performanceData.monthlyPerformance.map(item => item.performanceRatio * 100),
        smooth: true,
        lineStyle: {
          width: 3,
          color: '#52c41a'
        },
        itemStyle: {
          color: '#52c41a'
        }
      },
      {
        name: '容量系数',
        type: 'line',
        data: performanceData.monthlyPerformance.map(item => item.capacityFactor * 100),
        smooth: true,
        lineStyle: {
          width: 3,
          color: '#faad14'
        },
        itemStyle: {
          color: '#faad14'
        }
      }
    ]
  }

  return (
    <div>
      <EChartsWrapper 
        option={efficiencyOption} 
        style={{ height: '400px', marginBottom: '24px' }}
      />
      <EChartsWrapper 
        option={trendOption} 
        style={{ height: '400px' }}
      />
    </div>
  )
}

export default PerformanceAnalysisChart