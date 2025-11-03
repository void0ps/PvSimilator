import React from 'react'
import EChartsWrapper from './EChartsWrapper'

/**
 * 功率分析图表组件
 * 显示直流功率和交流功率的对比分析
 */
const PowerAnalysisChart = ({ data = [] }) => {
  // 处理数据，按时间排序 - 添加空数据检查
  const processedData = data && Array.isArray(data)
    ? data
        .filter(item => item.timestamp && item.power_dc && item.power_ac)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
        .slice(-24) // 显示最近24小时数据
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
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚡</div>
        <div style={{ fontSize: '16px' }}>暂无功率数据</div>
        <div style={{ fontSize: '14px', marginTop: '8px' }}>请选择模拟任务或检查数据源</div>
      </div>
    )
  }

  const option = {
    title: {
      text: '功率分析',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        const time = params[0].name
        let result = `<div style="text-align: left;">
          <div>时间: ${time}</div>`
        
        params.forEach(param => {
          result += `
            <div style="color: ${param.color};">
              ● ${param.seriesName}: ${param.value} W
            </div>`
        })
        
        result += '</div>'
        return result
      }
    },
    legend: {
      data: ['直流功率', '交流功率', '系统效率'],
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
      data: processedData.map(item => 
        new Date(item.timestamp).toLocaleTimeString('zh-CN', { 
          hour: '2-digit', 
          minute: '2-digit' 
        })
      )
    },
    yAxis: [
      {
        type: 'value',
        name: '功率 (W)',
        position: 'left',
        axisLine: {
          lineStyle: {
            color: '#1890ff'
          }
        }
      },
      {
        type: 'value',
        name: '效率 (%)',
        position: 'right',
        min: 0,
        max: 100,
        axisLine: {
          lineStyle: {
            color: '#52c41a'
          }
        }
      }
    ],
    series: [
      {
        name: '直流功率',
        type: 'line',
        data: processedData.map(item => item.power_dc),
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#1890ff'
        },
        itemStyle: {
          color: '#1890ff'
        }
      },
      {
        name: '交流功率',
        type: 'line',
        data: processedData.map(item => item.power_ac),
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#722ed1'
        },
        itemStyle: {
          color: '#722ed1'
        }
      },
      {
        name: '系统效率',
        type: 'line',
        yAxisIndex: 1,
        data: processedData.map(item => (item.efficiency || 0) * 100),
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#52c41a'
        },
        itemStyle: {
          color: '#52c41a'
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

export default PowerAnalysisChart