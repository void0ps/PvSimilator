import React from 'react'
import * as echarts from 'echarts'
import EChartsWrapper from './EChartsWrapper'

/**
 * 光伏板排列分析图表组件
 * 基于3D场景中的光伏板排列参数展示发电量数据
 */
const SolarPanelAnalysisChart = ({ data = [], solarPanelConfig = {} }) => {
  // 从3D场景配置中提取光伏板参数
  const {
    panelCount = 0,
    panelArea = 0, // 单板面积 m²
    panelEfficiency = 0, // 效率
    panelOrientation = 'south', // 朝向
    panelTilt = 30, // 倾角
    totalCapacity = 0 // 总容量 kW
  } = solarPanelConfig

  // 处理发电量数据 - 添加空数据检查
  const processedData = data && Array.isArray(data) 
    ? data
        .filter(item => item.timestamp && item.energy_daily)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    : []

  // 如果没有数据，显示空状态
  if (!processedData || processedData.length === 0) {
    return (
      <div style={{ 
        height: '450px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        flexDirection: 'column',
        color: '#999'
      }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔋</div>
        <div style={{ fontSize: '16px' }}>暂无光伏板发电数据</div>
        <div style={{ fontSize: '14px', marginTop: '8px' }}>请选择模拟任务或检查数据源</div>
      </div>
    )
  }

  // 计算理论发电量（基于光伏板参数）
  const calculateTheoreticalEnergy = (actualEnergy) => {
    if (!actualEnergy || !panelArea || !panelEfficiency) return 0
    
    // 简化的理论计算：实际发电量 / (面积 * 效率)
    return actualEnergy / (panelArea * panelEfficiency * panelCount)
  }

  const option = {
    title: {
      text: '光伏板发电量分析',
      subtext: `配置: ${panelCount}块光伏板 | 总容量: ${totalCapacity}kW | 朝向: ${panelOrientation} | 倾角: ${panelTilt}°`,
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
        let result = `<div style="text-align: left;">
          <div>${date.toLocaleDateString()}</div>
          <div style="color: ${params[0].color};">
            ● 实际发电量: ${params[0].value} kWh
          </div>`
        
        if (params[1]) {
          result += `<div style="color: ${params[1].color};">
            ● 理论发电量: ${params[1].value} kWh
          </div>`
        }
        
        result += `
          <div style="margin-top: 8px;">
            光伏板配置: ${panelCount}块 × ${panelArea}m² × ${(panelEfficiency * 100).toFixed(1)}%
          </div>
        </div>`
        return result
      }
    },
    legend: {
      data: ['实际发电量', '理论发电量'],
      top: '12%'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '25%',
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
        name: '实际发电量',
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
      },
      {
        name: '理论发电量',
        type: 'line',
        data: processedData.map(item => calculateTheoreticalEnergy(item.energy_daily)),
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#52c41a',
          type: 'dashed'
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
      style={{ height: '450px' }}
    />
  )
}

export default SolarPanelAnalysisChart