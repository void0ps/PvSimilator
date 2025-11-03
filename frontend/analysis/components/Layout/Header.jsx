import React from 'react'
import { Layout, Typography, Space } from 'antd'
import { SunOutlined } from '@ant-design/icons'

const { Header: AntHeader } = Layout
const { Title } = Typography

const Header = () => {
  return (
    <AntHeader style={{ 
      background: '#001529', 
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }}>
      <Space>
        <SunOutlined style={{ fontSize: '24px', color: '#fff' }} />
        <Title level={3} style={{ color: '#fff', margin: 0 }}>
          光伏仿真软件
        </Title>
      </Space>
      
      <Space>
        <span style={{ color: '#fff' }}>专业的光伏系统仿真平台</span>
      </Space>
    </AntHeader>
  )
}

export default Header