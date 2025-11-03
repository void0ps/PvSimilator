import React, { useState, useEffect } from 'react'
import {
  Table, Button, Space, Modal, Form, Input, InputNumber, Select,
  Card, Row, Col, Statistic, message, Popconfirm, Tag
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined,
  ThunderboltOutlined, DatabaseOutlined, SettingOutlined
} from '@ant-design/icons'
import { systemsApi as api } from '../services/api'

const { Option } = Select

const Systems = () => {
  const [systems, setSystems] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingSystem, setEditingSystem] = useState(null)
  const [form] = Form.useForm()

  // 获取系统列表
  const fetchSystems = async () => {
    setLoading(true)
    try {
      const response = await api.getSystems()
      setSystems(response || [])
    } catch (error) {
      message.error('获取系统列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSystems()
  }, [])

  // 创建/更新系统
  const handleSubmit = async (values) => {
    try {
      if (editingSystem) {
        await api.updateSystem(editingSystem.id, values)
        message.success('系统更新成功')
      } else {
        await api.createSystem(values)
        message.success('系统创建成功')
      }
      setModalVisible(false)
      setEditingSystem(null)
      form.resetFields()
      fetchSystems()
    } catch (error) {
      message.error('操作失败')
    }
  }

  // 删除系统
  const handleDelete = async (id) => {
    try {
      await api.deleteSystem(id)
      message.success('删除成功')
      fetchSystems()
    } catch (error) {
      message.error('删除失败')
    }
  }

  // 打开编辑模态框
  const showEditModal = (system) => {
    setEditingSystem(system)
    form.setFieldsValue(system)
    setModalVisible(true)
  }

  // 关闭模态框
  const handleCancel = () => {
    setModalVisible(false)
    setEditingSystem(null)
    form.resetFields()
  }

  // 查看系统详情（模块列表）
  const showSystemDetail = async (system) => {
    try {
      const response = await api.getModules(system.id)
      const modules = response || []
      
      Modal.info({
        title: `系统详情 - ${system.name}`,
        width: 800,
        content: (
          <div>
            <h3>系统基本信息</h3>
            <p><strong>系统名称：</strong>{system.name}</p>
            <p><strong>装机容量：</strong>{system.capacity_kw} kWp</p>
            <p><strong>组件数量：</strong>{system.module_count}</p>
            <p><strong>倾角：</strong>{system.tilt_angle}°</p>
            <p><strong>方位角：</strong>{system.azimuth}°</p>
            
            <h3 style={{ marginTop: 20 }}>光伏组件列表</h3>
            {modules.length > 0 ? (
              <Table 
                dataSource={modules}
                rowKey="id"
                pagination={false}
                size="small"
                columns={[
                  {
                    title: '厂商',
                    dataIndex: 'manufacturer',
                    key: 'manufacturer'
                  },
                  {
                    title: '型号',
                    dataIndex: 'model',
                    key: 'model'
                  },
                  {
                    title: '额定功率(W)',
                    dataIndex: 'power_rated',
                    key: 'power_rated',
                    render: (value) => <span>{value} W</span>
                  },
                  {
                    title: '最大功率电压(V)',
                    dataIndex: 'voltage_mp',
                    key: 'voltage_mp',
                    render: (value) => <span>{value} V</span>
                  },
                  {
                    title: '最大功率电流(A)',
                    dataIndex: 'current_mp',
                    key: 'current_mp',
                    render: (value) => <span>{value} A</span>
                  }
                ]}
              />
            ) : (
              <p>暂无组件数据</p>
            )}
          </div>
        ),
        onOk() {}
      })
    } catch (error) {
      message.error('获取模块列表失败')
    }
  }

  // 表格列定义
  const columns = [
    {
      title: '系统名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <ThunderboltOutlined style={{ color: '#1890ff' }} />
          <span>{text}</span>
        </Space>
      )
    },
    {
      title: '装机容量(kWp)',
      dataIndex: 'capacity_kw',
      key: 'capacity_kw',
      render: (value) => <Tag color="blue">{value} kWp</Tag>
    },
    {
      title: '组件数量',
      dataIndex: 'module_count',
      key: 'module_count'
    },
    {
      title: '倾角(度)',
      dataIndex: 'tilt_angle',
      key: 'tilt_angle'
    },
    {
      title: '方位角(度)',
      dataIndex: 'azimuth',
      key: 'azimuth'
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => (
        <Tag color="green">
          活跃
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button 
            type="link" 
            icon={<EyeOutlined />}
            onClick={() => showSystemDetail(record)}
          >
            查看
          </Button>
          <Button 
            type="link" 
            icon={<EditOutlined />}
            onClick={() => showEditModal(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除这个系统吗？"
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
    totalCapacity: systems.reduce((sum, sys) => sum + (sys.capacity_kw || 0), 0),
    totalSystems: systems.length,
    activeSystems: systems.length // 所有系统都视为活跃状态
  }

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="总系统数"
              value={stats.totalSystems}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="总装机容量"
              value={stats.totalCapacity}
              precision={2}
              suffix="kWp"
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="活跃系统"
              value={stats.activeSystems}
              prefix={<SettingOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作栏 */}
      <Card 
        title="光伏系统管理" 
        extra={
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => setModalVisible(true)}
          >
            新建系统
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={systems}
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
        title={editingSystem ? '编辑系统' : '新建系统'}
        open={modalVisible}
        onCancel={handleCancel}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="系统名称"
                name="name"
                rules={[{ required: true, message: '请输入系统名称' }]}
              >
                <Input placeholder="请输入系统名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="装机容量(kWp)"
                name="capacity_kw"
                rules={[{ required: true, message: '请输入装机容量' }]}
              >
                <InputNumber 
                  min={0.1}
                  max={10000}
                  step={0.1}
                  style={{ width: '100%' }}
                  placeholder="请输入装机容量"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="倾角(度)"
                name="tilt_angle"
                rules={[{ required: true, message: '请输入倾角' }]}
              >
                <InputNumber 
                  min={0}
                  max={90}
                  step={1}
                  style={{ width: '100%' }}
                  placeholder="请输入倾角"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="方位角(度)"
                name="azimuth"
                rules={[{ required: true, message: '请输入方位角' }]}
              >
                <InputNumber 
                  min={0}
                  max={360}
                  step={1}
                  style={{ width: '100%' }}
                  placeholder="请输入方位角"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="组件高度(m)"
                name="module_height"
                initialValue={2.0}
                rules={[{ required: true, message: '请输入组件高度' }]}
              >
                <InputNumber 
                  min={0.1}
                  max={10}
                  step={0.1}
                  style={{ width: '100%' }}
                  placeholder="请输入组件高度"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="组件长度(m)"
                name="module_length"
                initialValue={2.268}
                rules={[{ required: true, message: '请输入组件长度' }]}
              >
                <InputNumber 
                  min={0.1}
                  max={10}
                  step={0.1}
                  style={{ width: '100%' }}
                  placeholder="请输入组件长度"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="组件宽度(m)"
                name="module_width"
                initialValue={2.278}
                rules={[{ required: true, message: '请输入组件宽度' }]}
              >
                <InputNumber 
                  min={0.1}
                  max={10}
                  step={0.1}
                  style={{ width: '100%' }}
                  placeholder="请输入组件宽度"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="行间距(m)"
                name="pitch"
                initialValue={4.1}
                rules={[{ required: true, message: '请输入行间距' }]}
              >
                <InputNumber 
                  min={1}
                  max={20}
                  step={0.1}
                  style={{ width: '100%' }}
                  placeholder="请输入行间距"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="系统描述"
            name="description"
          >
            <Input.TextArea rows={4} placeholder="请输入系统描述" />
          </Form.Item>

          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={handleCancel}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingSystem ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Systems