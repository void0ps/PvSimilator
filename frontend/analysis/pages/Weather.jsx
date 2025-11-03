import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Table, Button, Space, Modal, Form, Input, InputNumber, Select,
  Card, Row, Col, Statistic, message, Popconfirm, Tag, Tabs,
  DatePicker, Divider, Descriptions, Progress
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined,
  EnvironmentOutlined, CloudOutlined, SunOutlined,
  DownloadOutlined, UploadOutlined, SyncOutlined
} from '@ant-design/icons'
import { weatherApi as api } from '../services/api'

const { Option } = Select
const { TabPane } = Tabs

const Weather = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [locations, setLocations] = useState([])
  const [weatherData, setWeatherData] = useState([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'locations')
  const [locationModalVisible, setLocationModalVisible] = useState(false)
  const [dataModalVisible, setDataModalVisible] = useState(false)
  const [editingLocation, setEditingLocation] = useState(null)
  const [currentPageSize, setCurrentPageSize] = useState(10)
  const [form] = Form.useForm()

  // 获取位置列表
  const fetchLocations = async () => {
    setLoading(true)
    try {
      const response = await api.getLocations()
      setLocations(response || [])
    } catch (error) {
      message.error('获取位置列表失败')
    } finally {
      setLoading(false)
    }
  }

  // 获取气象数据
  const fetchWeatherData = async (limit = 1000) => {
    try {
      const response = await api.getWeatherData({ limit })
      // 后端返回的数据结构是 { data_count: number, weather_data: array }
      setWeatherData(response?.weather_data || [])
    } catch (error) {
      message.error('获取气象数据失败')
    }
  }

  // 处理分页变化
  const handleTableChange = (pagination) => {
    const { pageSize } = pagination
    // 当切换每页显示条数时，更新状态但不重新获取数据
    // 前端分页由Ant Design Table组件自动处理
    if (pageSize !== currentPageSize) {
      setCurrentPageSize(pageSize)
    }
  }

  // 处理标签页切换
  const handleTabChange = (tabKey) => {
    setActiveTab(tabKey)
    // 更新URL参数
    setSearchParams({ tab: tabKey })
  }

  useEffect(() => {
    fetchLocations()
    fetchWeatherData(1000) // 获取1000条数据以支持分页
  }, [])

  // 创建/更新位置
  const handleLocationSubmit = async (values) => {
    try {
      if (editingLocation) {
        await api.updateLocation(editingLocation.id, values)
        message.success('位置更新成功')
      } else {
        await api.createLocation(values)
        message.success('位置创建成功')
      }
      setLocationModalVisible(false)
      setEditingLocation(null)
      form.resetFields()
      fetchLocations()
    } catch (error) {
      message.error('操作失败')
    }
  }

  // 删除位置
  const handleDeleteLocation = async (id) => {
    try {
      await api.deleteLocation(id)
      message.success('删除成功')
      fetchLocations()
    } catch (error) {
      message.error('删除失败')
    }
  }

  // 获取气象数据
  const handleFetchWeatherData = async (locationId) => {
    try {
      message.loading('正在获取气象数据...', 0)
      await api.getWeatherData({ location_id: locationId })
      message.destroy()
      message.success('气象数据获取成功')
      fetchWeatherData()
    } catch (error) {
      message.destroy()
      message.error('获取气象数据失败')
    }
  }

  // 计算太阳位置
  const handleCalculateSolarPosition = async (location) => {
    try {
      const currentDate = new Date()
      // 格式化时间为 HH:MM:SS 格式
      const hours = currentDate.getHours().toString().padStart(2, '0')
      const minutes = currentDate.getMinutes().toString().padStart(2, '0')
      const seconds = currentDate.getSeconds().toString().padStart(2, '0')
      const timeString = `${hours}:${minutes}:${seconds}`
      
      const response = await api.getSolarPosition({
        latitude: location.latitude,
        longitude: location.longitude,
        date: currentDate.toISOString().split('T')[0],
        time: timeString,
        timezone: 'Asia/Shanghai'
      })
      
      // 获取第一个太阳位置数据（当前时间的计算结果）
      const solarData = response.solar_positions && response.solar_positions.length > 0 
        ? response.solar_positions[0] 
        : null
      
      if (solarData) {
        Modal.info({
          title: `太阳位置计算结果 - ${location.name}`,
          content: (
            <Descriptions column={1}>
              <Descriptions.Item label="方位角">{solarData.solar_azimuth.toFixed(2)}°</Descriptions.Item>
              <Descriptions.Item label="高度角">{solarData.solar_elevation.toFixed(2)}°</Descriptions.Item>
              <Descriptions.Item label="天顶角">{solarData.solar_zenith.toFixed(2)}°</Descriptions.Item>
              {solarData.sunrise && (
                <Descriptions.Item label="日出时间">
                  {new Date(solarData.sunrise).toLocaleString()}
                </Descriptions.Item>
              )}
              {solarData.sunset && (
                <Descriptions.Item label="日落时间">
                  {new Date(solarData.sunset).toLocaleString()}
                </Descriptions.Item>
              )}
            </Descriptions>
          ),
          width: 500
        })
      } else {
        message.error('未获取到太阳位置数据')
      }
    } catch (error) {
      message.error('计算太阳位置失败')
    }
  }

  // 打开编辑位置模态框
  const showEditLocationModal = (location) => {
    setEditingLocation(location)
    form.setFieldsValue(location)
    setLocationModalVisible(true)
  }

  // 关闭模态框
  const handleCancel = () => {
    setLocationModalVisible(false)
    setDataModalVisible(false)
    setEditingLocation(null)
    form.resetFields()
  }

  // 位置表格列定义
  const locationColumns = [
    {
      title: '位置名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (text, record) => (
        <Space>
          <EnvironmentOutlined style={{ color: '#52c41a' }} />
          <span>{text}</span>
        </Space>
      )
    },
    {
      title: '经纬度',
      key: 'coordinates',
      render: (_, record) => (
        <span>
          {record.latitude.toFixed(4)}°, {record.longitude.toFixed(4)}°
        </span>
      )
    },
    {
      title: '海拔',
      dataIndex: 'altitude',
      key: 'altitude',
      sorter: (a, b) => (a.altitude || 0) - (b.altitude || 0),
      render: (value) => value ? `${value}m` : '未知'
    },
    {
      title: '时区',
      dataIndex: 'timezone',
      key: 'timezone',
      sorter: (a, b) => a.timezone.localeCompare(b.timezone)
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => (
        <Space>
          <Tag color="green">
            <CloudOutlined /> 可用
          </Tag>
          <Button 
            type="link" 
            size="small"
            onClick={() => handleCalculateSolarPosition(record)}
          >
            太阳位置
          </Button>
        </Space>
      )
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button 
            type="link" 
            icon={<SyncOutlined />}
            onClick={() => handleFetchWeatherData(record.id)}
          >
            更新数据
          </Button>
          <Button 
            type="link" 
            icon={<EditOutlined />}
            onClick={() => showEditLocationModal(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除这个位置吗？"
            onConfirm={() => handleDeleteLocation(record.id)}
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

  // 气象数据表格列定义
  const weatherColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      sorter: (a, b) => new Date(a.timestamp) - new Date(b.timestamp),
      render: (date) => new Date(date).toLocaleString()
    },
    {
      title: '位置',
      key: 'location',
      sorter: (a, b) => {
        const locationA = locations.find(loc => loc.id === a.location_id)
        const locationB = locations.find(loc => loc.id === b.location_id)
        const nameA = locationA ? locationA.name : ''
        const nameB = locationB ? locationB.name : ''
        return nameA.localeCompare(nameB)
      },
      render: (_, record) => {
        const location = locations.find(loc => loc.id === record.location_id)
        return location ? location.name : '未知位置'
      }
    },
    {
      title: '温度(°C)',
      dataIndex: 'temperature',
      key: 'temperature',
      sorter: (a, b) => (a.temperature || 0) - (b.temperature || 0),
      render: (value) => value ? `${value.toFixed(1)}°C` : '-'
    },
    {
      title: '总辐射(W/m²)',
      dataIndex: 'ghi',
      key: 'ghi',
      sorter: (a, b) => (a.ghi || 0) - (b.ghi || 0),
      render: (value) => value ? `${value.toFixed(1)}` : '-'
    },
    {
      title: '直接辐射(W/m²)',
      dataIndex: 'dni',
      key: 'dni',
      sorter: (a, b) => (a.dni || 0) - (b.dni || 0),
      render: (value) => value ? `${value.toFixed(1)}` : '-'
    },
    {
      title: '风速(m/s)',
      dataIndex: 'wind_speed',
      key: 'wind_speed',
      sorter: (a, b) => (a.wind_speed || 0) - (b.wind_speed || 0),
      render: (value) => value ? `${value.toFixed(1)}` : '-'
    }
  ]

  // 统计信息
  const stats = {
    totalLocations: locations.length,
    totalWeatherData: weatherData.length,
    dataCoverage: locations.length > 0 ? (weatherData.length / (locations.length * 365)).toFixed(2) : 0
  }

  // 当前时间状态
  const [currentTime, setCurrentTime] = useState(new Date())

  // 更新时间
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="当前时间"
              value={currentTime.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
              })}
              prefix={<SunOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="位置数量"
              value={stats.totalLocations}
              prefix={<EnvironmentOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="气象数据量"
              value={stats.totalWeatherData}
              prefix={<CloudOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="数据覆盖率"
              value={stats.dataCoverage}
              suffix="%"
              prefix={<SunOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 标签页 */}
      <Card>
        <Tabs activeKey={activeTab} onChange={handleTabChange}>
          <TabPane tab="位置管理" key="locations">
            <div style={{ marginBottom: 16, textAlign: 'right' }}>
              <Button 
                type="primary" 
                icon={<PlusOutlined />}
                onClick={() => setLocationModalVisible(true)}
              >
                添加位置
              </Button>
            </div>
            
            <Table
              columns={locationColumns}
              dataSource={locations}
              rowKey="id"
              loading={loading}
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true
              }}
            />
          </TabPane>
          
          <TabPane tab="气象数据" key="weather">
            <div style={{ marginBottom: 16, textAlign: 'right' }}>
              <Space>
                <Button icon={<DownloadOutlined />}>
                  导出数据
                </Button>
                <Button icon={<UploadOutlined />}>
                  导入数据
                </Button>
                <Button 
                  icon={<SyncOutlined />}
                  onClick={fetchWeatherData}
                >
                  刷新数据
                </Button>
              </Space>
            </div>
            
            <Table
              columns={weatherColumns}
              dataSource={weatherData}
              rowKey="id"
              pagination={{
                pageSize: currentPageSize,
                showSizeChanger: true,
                showQuickJumper: true
              }}
              onChange={handleTableChange}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 位置创建/编辑模态框 */}
      <Modal
        title={editingLocation ? '编辑位置' : '添加位置'}
        open={locationModalVisible}
        onCancel={handleCancel}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleLocationSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="位置名称"
                name="name"
                rules={[{ required: true, message: '请输入位置名称' }]}
              >
                <Input placeholder="请输入位置名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="国家"
                name="country"
              >
                <Input placeholder="请输入国家" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="省份"
                name="province"
              >
                <Input placeholder="请输入省份" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="城市"
                name="city"
              >
                <Input placeholder="请输入城市" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="时区"
                name="timezone"
                initialValue="UTC+8"
              >
                <Select>
                  <Option value="UTC+8">UTC+8 (北京时间)</Option>
                  <Option value="UTC+0">UTC+0 (格林威治时间)</Option>
                  <Option value="UTC-5">UTC-5 (美国东部时间)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="纬度"
                name="latitude"
                rules={[{ required: true, message: '请输入纬度' }]}
              >
                <InputNumber 
                  min={-90}
                  max={90}
                  step={0.0001}
                  style={{ width: '100%' }}
                  placeholder="请输入纬度"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="经度"
                name="longitude"
                rules={[{ required: true, message: '请输入经度' }]}
              >
                <InputNumber 
                  min={-180}
                  max={180}
                  step={0.0001}
                  style={{ width: '100%' }}
                  placeholder="请输入经度"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="海拔高度(m)"
            name="altitude"
          >
            <InputNumber 
              min={0}
              max={10000}
              step={1}
              style={{ width: '100%' }}
              placeholder="请输入海拔高度"
            />
          </Form.Item>

          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={handleCancel}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingLocation ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Weather