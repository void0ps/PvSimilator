import axios from 'axios'

// 根据环境变量设置API基础URL
const getApiBaseUrl = () => {
  // 开发环境使用代理，生产环境使用环境变量
  if (import.meta.env.MODE === 'development') {
    return '/api/v1'
  } else {
    // 生产环境使用环境变量或默认值
    // 在Docker容器内部，前端通过Nginx代理访问后端，所以使用相对路径
    return import.meta.env.VITE_API_BASE_URL || '/api/v1'
  }
}

// 创建axios实例
const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)

// 光伏系统API
export const systemsApi = {
  // 获取系统列表
  getSystems: (params = {}) => api.get('/systems', { params }),
  
  // 获取单个系统
  getSystem: (id) => api.get(`/systems/${id}`),
  
  // 创建系统
  createSystem: (data) => api.post('/systems', data),
  
  // 更新系统
  updateSystem: (id, data) => api.put(`/systems/${id}`, data),
  
  // 删除系统
  deleteSystem: (id) => api.delete(`/systems/${id}`),
  
  // 获取系统组件
  getModules: (systemId) => api.get(`/systems/${systemId}/modules`),
  
  // 添加组件
  createModule: (systemId, data) => api.post(`/systems/${systemId}/modules`, data),
  
  // 获取逆变器
  getInverters: (systemId) => api.get(`/systems/${systemId}/inverters`),
  
  // 添加逆变器
  createInverter: (systemId, data) => api.post(`/systems/${systemId}/inverters`, data),
  
  // 获取电池
  getBatteries: (systemId) => api.get(`/systems/${systemId}/batteries`),
  
  // 添加电池
  createBattery: (systemId, data) => api.post(`/systems/${systemId}/batteries`, data)
}

// 模拟任务API
export const simulationsApi = {
  // 获取模拟列表
  getSimulations: (params = {}) => api.get('/simulations', { params }),
  
  // 获取单个模拟
  getSimulation: (id) => api.get(`/simulations/${id}`),
  
  // 创建模拟
  createSimulation: (data) => api.post('/simulations', data),
  
  // 更新模拟
  updateSimulation: (id, data) => api.put(`/simulations/${id}`, data),
  
  // 删除模拟
  deleteSimulation: (id) => api.delete(`/simulations/${id}`),
  
  // 获取模拟结果
  getResults: (simulationId, params = {}) => 
    api.get(`/simulations/${simulationId}/results`, { params }),

  // 获取遮挡数据
  getShading: (simulationId) => api.get(`/simulations/${simulationId}/shading`)
}

// 天气数据API
export const weatherApi = {
  // 获取位置列表
  getLocations: (params = {}) => api.get('/weather/locations', { params }),
  
  // 创建位置
  createLocation: (data) => api.post('/weather/locations', data),
  
  // 更新位置
  updateLocation: (id, data) => api.put(`/weather/locations/${id}`, data),
  
  // 删除位置
  deleteLocation: (id) => api.delete(`/weather/locations/${id}`),
  
  // 获取气象数据
  getWeatherData: (params) => api.get('/weather/data', { params }),
  
  // 计算太阳位置
  getSolarPosition: (params) => api.get('/weather/solar-position', { params }),
  
  // 计算斜面辐射
  getIrradiance: (params) => api.get('/weather/irradiance', { params })
}

// 地形数据API
export const terrainApi = {
  getLayout: (params = {}) => api.get('/terrain/layout', { params })
}

// 默认导出所有API
export default {
  ...systemsApi,
  ...simulationsApi,
  ...weatherApi,
  ...terrainApi
}