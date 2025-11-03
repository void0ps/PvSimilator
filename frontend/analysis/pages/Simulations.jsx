import React, { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import {
  Table, Button, Space, Modal, Form, Input, Select, DatePicker,
  Card, Row, Col, Statistic, message, Popconfirm, Tag, Progress,
  Steps, Timeline, Descriptions, Checkbox, Divider, Spin, Alert, List
} from 'antd'
import {
  PlayCircleOutlined, PauseCircleOutlined, PlusOutlined,
  EditOutlined, DeleteOutlined, EyeOutlined, FileTextOutlined,
  BarChartOutlined, ClockCircleOutlined, CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons'
import { simulationsApi as api } from '../services/api'
import { systemsApi as systemsApi } from '../services/api'

const { Option } = Select
const { RangePicker } = DatePicker
const { Step } = Steps

const Simulations = () => {
  const [simulations, setSimulations] = useState([])
  const [systems, setSystems] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedSimulation, setSelectedSimulation] = useState(null)
  const [editingSimulation, setEditingSimulation] = useState(null)
  const [shadingData, setShadingData] = useState(null)
  const [shadingLoading, setShadingLoading] = useState(false)
  const [form] = Form.useForm()

  // 获取模拟列表
  const fetchSimulations = async () => {
    setLoading(true)
    try {
      const response = await api.getSimulations()
      setSimulations(response || [])
    } catch (error) {
      message.error('获取模拟列表失败')
    } finally {
      setLoading(false)
    }
  }

  // 获取系统列表（用于关联模拟任务）
  const fetchSystems = async () => {
    try {
      const response = await systemsApi.getSystems()
      setSystems(response || [])
    } catch (error) {
      message.error('获取系统列表失败')
    }
  }

  useEffect(() => {
    fetchSimulations()
    fetchSystems()
  }, [])

  // 创建/更新模拟
  const handleSubmit = async (values) => {
    try {
      // 处理日期范围字段，将dateRange转换为start_date和end_date
      const processedValues = {
        ...values,
        start_date: values.dateRange ? values.dateRange[0].format('YYYY-MM-DDTHH:mm:ss') : null,
        end_date: values.dateRange ? values.dateRange[1].format('YYYY-MM-DDTHH:mm:ss') : null
      }
      
      // 删除dateRange字段，避免后端验证错误
      delete processedValues.dateRange
      
      if (editingSimulation) {
        await api.updateSimulation(editingSimulation.id, processedValues)
        message.success('模拟更新成功')
      } else {
        await api.createSimulation(processedValues)
        message.success('模拟创建成功')
      }
      setModalVisible(false)
      setEditingSimulation(null)
      form.resetFields()
      fetchSimulations()
    } catch (error) {
      message.error('操作失败')
    }
  }

  // 删除模拟
  const handleDelete = async (id) => {
    try {
      await api.deleteSimulation(id)
      message.success('删除成功')
      fetchSimulations()
    } catch (error) {
      message.error('删除失败')
    }
  }

  // 开始模拟
  const handleStart = async (id) => {
    try {
      await api.updateSimulation(id, { status: 'running' })
      message.success('模拟已开始')
      fetchSimulations()
    } catch (error) {
      message.error('启动失败')
    }
  }

  // 暂停模拟
  const handlePause = async (id) => {
    try {
      await api.updateSimulation(id, { status: 'paused' })
      message.success('模拟已暂停')
      fetchSimulations()
    } catch (error) {
      message.error('暂停失败')
    }
  }

  // 查看详情
  const showDetail = (simulation) => {
    setSelectedSimulation(simulation)
    setDetailVisible(true)
  }

  const resetDetail = () => {
    setShadingData(null)
    setShadingLoading(false)
  }

  // 打开编辑模态框
  const showEditModal = (simulation) => {
    setEditingSimulation(simulation)
    form.setFieldsValue({
      ...simulation,
      dateRange: simulation.start_date && simulation.end_date ? [dayjs(simulation.start_date), dayjs(simulation.end_date)] : null
    })
    setModalVisible(true)
  }

  // 关闭模态框
  const handleCancel = () => {
    setModalVisible(false)
    setDetailVisible(false)
    setEditingSimulation(null)
    setSelectedSimulation(null)
    resetDetail()
    form.resetFields()
  }

  // 获取遮挡数据
  const fetchShadingData = async (simulationId) => {
    setShadingLoading(true)
    try {
      const response = await api.getShading(simulationId)
      setShadingData(response)
    } catch (error) {
      message.error('获取遮挡数据失败')
    } finally {
      setShadingLoading(false)
    }
  }

  useEffect(() => {
    if (detailVisible && selectedSimulation?.id && selectedSimulation.include_shading) {
      fetchShadingData(selectedSimulation.id)
    }
  }, [detailVisible, selectedSimulation])

  // 状态标签
  const statusTag = (status, progress) => {
    const statusConfig = {
      pending: { color: 'orange', text: '等待中', icon: <ClockCircleOutlined /> },
      running: { color: 'blue', text: '运行中', icon: <PlayCircleOutlined /> },
      paused: { color: 'yellow', text: '已暂停', icon: <PauseCircleOutlined /> },
      completed: { color: 'green', text: '已完成', icon: <CheckCircleOutlined /> },
      failed: { color: 'red', text: '失败', icon: <CloseCircleOutlined /> }
    }
    
    const config = statusConfig[status] || statusConfig.pending
    
    return (
      <Space>
        <Tag color={config.color} icon={config.icon}>
          {config.text}
        </Tag>
        {status === 'running' && (
          <Progress percent={progress || 0} size="small" style={{ width: 80 }} />
        )}
      </Space>
    )
  }

  // 表格列定义
  const columns = [
    {
      title: '模拟名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <FileTextOutlined style={{ color: '#1890ff' }} />
          <span>{text}</span>
        </Space>
      )
    },
    {
      title: '关联系统',
      dataIndex: 'system_id',
      key: 'system_id',
      render: (systemId) => {
        const system = systems.find(s => s.id === systemId)
        return system ? system.name : '未知系统'
      }
    },
    {
      title: '时间范围',
      key: 'date_range',
      render: (_, record) => (
        <span>
          {new Date(record.start_date).toLocaleDateString()} - {new Date(record.end_date).toLocaleDateString()}
        </span>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status, record) => statusTag(status, record.progress)
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button 
            type="link" 
            icon={<EyeOutlined />}
            onClick={() => showDetail(record)}
          >
            详情
          </Button>
          <Button 
            type="link" 
            icon={<EditOutlined />}
            onClick={() => showEditModal(record)}
          >
            编辑
          </Button>
          {record.status === 'pending' && (
            <Button 
              type="link" 
              icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record.id)}
            >
              开始
            </Button>
          )}
          {record.status === 'running' && (
            <Button 
              type="link" 
              icon={<PauseCircleOutlined />}
              onClick={() => handlePause(record.id)}
            >
              暂停
            </Button>
          )}
          <Popconfirm
            title="确定删除这个模拟吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  // 统计信息
  const stats = {
    totalSimulations: simulations.length,
    runningSimulations: simulations.filter(sim => sim.status === 'running').length,
    completedSimulations: simulations.filter(sim => sim.status === 'completed').length
  }

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="总模拟数"
              value={stats.totalSimulations}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="运行中"
              value={stats.runningSimulations}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="已完成"
              value={stats.completedSimulations}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作栏 */}
      <Card 
        title="仿真模拟管理" 
        extra={
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => setModalVisible(true)}
          >
            新建模拟
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={simulations}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true
          }}
        />
      </Card>

      {/* 创建/编辑模态框 */}
      <Modal
        title={editingSimulation ? '编辑模拟' : '新建模拟'}
        open={modalVisible}
        onCancel={handleCancel}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="模拟名称"
                name="name"
                rules={[{ required: true, message: '请输入模拟名称' }]}
              >
                <Input placeholder="请输入模拟名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="关联系统"
                name="system_id"
                rules={[{ required: true, message: '请选择关联系统' }]}
              >
                <Select placeholder="请选择系统">
                  {systems.map(system => (
                    <Option key={system.id} value={system.id}>
                      {system.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="时间范围"
            name="dateRange"
            rules={[{ required: true, message: '请选择时间范围' }]}
          >
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="时间分辨率"
                name="time_resolution"
                initialValue="hourly"
              >
                <Select>
                  <Option value="hourly">小时级</Option>
                  <Option value="daily">日级</Option>
                  <Option value="monthly">月级</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="气象数据源"
                name="weather_source"
                initialValue="nasa_sse"
              >
                <Select>
                  <Option value="nasa_sse">NASA SSE</Option>
                  <Option value="meteonorm">Meteonorm</Option>
                  <Option value="custom">自定义</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="模拟描述"
            name="description"
          >
            <Input.TextArea rows={4} placeholder="请输入模拟描述" />
          </Form.Item>

          {/* 高级功能配置 */}
          <Card title="高级功能配置" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item
                  label="包含阴影分析"
                  name="include_shading"
                  valuePropName="checked"
                  initialValue={false}
                >
                  <Checkbox>启用阴影分析</Checkbox>
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item
                  label="包含污秽损失"
                  name="include_soiling"
                  valuePropName="checked"
                  initialValue={false}
                >
                  <Checkbox>启用污秽损失</Checkbox>
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item
                  label="包含衰减分析"
                  name="include_degradation"
                  valuePropName="checked"
                  initialValue={false}
                >
                  <Checkbox>启用衰减分析</Checkbox>
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item
                  label="阴影损失系数"
                  name="shading_factor"
                  initialValue={0.0}
                >
                  <Input type="number" step={0.01} min={0} max={1} placeholder="0-1之间" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item
                  label="污秽损失系数"
                  name="soiling_loss"
                  initialValue={0.0}
                >
                  <Input type="number" step={0.01} min={0} max={1} placeholder="0-1之间" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item
                  label="年衰减率"
                  name="degradation_rate"
                  initialValue={0.0}
                >
                  <Input type="number" step={0.001} min={0} max={0.1} placeholder="0-0.1之间" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item
                  label="通货膨胀率"
                  name="inflation_rate"
                  initialValue={0.03}
                >
                  <Input type="number" step={0.01} min={0} max={1} placeholder="0-1之间" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item
                  label="贴现率"
                  name="discount_rate"
                  initialValue={0.08}
                >
                  <Input type="number" step={0.01} min={0} max={1} placeholder="0-1之间" />
                </Form.Item>
              </Col>
            </Row>
            
            {/* 障碍物配置 */}
            <Row gutter={16}>
              <Col span={24}>
                <Form.Item
                  label="障碍物配置"
                  name="obstacles"
                >
                  <Input.TextArea 
                    rows={3} 
                    placeholder='请输入障碍物配置，格式：[{"type": "building", "height": 10, "distance": 20}]' 
                  />
                </Form.Item>
              </Col>
            </Row>
            
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  label="初始投资成本(元)"
                  name="capex"
                >
                  <Input type="number" min={0} placeholder="请输入投资成本" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  label="运维成本比例"
                  name="opex_percentage"
                  initialValue={0.02}
                >
                  <Input type="number" step={0.01} min={0} max={1} placeholder="0-1之间" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  label="电价(元/kWh)"
                  name="electricity_price"
                  initialValue={0.5}
                >
                  <Input type="number" step={0.01} min={0} placeholder="请输入电价" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={handleCancel}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingSimulation ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情模态框 */}
      <Modal
        title="模拟详情"
        open={detailVisible}
        onCancel={handleCancel}
        footer={[
          <Button key="close" onClick={handleCancel}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {selectedSimulation && (
          <div>
            <Descriptions title="基本信息" bordered column={2}>
              <Descriptions.Item label="模拟名称">{selectedSimulation.name}</Descriptions.Item>
              <Descriptions.Item label="状态">
                {statusTag(selectedSimulation.status, selectedSimulation.progress)}
              </Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {new Date(selectedSimulation.start_date).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="结束时间">
                {new Date(selectedSimulation.end_date).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="时间分辨率">{selectedSimulation.time_resolution}</Descriptions.Item>
              <Descriptions.Item label="气象数据源">{selectedSimulation.weather_source}</Descriptions.Item>
            </Descriptions>
            
            <div style={{ marginTop: 24 }}>
              <Steps
                current={selectedSimulation.status === 'completed' ? 3 : 
                        selectedSimulation.status === 'running' ? 1 : 0}
                size="small"
              >
                <Step title="等待中" description="模拟任务已创建" />
                <Step title="运行中" description="正在进行计算" />
                <Step title="已完成" description="模拟计算完成" />
              </Steps>
            </div>

            {selectedSimulation.include_shading && (
              <Card
                title="地形遮挡分析"
                style={{ marginTop: 24 }}
              >
                {shadingLoading ? (
                  <div style={{ textAlign: 'center', padding: '24px 0' }}>
                    <Spin />
                  </div>
                ) : shadingData ? (
                  <>
                    <Alert
                      type="info"
                      message={`遮挡数据点数：${shadingData.count || 0}`}
                      description={
                        shadingData.summary ? (
                          <Space direction="vertical">
                            {shadingData.summary.mean_terrain_shading !== undefined && (
                              <span>平均 terrain 遮挡乘数：{(shadingData.summary.mean_terrain_shading * 100).toFixed(2)}%</span>
                            )}
                            {shadingData.summary.min_terrain_shading !== undefined && shadingData.summary.max_terrain_shading !== undefined && (
                              <span>范围：{(shadingData.summary.min_terrain_shading * 100).toFixed(2)}% ~ {(shadingData.summary.max_terrain_shading * 100).toFixed(2)}%</span>
                            )}
                          </Space>
                        ) : '暂无摘要数据'
                      }
                      showIcon
                    />

                    <Divider orientation="left">前 10 条遮挡记录</Divider>
                    <List
                      dataSource={(shadingData.series || []).slice(0, 10)}
                      locale={{ emptyText: '暂无遮挡记录' }}
                      renderItem={(item) => (
                        <List.Item>
                          <List.Item.Meta
                            title={new Date(item.timestamp).toLocaleString()}
                            description={`terrain乘数: ${item.terrain_shading_multiplier !== undefined ? (item.terrain_shading_multiplier * 100).toFixed(1) + '%' : '—'} | 综合乘数: ${item.shading_multiplier !== undefined ? (item.shading_multiplier * 100).toFixed(1) + '%' : '—'} | AC功率: ${item.power_ac ? item.power_ac.toFixed(1) : '—'} W`}
                          />
                        </List.Item>
                      )}
                    />
                  </>
                ) : (
                  <Alert type="warning" message="暂无遮挡数据" showIcon />
                )}
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default Simulations