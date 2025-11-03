import React, { useState, useEffect } from 'react'
import { Menu, Card, Row, Col, Statistic, List, Typography, Space, Divider, message } from 'antd'
import { 
  DashboardOutlined, 
  ApartmentOutlined, 
  PlayCircleOutlined, 
  CloudOutlined,
  BarChartOutlined,
  ThunderboltOutlined
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { systemsApi, simulationsApi } from '../../services/api'

const { Text } = Typography

const Sidebar = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [stats, setStats] = useState({
    systemCount: 0,
    simulationCount: 0,
    totalCapacity: 0,
    avgEfficiency: 0
  })
  const [recentSimulations, setRecentSimulations] = useState([])

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // 获取系统列表
        const systemsResponse = await systemsApi.getSystems()
        const systems = systemsResponse || []
        
        // 获取模拟列表
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
        
        // 获取最近的模拟任务
        const recentSims = simulations
          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
          .slice(0, 3)
          .map(sim => {
            // 查找对应的系统名称
            const system = systems.find(s => s.id === sim.system_id)
            return {
              id: sim.id,
              name: system ? system.name : sim.name || '未命名系统',
              status: sim.status || 'pending',
              progress: sim.progress || 0
            }
          })
        
        setRecentSimulations(recentSims)
        
      } catch (error) {
        console.error('获取仪表板数据失败:', error)
        message.error('获取仪表板数据失败，请检查网络连接或后端服务状态')
        
        // API调用失败时显示空数据
        setStats({
          systemCount: 0,
          simulationCount: 0,
          totalCapacity: 0,
          avgEfficiency: 0
        })
        
        setRecentSimulations([])
      }
    }
    
    fetchDashboardData()
  }, [])

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表板',
    },
    {
      key: '/systems',
      icon: <ApartmentOutlined />,
      label: '光伏系统',
    },
    {
      key: '/weather',
      icon: <CloudOutlined />,
      label: '气象数据',
    },
    {
      key: '/simulations',
      icon: <PlayCircleOutlined />,
      label: '仿真模拟',
    },
    {
      key: '/analysis',
      icon: <BarChartOutlined />,
      label: '分析报告',
    },
  ]

  const handleMenuClick = ({ key }) => {
    navigate(key)
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 仪表盘统计信息 */}
      <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
        <Text strong style={{ fontSize: '14px', marginBottom: '12px', display: 'block' }}>
          系统概览
        </Text>
        
        <Row gutter={[8, 8]}>
          <Col span={12}>
            <Card size="small" styles={{ body: { padding: '8px' } }}>
              <Statistic
                title="系统数量"
                value={stats.systemCount}
                prefix={<ApartmentOutlined style={{ fontSize: '12px' }} />}
                valueStyle={{ fontSize: '14px', color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" styles={{ body: { padding: '8px' } }}>
              <Statistic
                title="模拟任务"
                value={stats.simulationCount}
                prefix={<PlayCircleOutlined style={{ fontSize: '12px' }} />}
                valueStyle={{ fontSize: '14px', color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" styles={{ body: { padding: '8px' } }}>
              <Statistic
                title="容量(kW)"
                value={stats.totalCapacity}
                precision={1}
                prefix={<ThunderboltOutlined style={{ fontSize: '12px' }} />}
                valueStyle={{ fontSize: '14px', color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" styles={{ body: { padding: '8px' } }}>
              <Statistic
                title="效率(%)"
                value={stats.avgEfficiency}
                precision={1}
                prefix={<BarChartOutlined style={{ fontSize: '12px' }} />}
                valueStyle={{ fontSize: '14px', color: '#f5222d' }}
              />
            </Card>
          </Col>
        </Row>
        
        <Divider style={{ margin: '12px 0' }} />
        
        {/* 最近模拟任务 */}
        <div>
          <Text strong style={{ fontSize: '14px', marginBottom: '8px', display: 'block' }}>
            最近任务
          </Text>
          <List
            size="small"
            dataSource={recentSimulations.slice(0, 3)}
            renderItem={(simulation) => (
              <List.Item style={{ padding: '4px 0' }}>
                <div style={{ width: '100%' }}>
                  <Text style={{ fontSize: '12px' }}>{simulation.name}</Text>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text 
                      type={simulation.status === 'completed' ? 'success' : 
                            simulation.status === 'running' ? 'warning' : 'secondary'} 
                      style={{ fontSize: '12px' }}
                    >
                      {simulation.status === 'completed' ? '已完成' : 
                       simulation.status === 'running' ? '进行中' : '待开始'}
                    </Text>
                    <Text type="secondary" style={{ fontSize: '9px' }}>
                      {simulation.progress}%
                    </Text>
                  </div>
                </div>
              </List.Item>
            )}
          />
        </div>
      </div>
      
      {/* 导航菜单 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0 }}
        />
      </div>
    </div>
  )
}

export default Sidebar