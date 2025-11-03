import React, { useMemo } from 'react'
import * as THREE from 'three'

/**
 * 真实地形网格组件
 * 基于API返回的桩位数据生成地形mesh
 */
const TerrainMesh = ({ terrainData, showHeightMap = false }) => {
  const terrainGeometry = useMemo(() => {
    if (!terrainData || !terrainData.tables || terrainData.tables.length === 0) {
      // 默认平面地形
      return new THREE.PlaneGeometry(200, 120, 50, 50)
    }

    // 从桩位数据提取地形点
    const terrainPoints = []
    terrainData.tables.forEach(table => {
      if (table.piles && Array.isArray(table.piles)) {
        table.piles.forEach(pile => {
          if (pile.x !== undefined && pile.y !== undefined && pile.z !== undefined) {
            terrainPoints.push({
              x: pile.x,
              y: pile.y,
              z: pile.z || 0  // z是高程
            })
          }
        })
      }
    })

    if (terrainPoints.length === 0) {
      return new THREE.PlaneGeometry(200, 120, 50, 50)
    }

    // 计算地形范围
    const bounds = {
      minX: Math.min(...terrainPoints.map(p => p.x)),
      maxX: Math.max(...terrainPoints.map(p => p.x)),
      minY: Math.min(...terrainPoints.map(p => p.y)),
      maxY: Math.max(...terrainPoints.map(p => p.y)),
      minZ: Math.min(...terrainPoints.map(p => p.z)),
      maxZ: Math.max(...terrainPoints.map(p => p.z))
    }

    // 创建网格
    const segments = 80
    const width = bounds.maxX - bounds.minX + 20  // 加边距
    const height = bounds.maxY - bounds.minY + 20
    const geometry = new THREE.PlaneGeometry(width, height, segments, segments)

    // 旋转使其水平
    geometry.rotateX(-Math.PI / 2)

    // 根据真实地形数据调整顶点高度
    const positions = geometry.attributes.position
    for (let i = 0; i < positions.count; i++) {
      const x = positions.getX(i) + (bounds.minX + bounds.maxX) / 2
      const y = positions.getY(i)  // 这是Three.js的y（我们的z高程）
      const z = positions.getZ(i) + (bounds.minY + bounds.maxY) / 2

      // 找最近的地形点插值计算高度
      let height = 0
      if (terrainPoints.length > 0) {
        // 简化：使用最近的3个点进行插值
        const distances = terrainPoints.map(p => {
          const dx = p.x - x
          const dy = p.y - z  // 注意坐标系转换
          return {
            distance: Math.sqrt(dx * dx + dy * dy),
            height: p.z
          }
        }).sort((a, b) => a.distance - b.distance)

        // IDW插值（反距离加权）
        const maxDist = 10.0  // 影响半径
        let weightSum = 0
        let heightSum = 0
        
        for (let j = 0; j < Math.min(5, distances.length); j++) {
          if (distances[j].distance < maxDist) {
            const weight = 1 / (distances[j].distance + 0.1)  // 避免除零
            weightSum += weight
            heightSum += distances[j].height * weight
          }
        }

        if (weightSum > 0) {
          height = heightSum / weightSum
        }
      }

      positions.setY(i, height)
    }

    geometry.computeVertexNormals()
    geometry.computeBoundingBox()
    
    return geometry
  }, [terrainData])

  // 根据高度生成颜色（热力图效果）
  const material = useMemo(() => {
    if (!showHeightMap) {
      return (
        <meshStandardMaterial 
          color="#4CAF50" 
          roughness={0.85}
          metalness={0.1}
        />
      )
    }

    // 创建高度图材质
    const positions = terrainGeometry.attributes.position
    const colors = new Float32Array(positions.count * 3)
    
    let minHeight = Infinity
    let maxHeight = -Infinity
    
    for (let i = 0; i < positions.count; i++) {
      const height = positions.getY(i)
      minHeight = Math.min(minHeight, height)
      maxHeight = Math.max(maxHeight, height)
    }

    const heightRange = maxHeight - minHeight || 1

    for (let i = 0; i < positions.count; i++) {
      const height = positions.getY(i)
      const normalized = (height - minHeight) / heightRange
      
      // 颜色渐变：蓝色（低）-> 绿色（中）-> 红色（高）
      let r, g, b
      if (normalized < 0.5) {
        // 蓝到绿
        const t = normalized * 2
        r = t * 0.3
        g = 0.5 + t * 0.5
        b = 1.0 - t * 0.5
      } else {
        // 绿到红
        const t = (normalized - 0.5) * 2
        r = 0.3 + t * 0.7
        g = 1.0 - t * 0.5
        b = 0.5 - t * 0.5
      }

      colors[i * 3] = r
      colors[i * 3 + 1] = g
      colors[i * 3 + 2] = b
    }

    terrainGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    return (
      <meshStandardMaterial 
        vertexColors
        roughness={0.85}
        metalness={0.1}
      />
    )
  }, [terrainGeometry, showHeightMap])

  return (
    <mesh 
      position={[0, 0, 0]} 
      receiveShadow
      geometry={terrainGeometry}
    >
      {material}
    </mesh>
  )
}

export default TerrainMesh



