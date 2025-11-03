import React, { useState, useEffect } from 'react'
import { Card, Row, Col, InputNumber, Slider, Select, Button, Form, Input, Divider, Space } from 'antd'
import { SettingOutlined, CalculatorOutlined, SyncOutlined } from '@ant-design/icons'

const { Option } = Select

const EconomicConfigPanel = ({ 
  config, 
  onConfigChange,
  solarPanelConfig 
}) => {
  const [form] = Form.useForm()
  const [isCustomizing, setIsCustomizing] = useState(false)

  // 默认经济参数配置
  const defaultConfig = {
    // 电价相关
    electricityPrice: 0.6, // 元/kWh
    feedInTariff: 0.4, // 上网电价
    selfConsumptionRate: 0.3, // 自用比例
    
    // 成本相关
    systemCostPerWatt: 4.5, // 元/W
    installationCost: 0, // 安装费用
    maintenanceCost: 0.02, // 维护成本比例
    insuranceCost: 0.01, // 保险成本比例
    
    // 财务参数
    discountRate: 0.08, // 折现率
    inflationRate: 0.03, // 通货膨胀率
    taxRate: 0.25, // 所得税率
    systemLifetime: 25, // 系统寿命
    degradationRate: 0.005, // 年衰减率
    
    // 补贴政策
    hasSubsidy: true,
    subsidyAmount: 0.3, // 补贴金额 元/W
    subsidyYears: 3, // 补贴年限
    
    // 贷款参数
    hasLoan: false,
    loanAmount: 0,
    loanInterestRate: 0.05,
    loanTerm: 10
  }

  useEffect(() => {
    if (config) {
      form.setFieldsValue({
        ...defaultConfig,
        ...config
      })
    }
  }, [config, form])

  // 计算系统总成本
  const calculateSystemCost = () => {
    const systemCapacity = solarPanelConfig?.totalCapacity || 8.64 // kW
    const costPerWatt = form.getFieldValue('systemCostPerWatt') || defaultConfig.systemCostPerWatt
    const installationCost = form.getFieldValue('installationCost') || defaultConfig.installationCost
    
    return Math.round(systemCapacity * 1000 * costPerWatt + installationCost)
  }

  // 计算年度收益
  const calculateAnnualRevenue = () => {
    const systemCapacity = solarPanelConfig?.totalCapacity || 8.64 // kW
    const annualGeneration = systemCapacity * 1000 * 4 // 假设年等效发电小时数
    const electricityPrice = form.getFieldValue('electricityPrice') || defaultConfig.electricityPrice
    const selfConsumptionRate = form.getFieldValue('selfConsumptionRate') || defaultConfig.selfConsumptionRate
    const feedInTariff = form.getFieldValue('feedInTariff') || defaultConfig.feedInTariff
    
    const selfConsumptionRevenue = annualGeneration * selfConsumptionRate * electricityPrice
    const feedInRevenue = annualGeneration * (1 - selfConsumptionRate) * feedInTariff
    
    return Math.round(selfConsumptionRevenue + feedInRevenue)
  }

  // 计算年度成本
  const calculateAnnualCost = () => {
    const systemCost = calculateSystemCost()
    const maintenanceRate = form.getFieldValue('maintenanceCost') || defaultConfig.maintenanceCost
    const insuranceRate = form.getFieldValue('insuranceCost') || defaultConfig.insuranceCost
    
    const maintenanceCost = systemCost * maintenanceRate
    const insuranceCost = systemCost * insuranceRate
    
    return Math.round(maintenanceCost + insuranceCost)
  }

  // 处理配置变化
  const handleValuesChange = (changedValues, allValues) => {
    if (onConfigChange) {
      onConfigChange({
        ...defaultConfig,
        ...allValues
      })
    }
  }

  // 重置为默认配置
  const handleReset = () => {
    form.setFieldsValue(defaultConfig)
    if (onConfigChange) {
      onConfigChange(defaultConfig)
    }
  }

  // 快速配置预设
  const applyPreset = (presetName) => {
    const presets = {
      residential: {
        electricityPrice: 0.6,
        selfConsumptionRate: 0.7,
        systemCostPerWatt: 4.5,
        hasSubsidy: true
      },
      commercial: {
        electricityPrice: 0.8,
        selfConsumptionRate: 0.4,
        systemCostPerWatt: 4.0,
        hasSubsidy: false
      },
      industrial: {
        electricityPrice: 1.0,
        selfConsumptionRate: 0.2,
        systemCostPerWatt: 3.5,
        hasSubsidy: false
      }
    }
    
    const preset = presets[presetName]
    if (preset) {
      form.setFieldsValue({
        ...defaultConfig,
        ...preset
      })
      if (onConfigChange) {
        onConfigChange({
          ...defaultConfig,
          ...preset
        })
      }
    }
  }

  const systemCost = calculateSystemCost()
  const annualRevenue = calculateAnnualRevenue()
  const annualCost = calculateAnnualCost()
  const annualProfit = annualRevenue - annualCost

  return (
    <Card 
      title={
        <Space>
          <SettingOutlined />
          经济参数配置
        </Space>
      }
      extra={
        <Space>
          <Button 
            size="small" 
            onClick={() => setIsCustomizing(!isCustomizing)}
            icon={<SettingOutlined />}
          >
            {isCustomizing ? '简化视图' : '详细配置'}
          </Button>
          <Button 
            size="small" 
            onClick={handleReset}
            icon={<SyncOutlined />}
          >
            重置
          </Button>
        </Space>
      }
      style={{ marginBottom: 24 }}
    >
      {/* 快速配置预设 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Space>
            <span>快速配置:</span>
            <Button size="small" onClick={() => applyPreset('residential')}>住宅</Button>
            <Button size="small" onClick={() => applyPreset('commercial')}>商业</Button>
            <Button size="small" onClick={() => applyPreset('industrial')}>工业</Button>
          </Space>
        </Col>
      </Row>

      {/* 经济指标概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <div style={{ textAlign: 'center', padding: 12, backgroundColor: '#f0f8ff', borderRadius: 6 }}>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#1890ff' }}>
              {systemCost.toLocaleString()}元
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>系统总投资</div>
          </div>
        </Col>
        <Col span={6}>
          <div style={{ textAlign: 'center', padding: 12, backgroundColor: '#f6ffed', borderRadius: 6 }}>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#52c41a' }}>
              {annualRevenue.toLocaleString()}元
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>年收益</div>
          </div>
        </Col>
        <Col span={6}>
          <div style={{ textAlign: 'center', padding: 12, backgroundColor: '#fff2e8', borderRadius: 6 }}>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#fa8c16' }}>
              {annualCost.toLocaleString()}元
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>年成本</div>
          </div>
        </Col>
        <Col span={6}>
          <div style={{ textAlign: 'center', padding: 12, backgroundColor: '#f9f0ff', borderRadius: 6 }}>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#722ed1' }}>
              {annualProfit.toLocaleString()}元
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>年利润</div>
          </div>
        </Col>
      </Row>

      <Form
        form={form}
        layout="vertical"
        onValuesChange={handleValuesChange}
        initialValues={defaultConfig}
      >
        {isCustomizing ? (
          <>
            {/* 详细配置 */}
            <Divider orientation="left">电价配置</Divider>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="电价 (元/kWh)" name="electricityPrice">
                  <InputNumber 
                    min={0.1} 
                    max={2} 
                    step={0.01} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="上网电价 (元/kWh)" name="feedInTariff">
                  <InputNumber 
                    min={0.1} 
                    max={1} 
                    step={0.01} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="自用比例" name="selfConsumptionRate">
                  <Slider 
                    min={0} 
                    max={1} 
                    step={0.01} 
                    tipFormatter={value => `${(value * 100).toFixed(0)}%`}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Divider orientation="left">成本配置</Divider>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="系统成本 (元/W)" name="systemCostPerWatt">
                  <InputNumber 
                    min={2} 
                    max={10} 
                    step={0.1} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="安装费用 (元)" name="installationCost">
                  <InputNumber 
                    min={0} 
                    max={100000} 
                    step={1000} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="维护成本比例" name="maintenanceCost">
                  <Slider 
                    min={0} 
                    max={0.1} 
                    step={0.001} 
                    tipFormatter={value => `${(value * 100).toFixed(1)}%`}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Divider orientation="left">财务参数</Divider>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item label="折现率" name="discountRate">
                  <Slider 
                    min={0.01} 
                    max={0.15} 
                    step={0.01} 
                    tipFormatter={value => `${(value * 100).toFixed(1)}%`}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="通货膨胀率" name="inflationRate">
                  <Slider 
                    min={0} 
                    max={0.1} 
                    step={0.001} 
                    tipFormatter={value => `${(value * 100).toFixed(1)}%`}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="系统寿命 (年)" name="systemLifetime">
                  <InputNumber 
                    min={10} 
                    max={40} 
                    step={1} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="年衰减率" name="degradationRate">
                  <Slider 
                    min={0} 
                    max={0.02} 
                    step={0.001} 
                    tipFormatter={value => `${(value * 100).toFixed(1)}%`}
                  />
                </Form.Item>
              </Col>
            </Row>
          </>
        ) : (
          <>
            {/* 简化配置 */}
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="电价 (元/kWh)" name="electricityPrice">
                  <InputNumber 
                    min={0.1} 
                    max={2} 
                    step={0.01} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="系统成本 (元/W)" name="systemCostPerWatt">
                  <InputNumber 
                    min={2} 
                    max={10} 
                    step={0.1} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="自用比例" name="selfConsumptionRate">
                  <Slider 
                    min={0} 
                    max={1} 
                    step={0.01} 
                    tipFormatter={value => `${(value * 100).toFixed(0)}%`}
                  />
                </Form.Item>
              </Col>
            </Row>
          </>
        )}
      </Form>
    </Card>
  )
}

export default EconomicConfigPanel