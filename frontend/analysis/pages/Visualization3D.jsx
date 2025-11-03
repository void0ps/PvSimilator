import React, { useState } from 'react'
import EnhancedSolarPanel3D from '../components/ThreeD/EnhancedSolarPanel3D'

/**
 * 3D可视化页面
 * 集成增强版3D场景
 */
const Visualization3D = () => {
  const [simulationId, setSimulationId] = useState(null)
  const [enableHeightMap, setEnableHeightMap] = useState(false)
  const [enableShadingHeatmap, setEnableShadingHeatmap] = useState(true)
  const [showStats, setShowStats] = useState(false)

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '20px'
      }}>
        <h1 style={{ margin: 0 }}>3D地形与遮挡可视化</h1>
        
        {/* 控制面板 */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={enableHeightMap}
              onChange={(e) => setEnableHeightMap(e.target.checked)}
            />
            <span style={{ fontSize: '14px' }}>高程热力图</span>
          </label>
          
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={enableShadingHeatmap}
              onChange={(e) => setEnableShadingHeatmap(e.target.checked)}
            />
            <span style={{ fontSize: '14px' }}>遮挡热力图</span>
          </label>
          
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showStats}
              onChange={(e) => setShowStats(e.target.checked)}
            />
            <span style={{ fontSize: '14px' }}>性能统计</span>
          </label>
        </div>
      </div>

      {/* 说明卡片 */}
      <div style={{
        background: '#e3f2fd',
        border: '1px solid #2196F3',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '20px'
      }}>
        <h3 style={{ margin: '0 0 12px 0', color: '#1976d2' }}>功能说明</h3>
        <ul style={{ margin: 0, paddingLeft: '20px' }}>
          <li>✅ <strong>真实地形</strong>：基于实际桩位数据生成的3D地形mesh</li>
          <li>✅ <strong>回溯轨迹</strong>：播放真实的跟踪器角度变化</li>
          <li>✅ <strong>遮挡热力图</strong>：颜色编码显示遮挡因子（绿色=无遮挡，红色=严重遮挡）</li>
          <li>✅ <strong>高程可视化</strong>：通过颜色显示地形高度变化</li>
          <li>✅ <strong>交互控制</strong>：鼠标拖拽旋转，滚轮缩放，播放速度调节</li>
        </ul>
      </div>

      {/* 模拟选择（可选）*/}
      <div style={{
        background: 'white',
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '20px'
      }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
          选择模拟（可选）：
        </label>
        <select
          value={simulationId || ''}
          onChange={(e) => setSimulationId(e.target.value || null)}
          style={{
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid #ccc',
            width: '200px'
          }}
        >
          <option value="">默认场景</option>
          <option value="1">模拟 #1</option>
          <option value="2">模拟 #2</option>
          <option value="3">模拟 #3</option>
        </select>
        <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: '#666' }}>
          选择模拟后将加载真实的回溯轨迹和遮挡数据
        </p>
      </div>

      {/* 3D场景 */}
      <EnhancedSolarPanel3D
        simulationId={simulationId}
        enableHeightMap={enableHeightMap}
        enableShadingHeatmap={enableShadingHeatmap}
        showStats={showStats}
      />

      {/* 数据统计 */}
      <div style={{
        marginTop: '20px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px'
      }}>
        <div style={{
          background: 'white',
          border: '1px solid #ddd',
          borderRadius: '8px',
          padding: '16px'
        }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>能量损失（当前）</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f44336' }}>9.85%</div>
        </div>
        
        <div style={{
          background: 'white',
          border: '1px solid #ddd',
          borderRadius: '8px',
          padding: '16px'
        }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Bay系统（预期）</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ff9800' }}>6.60%</div>
        </div>
        
        <div style={{
          background: 'white',
          border: '1px solid #ddd',
          borderRadius: '8px',
          padding: '16px'
        }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Bay+射线追踪（预期）</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#4CAF50' }}>3.64%</div>
        </div>
        
        <div style={{
          background: 'white',
          border: '1px solid #ddd',
          borderRadius: '8px',
          padding: '16px'
        }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>预期改善</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#2196F3' }}>6.21 pp</div>
        </div>
      </div>

      {/* 技术说明 */}
      <div style={{
        marginTop: '20px',
        background: '#f5f5f5',
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '16px',
        fontSize: '12px',
        color: '#666'
      }}>
        <strong>技术实现：</strong>
        <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px' }}>
          <li>使用React Three Fiber + Three.js渲染3D场景</li>
          <li>地形网格基于IDW（反距离加权）插值生成</li>
          <li>遮挡热力图实时计算颜色映射</li>
          <li>支持时间序列数据播放和控制</li>
          <li>优化的渲染性能，支持大规模数据可视化</li>
        </ul>
      </div>
    </div>
  )
}

export default Visualization3D



