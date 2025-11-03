import React, { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

/**
 * ECharts图表包装组件
 * 提供基础的图表渲染和响应式功能
 */
const EChartsWrapper = ({ 
  option, 
  style = { height: '400px' }, 
  theme = 'light',
  onChartReady,
  loading = false,
  ...props 
}) => {
  const chartRef = useRef(null)
  const chartInstance = useRef(null)

  useEffect(() => {
    if (chartRef.current) {
      // 初始化图表
      chartInstance.current = echarts.init(chartRef.current, theme)
      
      // 图表准备就绪回调
      if (onChartReady) {
        onChartReady(chartInstance.current)
      }

      // 组件卸载时销毁图表
      return () => {
        if (chartInstance.current) {
          chartInstance.current.dispose()
        }
      }
    }
  }, [theme, onChartReady])

  useEffect(() => {
    if (chartInstance.current && option) {
      // 设置加载状态
      if (loading) {
        chartInstance.current.showLoading()
      } else {
        chartInstance.current.hideLoading()
      }
      
      // 设置图表配置
      chartInstance.current.setOption(option, true)
    }
  }, [option, loading])

  // 响应式调整
  useEffect(() => {
    const handleResize = () => {
      if (chartInstance.current) {
        chartInstance.current.resize()
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div 
      ref={chartRef} 
      style={style} 
      {...props}
    />
  )
}

export default EChartsWrapper