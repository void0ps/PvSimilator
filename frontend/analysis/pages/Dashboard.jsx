import React, { useState, useEffect } from 'react'
import { Row, Col, Card, Statistic, List, Typography, Space, Alert, Switch } from 'antd'
import { 
  ThunderboltOutlined, 
  ApartmentOutlined, 
  PlayCircleOutlined,
  BarChartOutlined,
  EyeOutlined
} from '@ant-design/icons'
import { systemsApi, simulationsApi } from '../services/api'
import SolarPanel3D from '../components/ThreeD/SolarPanel3D'
import SolarTrackingChart from '../components/SolarTrackingChart'

const { Title, Text } = Typography

// 仪表盘统计卡片组件 - 可以独立使用
const DashboardStats = ({ stats, loading }) => (
  <Row gutter={16} style={{ marginBottom: 16 }}>
    <Col span={6}>
      <Card size="small">
        <Statistic
          title="光伏系统数量"
          value={stats.systemCount}
          prefix={<ApartmentOutlined />}
          valueStyle={{ color: '#1890ff', fontSize: '16px' }}
        />
      </Card>
    </Col>
    <Col span={6}>
      <Card size="small">
        <Statistic
          title="模拟任务数量"
          value={stats.simulationCount}
          prefix={<PlayCircleOutlined />}
          valueStyle={{ color: '#52c41a', fontSize: '16px' }}
        />
      </Card>
    </Col>
    <Col span={6}>
      <Card size="small">
        <Statistic
          title="总装机容量(kW)"
          value={stats.totalCapacity}
          precision={1}
          prefix={<ThunderboltOutlined />}
          valueStyle={{ color: '#faad14', fontSize: '16px' }}
        />
      </Card>
    </Col>
    <Col span={6}>
      <Card size="small">
        <Statistic
          title="平均效率(%)"
          value={stats.avgEfficiency}
          precision={1}
          prefix={<BarChartOutlined />}
          valueStyle={{ color: '#f5222d', fontSize: '16px' }}
        />
      </Card>
    </Col>
  </Row>
)

// 最近模拟任务组件 - 可以独立使用
const RecentSimulations = ({ recentSimulations, loading }) => (
  <Card title="最近模拟任务" size="small" loading={loading}>
    <List
      size="small"
      dataSource={recentSimulations}
      renderItem={(simulation) => (
        <List.Item>
          <List.Item.Meta
            title={<Text style={{ fontSize: '12px' }}>{simulation.name}</Text>}
            description={
              <Space direction="vertical" size={0}>
                <Text type={simulation.status === 'completed' ? 'success' : 
                           simulation.status === 'running' ? 'warning' : 'secondary'} 
                      style={{ fontSize: '10px' }}>
                  状态: {simulation.status === 'completed' ? '已完成' : 
                        simulation.status === 'running' ? '进行中' : '待开始'}
                </Text>
                <Text type="secondary" style={{ fontSize: '10px' }}>
                  进度: {simulation.progress || 0}%
                </Text>
              </Space>
            }
          />
        </List.Item>
      )}
    />
  </Card>
)

// 3D展示控制组件
const ThreeDControl = ({ show3D, setShow3D }) => (
  <div style={{ marginBottom: 16 }}>
    <Space>
      <EyeOutlined />
      <span style={{ fontSize: '12px' }}>3D展示:</span>
      <Switch 
        size="small"
        checked={show3D} 
        onChange={setShow3D}
        checkedChildren="开启" 
        unCheckedChildren="关闭" 
      />
    </Space>
  </div>
)

const Dashboard = () => {
  const [stats, setStats] = useState({
    systemCount: 0,
    simulationCount: 0,
    totalCapacity: 0,
    avgEfficiency: 0
  })
  const [recentSimulations, setRecentSimulations] = useState([])
  const [loading, setLoading] = useState(true)
  const [show3D, setShow3D] = useState(false)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      
      // 获取系统统计
      const systemsResponse = await systemsApi.getSystems()
      const systems = systemsResponse || []
      
      // 获取模拟统计
      const simulationsResponse = await simulationsApi.getSimulations()
      const simulations = simulationsResponse || []
      
      // 计算统计数据
      const totalCapacity = systems.reduce((sum, system) => sum + system.capacity_kw, 0)
      const avgEfficiency = simulations.length > 0 
        ? simulations.reduce((sum, sim) => sum + (sim.avg_efficiency || 0), 0) / simulations.length 
        : 0
      
      setStats({
        systemCount: systems.length,
        simulationCount: simulations.length,
        totalCapacity: parseFloat(totalCapacity.toFixed(2)),
        avgEfficiency: parseFloat(avgEfficiency.toFixed(2))
      })
      
      // 获取最近的模拟
      const recentSims = simulations
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 5)
      
      setRecentSimulations(recentSims)
      
    } catch (error) {
      console.error('获取仪表板数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* 完整仪表盘页面布局 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>仪表板</Title>
        <ThreeDControl show3D={show3D} setShow3D={setShow3D} />
      </div>
      
      <Alert
        message="欢迎使用光伏仿真软件"
        description="这是一个专业的光伏系统仿真平台，提供系统建模、环境模拟、性能计算和可视化分析功能。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />
      
      <DashboardStats stats={stats} loading={loading} />
      
      {/* 3D展示区域和内容区域并排显示 */}
      <Row gutter={16}>
        {/* 3D展示区域 - 占据2/3宽度 */}
        {show3D && (
          <Col span={16}>
            <Card title="3D光伏板跟踪太阳演示" style={{ height: '700px' }}>
              <SolarPanel3D />
            </Card>
          </Col>
        )}
        
        {/* 逆跟踪算法太阳角度曲线 - 占据1/3宽度（3D光伏板的一半） */}
        <Col span={show3D ? 8 : 24}>
          {show3D ? (
            // 3D模式：显示太阳角度跟踪曲线
            <Card title="逆跟踪算法太阳角度曲线" style={{ height: '700px' }}>
              <SolarTrackingChart />
            </Card>
          ) : (
            // 普通模式：显示最近模拟任务和快速操作
            <Row gutter={16}>
              <Col span={24}>
                <Card title="最近模拟任务" loading={loading} size="small" style={{ height: '180px', marginBottom: 16 }}>
                  <List
                    size="small"
                    dataSource={recentSimulations}
                    renderItem={(simulation) => (
                      <List.Item>
                        <List.Item.Meta
                          title={<Text style={{ fontSize: '12px' }}>{simulation.name}</Text>}
                          description={
                            <Space direction="vertical" size={0}>
                              <Text type={simulation.status === 'completed' ? 'success' : 
                                         simulation.status === 'running' ? 'warning' : 'secondary'} 
                                    style={{ fontSize: '10px' }}>
                                状态: {simulation.status === 'completed' ? '已完成' : 
                                      simulation.status === 'running' ? '进行中' : '待开始'}
                              </Text>
                              <Text type="secondary" style={{ fontSize: '10px' }}>
                                进度: {simulation.progress || 0}%
                              </Text>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
              
              <Col span={24}>
                <Card title="快速操作" loading={loading} size="small" style={{ height: '180px' }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text style={{ fontSize: '12px' }}>快速开始新的仿真任务或查看现有系统</Text>
                    <div>
                      <Text strong style={{ fontSize: '12px' }}>功能特性:</Text>
                      <ul style={{ marginTop: 4, marginLeft: 16, fontSize: '10px' }}>
                        <li>光伏系统建模与配置</li>
                        <li>气象数据集成分析</li>
                        <li>发电量预测计算</li>
                        <li>经济性评估 (LCOE)</li>
                        <li>3D可视化展示</li>
                      </ul>
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>
          )}
        </Col>
      </Row>
    </div>
  )
}

// 导出组件供侧边栏使用
export { DashboardStats, RecentSimulations, ThreeDControl }
export default Dashboard