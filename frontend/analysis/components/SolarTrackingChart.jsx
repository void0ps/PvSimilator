import React, { useState, useEffect } from 'react'
import { Card, Typography, message } from 'antd'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import api from '../services/api'

const { Title, Text } = Typography

// 从气象数据获取位置数据并计算太阳位置
const fetchSolarTrackingData = async () => {
  try {
    // 1. 获取位置列表
    const locations = await api.getLocations()
    if (!locations || locations.length === 0) {
      message.warning('未找到位置数据，使用默认位置计算')
      return generateDefaultTrackingData()
    }
    
    // 使用第一个位置数据
    const location = locations[0]
    const { latitude, longitude } = location
    
    // 2. 获取当前日期
    const currentDate = new Date()
    const dateStr = currentDate.toISOString().split('T')[0]
    
    // 3. 调用后端API计算太阳位置（使用pvlib库）
    const solarPositionResponse = await api.getSolarPosition({
      latitude,
      longitude,
      date: dateStr,
      timezone: 'Asia/Shanghai'
    })
    
    // 4. 处理太阳位置数据
    const solarPositions = solarPositionResponse.solar_positions || []
    const trackingData = solarPositions.map((position, index) => {
      const timestamp = new Date(position.timestamp)
      const hour = timestamp.getHours()
      
      // 获取太阳高度角和方位角
      const solarElevation = position.solar_elevation || 0
      const solarAzimuth = position.solar_azimuth || 0
      
      // 单轴跟踪：光伏板倾角为0度，只进行方位角跟踪
      // 计算光伏板跟踪角度（东西向水平跟踪）
      const panelAzimuth = solarAzimuth > 180 ? solarAzimuth - 180 : solarAzimuth
      const panelElevation = 0 // 光伏板倾角为0度
      
      return {
        time: `${hour.toString().padStart(2, '0')}:00`,
        solarElevation: Math.max(0, solarElevation) + 90, // 角度加90度显示
        panelAzimuth: panelAzimuth + 90, // 角度加90度显示
        trackingError: Math.abs(solarAzimuth - panelAzimuth) // 跟踪误差
      }
    })
    
    return trackingData
    
  } catch (error) {
    console.error('获取太阳位置数据失败:', error)
    message.error('获取太阳位置数据失败，使用模拟数据')
    return generateDefaultTrackingData()
  }
}

// 默认数据生成函数（当API调用失败时使用）
const generateDefaultTrackingData = () => {
  const data = []
  
  // 生成一天24小时的数据
  for (let hour = 0; hour < 24; hour++) {
    // 使用pvlib库计算太阳高度角（正午最高，早晚最低）
    const hourAngle = (hour - 12) * 15 // 时角，正午为0度
    const declination = 23.45 * Math.sin((284 + 173) * Math.PI / 180) // 太阳赤纬角
    const latitude = 30 // 假设纬度30度
    
    // 计算太阳高度角
    const solarElevation = Math.asin(
      Math.sin(latitude * Math.PI / 180) * Math.sin(declination * Math.PI / 180) +
      Math.cos(latitude * Math.PI / 180) * Math.cos(declination * Math.PI / 180) * Math.cos(hourAngle * Math.PI / 180)
    ) * 180 / Math.PI
    
    // 计算太阳方位角
    const solarAzimuth = Math.atan2(
      Math.sin(hourAngle * Math.PI / 180),
      Math.cos(latitude * Math.PI / 180) * Math.tan(declination * Math.PI / 180) -
      Math.sin(latitude * Math.PI / 180) * Math.cos(hourAngle * Math.PI / 180)
    ) * 180 / Math.PI + 180
    
    // 单轴跟踪：光伏板倾角为0度，只进行方位角跟踪
    const panelAzimuth = solarAzimuth > 180 ? solarAzimuth - 180 : solarAzimuth
    const panelElevation = 0 // 光伏板倾角为0度
    
    data.push({
      time: `${hour.toString().padStart(2, '0')}:00`,
      solarElevation: Math.max(0, solarElevation) + 90, // 角度加90度显示
      panelAzimuth: panelAzimuth + 90, // 角度加90度显示
      trackingError: Math.abs(solarAzimuth - panelAzimuth) // 跟踪误差
    })
  }
  
  return data
}

const SolarTrackingChart = () => {
  const [trackingData, setTrackingData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadTrackingData = async () => {
      setLoading(true)
      try {
        const data = await fetchSolarTrackingData()
        setTrackingData(data)
      } catch (error) {
        console.error('加载跟踪数据失败:', error)
        const defaultData = generateDefaultTrackingData()
        setTrackingData(defaultData)
      } finally {
        setLoading(false)
      }
    }
    
    loadTrackingData()
  }, [])

  return (
    <Card 
      title="逆跟踪算法太阳角度曲线" 
      size="small" 
      style={{ height: '480px', marginBottom: '16px' }}
    >
      <div style={{ height: '420px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trackingData} margin={{ top: 15, right: 30, left: 20, bottom: 15 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis 
              label={{ value: '角度 (°)', angle: -90, position: 'insideLeft' }}
              domain={[0, 'dataMax + 10']} // 从0度开始，不显示负值
            />
            <Tooltip 
              formatter={(value, name) => [
                `${parseFloat(value).toFixed(1)}°`, 
                {
                  'solarElevation': '太阳高度角',
                  'panelAzimuth': '光伏板跟踪角度'
                }[name]
              ]}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="solarElevation" 
              stroke="#ff6b6b" 
              strokeWidth={2}
              name="太阳高度角"
              dot={false}
            />
            <Line 
              type="monotone" 
              dataKey="panelAzimuth" 
              stroke="#45b7d1" 
              strokeWidth={2}
              name="光伏板跟踪角度"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <div style={{ marginTop: '10px', fontSize: '10px', color: '#666' }}>
        <Text type="secondary">
          单轴跟踪算法：光伏板进行东西向水平跟踪，倾角为0度（水平放置）
        </Text>
      </div>
    </Card>
  )
}

export default SolarTrackingChart