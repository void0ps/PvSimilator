// Analysis.jsx 调试脚本
// 用于诊断腾讯云上图形无法生成的问题

// 1. 检查ECharts库是否正常加载
console.log('ECharts版本:', echarts ? echarts.version : '未加载')

// 2. 检查API连接状态
async function testAPI() {
    try {
        const response = await fetch('/api/v1/simulations/')
        console.log('API连接状态:', response.status)
        if (response.ok) {
            const data = await response.json()
            console.log('模拟任务列表:', data)
        }
    } catch (error) {
        console.error('API连接失败:', error)
    }
}

// 3. 检查图表容器
function checkChartContainers() {
    const containers = document.querySelectorAll('[class*="chart"]')
    console.log('图表容器数量:', containers.length)
    containers.forEach((container, index) => {
        console.log(`容器${index}:`, {
            id: container.id,
            className: container.className,
            dimensions: {
                width: container.offsetWidth,
                height: container.offsetHeight
            }
        })
    })
}

// 4. 模拟数据生成测试
function testMockData() {
    const mockData = generateMockAnalysisData()
    console.log('模拟数据生成测试:', {
        数据量: mockData.length,
        第一条数据: mockData[0],
        最后一条数据: mockData[mockData.length - 1]
    })
    return mockData
}

// 5. 图表渲染测试
function testChartRendering() {
    const testOption = {
        title: { text: '测试图表' },
        xAxis: { data: ['A', 'B', 'C'] },
        yAxis: {},
        series: [{ type: 'bar', data: [1, 2, 3] }]
    }
    
    const testContainer = document.createElement('div')
    testContainer.style.width = '400px'
    testContainer.style.height = '300px'
    document.body.appendChild(testContainer)
    
    try {
        const chart = echarts.init(testContainer)
        chart.setOption(testOption)
        console.log('基础图表渲染测试: 成功')
        return true
    } catch (error) {
        console.error('基础图表渲染测试失败:', error)
        return false
    }
}

// 运行诊断
console.log('=== Analysis.jsx 诊断开始 ===')
testAPI()
checkChartContainers()
testMockData()
testChartRendering()
console.log('=== 诊断结束 ===')