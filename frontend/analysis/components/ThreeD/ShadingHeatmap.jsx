import React, { useMemo } from 'react'
import * as THREE from 'three'

/**
 * 遮挡热力图组件
 * 在跟踪器行上显示遮挡因子的颜色编码
 */
const ShadingHeatmap = ({ tableId, position, rotation, shadingFactor = 1.0, dimensions = { width: 2.5, height: 0.05, depth: 1.5 } }) => {
  // 根据遮挡因子计算颜色
  const color = useMemo(() => {
    // shadingFactor: 1.0 = 无遮挡（绿色）, 0.38 = 完全遮挡（红色）
    const normalized = (shadingFactor - 0.38) / (1.0 - 0.38)
    const clamped = Math.max(0, Math.min(1, normalized))
    
    // 颜色渐变：红色 -> 黄色 -> 绿色
    let r, g, b
    if (clamped < 0.5) {
      // 红到黄
      const t = clamped * 2
      r = 1.0
      g = t
      b = 0.0
    } else {
      // 黄到绿
      const t = (clamped - 0.5) * 2
      r = 1.0 - t
      g = 1.0
      b = 0.0
    }

    return new THREE.Color(r, g, b)
  }, [shadingFactor])

  // 发光强度取决于遮挡程度
  const emissiveIntensity = useMemo(() => {
    return shadingFactor < 0.7 ? 0.3 : 0.1  // 遮挡严重时更明显
  }, [shadingFactor])

  // 支撑杆高度
  const poleHeight = position[1] - 0.5

  return (
    <group>
      {/* 支撑杆 */}
      <mesh 
        position={[position[0], position[1] - poleHeight / 2, position[2]]} 
        castShadow
      >
        <cylinderGeometry args={[0.05, 0.05, poleHeight, 8]} />
        <meshStandardMaterial color="#666666" />
      </mesh>
      
      {/* 太阳能板 */}
      <mesh position={position} rotation={rotation} castShadow>
        <boxGeometry args={[dimensions.width, dimensions.height, dimensions.depth]} />
        <meshStandardMaterial 
          color={color}
          emissive={color}
          emissiveIntensity={emissiveIntensity}
          metalness={0.7}
          roughness={0.3}
        />
      </mesh>
    </group>
  )
}

/**
 * 遮挡热力图图例
 */
export const ShadingLegend = ({ style = {} }) => {
  return (
    <div style={{
      position: 'absolute',
      bottom: '20px',
      right: '20px',
      background: 'rgba(255, 255, 255, 0.9)',
      padding: '12px',
      borderRadius: '8px',
      fontSize: '12px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      ...style
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>遮挡因子</div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
        <div style={{ width: '20px', height: '12px', background: 'rgb(0, 255, 0)', marginRight: '8px' }}></div>
        <span>1.00 - 无遮挡</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
        <div style={{ width: '20px', height: '12px', background: 'rgb(255, 255, 0)', marginRight: '8px' }}></div>
        <span>0.69 - 轻度遮挡</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
        <div style={{ width: '20px', height: '12px', background: 'rgb(255, 128, 0)', marginRight: '8px' }}></div>
        <span>0.54 - 中度遮挡</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ width: '20px', height: '12px', background: 'rgb(255, 0, 0)', marginRight: '8px' }}></div>
        <span>0.38 - 严重遮挡</span>
      </div>
    </div>
  )
}

export default ShadingHeatmap



