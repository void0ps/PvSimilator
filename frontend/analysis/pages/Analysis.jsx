import React, { useState, useEffect } from 'react'
import {
  Card, Row, Col, Select, DatePicker, Button, Tabs, Statistic,
  Table, Progress, Space, Tag, message, Spin
} from 'antd'
import {
  BarChartOutlined, LineChartOutlined, PieChartOutlined,
  DownloadOutlined, EyeOutlined, ThunderboltOutlined,
  DollarOutlined, RiseOutlined, FallOutlined, SettingOutlined
} from '@ant-design/icons'
import * as echarts from 'echarts'
import { simulationsApi as api } from '../services/api'

// 导入图表组件
import EnergyProductionChart from '../components/Charts/EnergyProductionChart'
import PowerAnalysisChart from '../components/Charts/PowerAnalysisChart'
import PerformanceAnalysisChart from '../components/Charts/PerformanceAnalysisChart'
import EconomicAnalysisChart from '../components/Charts/EconomicAnalysisChart'
import ComparisonAnalysisChart from '../components/Charts/ComparisonAnalysisChart'
import SolarPanelAnalysisChart from '../components/Charts/SolarPanelAnalysisChart'
import SolarPanelConfigPanel from '../components/SolarPanelConfigPanel'
import EconomicConfigPanel from '../components/EconomicConfigPanel'

const { Option } = Select
const { RangePicker } = DatePicker
const { TabPane } = Tabs

const Analysis = () => {
  const [simulations, setSimulations] = useState([])
  const [selectedSimulation, setSelectedSimulation] = useState(null)
  const [analysisData, setAnalysisData] = useState(null)
  const [solarPanelConfig, setSolarPanelConfig] = useState({})
  const [economicConfig, setEconomicConfig] = useState({})
  const [loading, setLoading] = useState(false)
  const [simulationResults, setSimulationResults] = useState([])

  // 获取模拟仿真结果数据
  const fetchSimulations = async () => {
    try {
      // 获取已完成的模拟任务列表
      const simulationsResponse = await api.getSimulations({ status: 'completed' })
      console.log('获取到的模拟任务列表:', simulationsResponse)
      setSimulations(simulationsResponse || [])
      
      // 为每个模拟任务获取仿真结果数据
      if (simulationsResponse && simulationsResponse.length > 0) {
        const resultsPromises = simulationsResponse.map(async (simulation) => {
          try {
            const resultsResponse = await api.getResults(simulation.id)
            console.log(`模拟 ${simulation.id} 的结果数据:`, resultsResponse)
            return {
              simulationId: simulation.id,
              simulationName: simulation.name,
              results: resultsResponse?.data || resultsResponse || [],
              totalCount: resultsResponse?.total_count || (resultsResponse?.data ? resultsResponse.data.length : 0) || (resultsResponse ? resultsResponse.length : 0),
              created_at: simulation.created_at
            }
          } catch (error) {
            console.error(`获取模拟 ${simulation.id} 的结果失败:`, error)
            return {
              simulationId: simulation.id,
              simulationName: simulation.name,
              results: [],
              totalCount: 0,
              created_at: simulation.created_at
            }
          }
        })
        
        const results = await Promise.all(resultsPromises)
        console.log('处理后的仿真结果数据:', results)
        setSimulationResults(results.filter(r => r.totalCount > 0))
      } else {
        console.log('没有找到已完成的模拟任务')
        setSimulationResults([])
      }
    } catch (error) {
      console.error('获取模拟仿真结果失败:', error)
      message.error('获取模拟仿真结果失败')
    }
  }

  // 获取分析数据
  const fetchAnalysisData = async (simulationId) => {
    setLoading(true)
    try {
      // 获取发电量数据
      const response = await api.getResults(simulationId)
      console.log('API返回的仿真结果数据:', response)
      // 处理不同的响应格式
      const data = response?.data || response || []
      setAnalysisData(data)
      
      // 获取光伏板配置数据（模拟数据）
      const solarConfig = await fetchSolarPanelConfig(simulationId)
      setSolarPanelConfig(solarConfig)
    } catch (error) {
      // API调用失败时使用模拟数据
      console.log('API调用失败，使用模拟数据:', error)
      const mockData = generateMockAnalysisData()
      setAnalysisData(mockData)
      
      // 获取光伏板配置数据（模拟数据）
      const solarConfig = await fetchSolarPanelConfig(simulationId)
      setSolarPanelConfig(solarConfig)
    } finally {
      setLoading(false)
    }
  }

  // 获取光伏板配置数据（模拟函数）
  const fetchSolarPanelConfig = async (simulationId) => {
    // 这里应该从3D场景数据中获取光伏板配置
    // 目前使用模拟数据
    return {
      panelCount: 24,
      panelArea: 1.6, // m²
      panelEfficiency: 0.21, // 21%
      panelOrientation: 'south',
      panelTilt: 30,
      totalCapacity: 8.64, // kW
      installationType: 'rooftop',
      shadingFactor: 0.05, // 5%
      temperatureCoefficient: -0.004,
      degradationRate: 0.005
    }
  }

  // 生成模拟分析数据
  const generateMockAnalysisData = () => {
    const data = []
    const now = new Date()
    
    // 生成30天的模拟数据
    for (let i = 29; i >= 0; i--) {
      const date = new Date(now)
      date.setDate(date.getDate() - i)
      
      // 模拟发电量数据（基于季节和天气变化）
      const baseEnergy = 25 + Math.sin(i * 0.2) * 10 // 基础发电量
      const weatherEffect = Math.random() * 8 - 4 // 天气影响
      const energyDaily = Math.max(5, baseEnergy + weatherEffect)
      
      // 模拟功率数据
      const powerDc = energyDaily * 1000 / 24 * (0.8 + Math.random() * 0.4)
      const powerAc = powerDc * (0.85 + Math.random() * 0.1)
      const efficiency = powerAc / powerDc
      
      data.push({
        timestamp: date.toISOString(),
        energy_daily: energyDaily,
        power_dc: powerDc,
        power_ac: powerAc,
        efficiency: efficiency
      })
    }
    
    return data
  }

  useEffect(() => {
    fetchSimulations()
    
    // 如果没有选择模拟任务，使用模拟数据
    if (!selectedSimulation) {
      console.log('初始化模拟数据')
      const mockData = generateMockAnalysisData()
      setAnalysisData(mockData)
      
      // 获取光伏板配置数据
      fetchSolarPanelConfig().then(config => {
        setSolarPanelConfig(config)
      })
    }
  }, [])

  // 模拟选择变化
  const handleSimulationChange = (simulationId) => {
    console.log('选择的模拟ID:', simulationId)
    const simulation = simulations.find(s => s.id === simulationId)
    console.log('找到的模拟任务:', simulation)
    setSelectedSimulation(simulation)
    if (simulationId) {
      // 从模拟仿真结果中获取数据
      const resultData = simulationResults.find(r => r.simulationId === simulationId)
      console.log('找到的仿真结果数据:', resultData)
      if (resultData && resultData.results && resultData.results.length > 0) {
        console.log('使用预加载的仿真结果数据')
        setAnalysisData(resultData.results)
        // 获取光伏板配置数据
        fetchSolarPanelConfig(simulationId).then(config => {
          setSolarPanelConfig(config)
        })
      } else {
        // 如果没有仿真结果数据，使用API获取
        console.log('使用API获取仿真结果数据')
        fetchAnalysisData(simulationId)
      }
    } else {
      // 如果没有选择模拟任务，使用模拟数据
      console.log('使用模拟数据')
      const mockData = generateMockAnalysisData()
      setAnalysisData(mockData)
      
      // 获取光伏板配置数据
      fetchSolarPanelConfig().then(config => {
        setSolarPanelConfig(config)
      })
    }
  }



  // 计算统计信息
  const calculateStats = () => {
    if (!analysisData || analysisData.length === 0) {
      return null
    }

    const validData = analysisData.filter(d => d.energy_daily)
    if (validData.length === 0) return null

    const totalEnergy = validData.reduce((sum, d) => sum + d.energy_daily, 0)
    const avgPower = validData.reduce((sum, d) => sum + (d.power_ac || 0), 0) / validData.length
    const maxPower = Math.max(...validData.map(d => d.power_ac || 0))
    const avgEfficiency = validData.reduce((sum, d) => sum + (d.efficiency || 0), 0) / validData.length

    return {
      totalEnergy: totalEnergy.toFixed(2),
      avgPower: avgPower.toFixed(2),
      maxPower: maxPower.toFixed(2),
      avgEfficiency: (avgEfficiency * 100).toFixed(1)
    }
  }

  const stats = calculateStats()

  return (
    <div>
      {/* 筛选条件 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col span={8}>
            <Select
              placeholder="选择模拟仿真结果"
              style={{ width: '100%' }}
              onChange={handleSimulationChange}
              value={selectedSimulation?.id}
            >
              {simulationResults.map(result => (
                <Option key={result.simulationId} value={result.simulationId}>
                  {result.simulationName} - {result.totalCount}个数据点 - {new Date(result.created_at).toLocaleDateString()}
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={8}>
            <RangePicker style={{ width: '100%' }} />
          </Col>
          <Col span={8}>
            <Space>
              <Button icon={<DownloadOutlined />}>
                导出报告
              </Button>
              <Button type="primary" icon={<EyeOutlined />}>
                查看详情
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 统计信息 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总发电量"
                value={stats.totalEnergy}
                suffix="kWh"
                prefix={<ThunderboltOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均功率"
                value={stats.avgPower}
                suffix="W"
                prefix={<BarChartOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="最大功率"
                value={stats.maxPower}
                suffix="W"
                prefix={<RiseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均效率"
                value={stats.avgEfficiency}
                suffix="%"
                prefix={<PieChartOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 光伏板配置信息 */}
      {selectedSimulation && Object.keys(solarPanelConfig).length > 0 && (
        <SolarPanelConfigPanel solarPanelConfig={solarPanelConfig} />
      )}

      {/* 分析内容 */}
      <Card>
        <Tabs defaultActiveKey="solar">
          <TabPane tab={
            <span>
              <SettingOutlined />
              光伏板分析
            </span>
          } key="solar">
            <Spin spinning={loading}>
              {analysisData && analysisData.length > 0 ? (
                <SolarPanelAnalysisChart 
                  data={analysisData} 
                  solarPanelConfig={solarPanelConfig} 
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                  <SettingOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                  <div>暂无数据，请选择仿真结果或等待数据加载</div>
                </div>
              )}
            </Spin>
          </TabPane>
          
          <TabPane tab={
            <span>
              <ThunderboltOutlined />
              发电分析
            </span>
          } key="energy">
            <Spin spinning={loading}>
              {analysisData && analysisData.length > 0 ? (
                <EnergyProductionChart data={analysisData} />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                  <ThunderboltOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                  <div>暂无数据，请选择仿真结果或等待数据加载</div>
                </div>
              )}
            </Spin>
          </TabPane>
          
          <TabPane tab={
            <span>
              <LineChartOutlined />
              功率分析
            </span>
          } key="power">
            <Spin spinning={loading}>
              {analysisData && analysisData.length > 0 ? (
                <PowerAnalysisChart data={analysisData} />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                  <LineChartOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                  <div>暂无数据，请选择仿真结果或等待数据加载</div>
                </div>
              )}
            </Spin>
          </TabPane>
          
          <TabPane tab={
            <span>
              <PieChartOutlined />
              性能分析
            </span>
          } key="performance">
            <Spin spinning={loading}>
              {analysisData && analysisData.length > 0 ? (
                <PerformanceAnalysisChart data={analysisData} />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                  <PieChartOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                  <div>暂无数据，请选择仿真结果或等待数据加载</div>
                </div>
              )}
            </Spin>
          </TabPane>
          
          <TabPane tab={
            <span>
              <DollarOutlined />
              经济分析
            </span>
          } key="economic">
            <Spin spinning={loading}>
              {/* 经济参数配置面板 */}
              <EconomicConfigPanel 
                config={economicConfig}
                onConfigChange={setEconomicConfig}
                solarPanelConfig={solarPanelConfig}
              />
              
              {/* 经济分析图表 */}
              {analysisData && analysisData.length > 0 ? (
                <EconomicAnalysisChart 
                  data={analysisData} 
                  solarPanelConfig={solarPanelConfig}
                  economicConfig={economicConfig}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                  <DollarOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                  <div>暂无数据，请选择仿真结果或等待数据加载</div>
                </div>
              )}
            </Spin>
          </TabPane>
          
          <TabPane tab={
            <span>
              <BarChartOutlined />
              对比分析
            </span>
          } key="comparison">
            <Spin spinning={loading}>
              {analysisData && analysisData.length > 0 ? (
                <ComparisonAnalysisChart data={analysisData} />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                  <BarChartOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                  <div>暂无数据，请选择仿真结果或等待数据加载</div>
                </div>
              )}
            </Spin>
          </TabPane>
        </Tabs>
      </Card>

      {/* 系统信息 */}
      {selectedSimulation && (
        <Card title="系统信息" style={{ marginTop: 24 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="模拟名称" value={selectedSimulation.name} />
            </Col>
            <Col span={6}>
              <Statistic 
                title="时间范围" 
                value={`${new Date(selectedSimulation.start_date).toLocaleDateString()} - ${new Date(selectedSimulation.end_date).toLocaleDateString()}`} 
              />
            </Col>
            <Col span={6}>
              <Statistic title="数据点数" value={analysisData?.length || 0} />
            </Col>
            <Col span={6}>
              <Statistic 
                title="光伏板数量" 
                value={solarPanelConfig.panelCount || 0} 
                suffix="块"
              />
            </Col>
          </Row>
          
          <div style={{ marginTop: 16 }}>
            <Progress 
              percent={selectedSimulation.progress || 0} 
              status={selectedSimulation.status === 'completed' ? 'success' : 'active'}
            />
          </div>
          
          {/* 光伏板配置摘要 */}
          {Object.keys(solarPanelConfig).length > 0 && (
            <div style={{ marginTop: 16, padding: 12, backgroundColor: '#f0f8ff', borderRadius: 6 }}>
              <Row gutter={16}>
                <Col span={6}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 18, fontWeight: 'bold', color: '#1890ff' }}>
                      {solarPanelConfig.panelCount}
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>光伏板数量</div>
                  </div>
                </Col>
                <Col span={6}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 18, fontWeight: 'bold', color: '#52c41a' }}>
                      {solarPanelConfig.totalCapacity}kW
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>总容量</div>
                  </div>
                </Col>
                <Col span={6}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 18, fontWeight: 'bold', color: '#faad14' }}>
                      {solarPanelConfig.panelOrientation?.toUpperCase()}
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>朝向</div>
                  </div>
                </Col>
                <Col span={6}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 18, fontWeight: 'bold', color: '#722ed1' }}>
                      {solarPanelConfig.panelTilt}°
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>倾角</div>
                  </div>
                </Col>
              </Row>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

export default Analysis