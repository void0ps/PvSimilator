import React from 'react'
import EChartsWrapper from './EChartsWrapper'

/**
 * 对比分析图表组件
 * 显示不同系统或不同时间段的对比分析
 */
const ComparisonAnalysisChart = ({ data = [] }) => {
  // 模拟对比分析数据
  const comparisonData = {
    // 不同系统对比
    systemComparison: [
      { 
        system: '系统A', 
        capacity: 100, 
        annualEnergy: 125000, 
        efficiency: 0.865,
        performanceRatio: 0.892,
        lcoe: 0.38
      },
      { 
        system: '系统B', 
        capacity: 150, 
        annualEnergy: 187500, 
        efficiency: 0.852,
        performanceRatio: 0.885,
        lcoe: 0.42
      },
      { 
        system: '系统C', 
        capacity: 200, 
        annualEnergy: 250000, 
        efficiency: 0.878,
        performanceRatio: 0.901,
        lcoe: 0.36
      },
      { 
        system: '系统D', 
        capacity: 120, 
        annualEnergy: 150000, 
        efficiency: 0.871,
        performanceRatio: 0.895,
        lcoe: 0.39
      }
    ],
    // 不同组件类型对比
    moduleComparison: [
      { type: '单晶硅', efficiency: 0.215, cost: 1.8, lifespan: 25 },
      { type: '多晶硅', efficiency: 0.185, cost: 1.5, lifespan: 25 },
      { type: '薄膜', efficiency: 0.125, cost: 1.2, lifespan: 20 },
      { type: 'PERC', efficiency: 0.225, cost: 2.0, lifespan: 30 }
    ]
  }

  const systemComparisonOption = {
    title: {
      text: '光伏系统对比分析',
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
      }
    },
    legend: {
      data: ['容量(kW)', '年发电量(kWh)', '效率(%)', '性能比', '度电成本(元)'],
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
      data: comparisonData.systemComparison.map(item => item.system)
    },
    yAxis: [
      {
        type: 'value',
        name: '容量/发电量',
        position: 'left',
        axisLine: {
          lineStyle: {
            color: '#1890ff'
          }
        }
      },
      {
        type: 'value',
        name: '效率/性能比',
        position: 'right',
        min: 0,
        max: 1,
        axisLine: {
          lineStyle: {
            color: '#52c41a'
          }
        }
      }
    ],
    series: [
      {
        name: '容量(kW)',
        type: 'bar',
        yAxisIndex: 0,
        data: comparisonData.systemComparison.map(item => item.capacity),
        itemStyle: {
          color: '#1890ff'
        }
      },
      {
        name: '年发电量(kWh)',
        type: 'bar',
        yAxisIndex: 0,
        data: comparisonData.systemComparison.map(item => item.annualEnergy / 1000),
        itemStyle: {
          color: '#722ed1'
        }
      },
      {
        name: '效率(%)',
        type: 'line',
        yAxisIndex: 1,
        data: comparisonData.systemComparison.map(item => item.efficiency * 100),
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#52c41a'
        },
        itemStyle: {
          color: '#52c41a'
        }
      },
      {
        name: '性能比',
        type: 'line',
        yAxisIndex: 1,
        data: comparisonData.systemComparison.map(item => item.performanceRatio),
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#faad14'
        },
        itemStyle: {
          color: '#faad14'
        }
      },
      {
        name: '度电成本(元)',
        type: 'line',
        yAxisIndex: 1,
        data: comparisonData.systemComparison.map(item => item.lcoe),
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#ff4d4f'
        },
        itemStyle: {
          color: '#ff4d4f'
        }
      }
    ]
  }

  const moduleComparisonOption = {
    title: {
      text: '光伏组件类型对比',
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
      }
    },
    legend: {
      data: ['效率(%)', '成本(元/W)', '寿命(年)'],
      top: '10%'
    },
    radar: {
      indicator: [
        { name: '效率', max: 0.25 },
        { name: '成本', max: 2.5 },
        { name: '寿命', max: 35 }
      ],
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: '#666',
        fontSize: 12
      }
    },
    series: [
      {
        type: 'radar',
        data: comparisonData.moduleComparison.map(item => ({
          value: [item.efficiency * 100, item.cost, item.lifespan],
          name: item.type
        })),
        areaStyle: {},
        lineStyle: {
          width: 2
        },
        itemStyle: {
          borderWidth: 2
        }
      }
    ]
  }

  const scatterOption = {
    title: {
      text: '效率与成本关系分析',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function (params) {
        return `${params.data[2]}<br/>效率: ${(params.data[0] * 100).toFixed(1)}%<br/>成本: ${params.data[1]}元/W`
      }
    },
    xAxis: {
      type: 'value',
      name: '效率 (%)',
      min: 10,
      max: 25,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    yAxis: {
      type: 'value',
      name: '成本 (元/W)',
      min: 1,
      max: 2.5
    },
    series: [
      {
        type: 'scatter',
        symbolSize: function (data) {
          return Math.sqrt(data[2]) * 5 // 根据寿命调整点大小
        },
        data: comparisonData.moduleComparison.map(item => [
          item.efficiency * 100,
          item.cost,
          item.lifespan,
          item.type
        ]),
        itemStyle: {
          color: function (params) {
            const colors = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f']
            return colors[params.dataIndex % colors.length]
          }
        },
        label: {
          show: true,
          formatter: function (params) {
            return params.data[3]
          },
          position: 'top'
        }
      }
    ]
  }

  return (
    <div>
      <EChartsWrapper 
        option={systemComparisonOption} 
        style={{ height: '400px', marginBottom: '24px' }}
      />
      <EChartsWrapper 
        option={moduleComparisonOption} 
        style={{ height: '400px', marginBottom: '24px' }}
      />
      <EChartsWrapper 
        option={scatterOption} 
        style={{ height: '400px' }}
      />
    </div>
  )
}

export default ComparisonAnalysisChart