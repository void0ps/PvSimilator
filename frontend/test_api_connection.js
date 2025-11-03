// API连接测试脚本
import axios from 'axios';

async function testAPIConnection() {
    console.log('测试本地后端API连接...');
    
    try {
        // 测试模拟任务API
        const response = await axios.get('http://localhost:8000/api/v1/simulations/');
        console.log('✅ 模拟任务API连接成功');
        console.log('响应数据:', response.data);
        
        // 测试模拟任务结果API
        if (response.data && response.data.length > 0) {
            const simulationId = response.data[0].id;
            const resultsResponse = await axios.get(`http://localhost:8000/api/v1/simulations/${simulationId}/results`);
            console.log('✅ 模拟结果API连接成功');
            console.log('结果数据预览:', JSON.stringify(resultsResponse.data).substring(0, 200) + '...');
        }
        
    } catch (error) {
        console.error('❌ API连接失败:', error.message);
        if (error.response) {
            console.error('响应状态:', error.response.status);
            console.error('响应数据:', error.response.data);
        }
    }
}

testAPIConnection();