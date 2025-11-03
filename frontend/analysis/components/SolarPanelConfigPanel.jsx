import React from 'react'
import { Card, Row, Col, Statistic, Tag, Progress, Descriptions } from 'antd'
import { 
  ThunderboltOutlined, 
  AreaChartOutlined, 
  SettingOutlined,
  CompassOutlined,
  RiseOutlined
} from '@ant-design/icons'

/**
 * 光伏板配置信息面板
 * 显示3D场景中的光伏板排列参数
 */
const SolarPanelConfigPanel = ({ solarPanelConfig = {} }) => {
  const {
    panelCount = 0,
    panelArea = 0,
    panelEfficiency = 0,
    panelOrientation = 'south',
    panelTilt = 30,
    totalCapacity = 0,
    installationType = 'rooftop', // 安装类型
    shadingFactor = 0, // 阴影系数
    temperatureCoefficient = -0.004, // 温度系数
    degradationRate = 0.005 // 年衰减率
  } = solarPanelConfig

  // 计算系统效率
  const systemEfficiency = panelEfficiency * (1 - shadingFactor) * 100

  // 获取朝向标签颜色
  const getOrientationColor = (orientation) => {
    const colors = {
      south: 'green',
      north: 'blue',
      east: 'orange',
      west: 'red'
    }
    return colors[orientation] || 'default'
  }

  // 获取安装类型标签
  const getInstallationTypeTag = (type) => {
    const types = {
      rooftop: { color: 'purple', text: '屋顶安装' },
      ground: { color: 'cyan', text: '地面安装' },
      building: { color: 'orange', text: '建筑一体化' }
    }
    const config = types[type] || { color: 'default', text: type }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  return (
    <Card 
      title={
        <span>
          <SettingOutlined /> 光伏板配置信息
        </span>
      }
      style={{ marginBottom: 24 }}
    >
      {/* 主要统计信息 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Statistic
            title="光伏板数量"
            value={panelCount}
            prefix={<AreaChartOutlined />}
            suffix="块"
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="总装机容量"
            value={totalCapacity}
            prefix={<ThunderboltOutlined />}
            suffix="kW"
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="单板面积"
            value={panelArea}
            prefix={<AreaChartOutlined />}
            suffix="m²"
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="系统效率"
            value={systemEfficiency.toFixed(1)}
            prefix={<RiseOutlined />}
            suffix="%"
          />
        </Col>
      </Row>

      {/* 详细配置信息 */}
      <Descriptions 
        bordered 
        size="small" 
        column={2}
        style={{ marginBottom: 16 }}
      >
        <Descriptions.Item label="安装类型">
          {getInstallationTypeTag(installationType)}
        </Descriptions.Item>
        <Descriptions.Item label="朝向">
          <Tag color={getOrientationColor(panelOrientation)}>
            <CompassOutlined /> {panelOrientation.toUpperCase()}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="倾角">
          {panelTilt}°
        </Descriptions.Item>
        <Descriptions.Item label="阴影系数">
          {(shadingFactor * 100).toFixed(1)}%
        </Descriptions.Item>
        <Descriptions.Item label="温度系数">
          {temperatureCoefficient}/°C
        </Descriptions.Item>
        <Descriptions.Item label="年衰减率">
          {(degradationRate * 100).toFixed(2)}%
        </Descriptions.Item>
      </Descriptions>

      {/* 效率分析 */}
      <div style={{ marginTop: 16 }}>
        <div style={{ marginBottom: 8 }}>
          <strong>效率分析</strong>
        </div>
        <Row gutter={8}>
          <Col span={6}>
            <div style={{ fontSize: 12, color: '#666' }}>组件效率</div>
            <Progress 
              percent={Math.round(panelEfficiency * 100)} 
              size="small" 
              format={percent => `${percent}%`}
            />
          </Col>
          <Col span={6}>
            <div style={{ fontSize: 12, color: '#666' }}>阴影损失</div>
            <Progress 
              percent={Math.round(shadingFactor * 100)} 
              size="small" 
              status="exception"
              format={percent => `-${percent}%`}
            />
          </Col>
          <Col span={6}>
            <div style={{ fontSize: 12, color: '#666' }}>温度损失</div>
            <Progress 
              percent={5} 
              size="small" 
              status="active"
              format={percent => `-${percent}%`}
            />
          </Col>
          <Col span={6}>
            <div style={{ fontSize: 12, color: '#666' }}>系统效率</div>
            <Progress 
              percent={Math.round(systemEfficiency)} 
              size="small" 
              status="success"
              format={percent => `${percent}%`}
            />
          </Col>
        </Row>
      </div>

      {/* 性能指标 */}
      <div style={{ marginTop: 16, padding: 12, backgroundColor: '#f5f5f5', borderRadius: 6 }}>
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                {Math.round(panelEfficiency * 100)}%
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>组件效率</div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                {Math.round((1 - shadingFactor) * 100)}%
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>可用率</div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                {Math.round(systemEfficiency)}%
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>系统效率</div>
            </div>
          </Col>
        </Row>
      </div>
    </Card>
  )
}

export default SolarPanelConfigPanel