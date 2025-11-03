import React from 'react'
import * as echarts from 'echarts'
import EChartsWrapper from './EChartsWrapper'

/**
 * 发电量分析图表组件
 * 显示时间序列的发电量数据
 */
const EnergyProductionChart = ({ data = [] }) => {
  // 处理数据，按时间排序 - 添加空数据检查
  const processedData = data && Array.isArray(data)
    ? data
        .filter(item => item.timestamp && item.energy_daily)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
        .slice(-30) // 显示最近30天数据
    : []

  // 如果没有数据，显示空状态
  if (!processedData || processedData.length === 0) {
    return (
      <div style={{ 
        height: '400px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        flexDirection: 'column',
        color: '#999'
      }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>
        <div style={{ fontSize: '16px' }}>暂无发电量数据</div>
        <div style={{ fontSize: '14px', marginTop: '8px' }}>请选择模拟任务或检查数据源</div>
      </div>
    )
  }

  const option = {
    title: {
      text: '日发电量趋势',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        const date = new Date(params[0].name)
        const energy = params[0].value
        return `
          <div style="text-align: left;">
            <div>${date.toLocaleDateString()}</div>
            <div style="color: ${params[0].color};">
              ● 日发电量: ${energy} kWh
            </div>
          </div>
        `
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: processedData.map(item => 
        new Date(item.timestamp).toLocaleDateString()
      ),
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: '发电量 (kWh)',
      nameTextStyle: {
        padding: [0, 0, 0, 20]
      }
    },
    series: [
      {
        name: '日发电量',
        type: 'line',
        data: processedData.map(item => item.energy_daily),
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
      }
    ]
  }

  return (
    <EChartsWrapper 
      option={option} 
      style={{ height: '400px' }}
    />
  )
}

export default EnergyProductionChart