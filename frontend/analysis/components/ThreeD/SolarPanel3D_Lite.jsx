import React, { useRef, useState, useMemo, useEffect } from 'react'
import * as THREE from 'three'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { Slider, Switch, Space, Spin } from 'antd'
import { terrainApi } from '../../services/api'
import Delaunator from 'delaunator'

// 统一的地形高度计算函数
const getTerrainHeight = (x, z) => {
  // 创建明显的坡度：从左到右逐渐降低
  const slopeHeight = -x * 0.15
  // 添加更明显的起伏
  const hillHeight = Math.sin(x * 0.1) * Math.cos(z * 0.1) * 3.0
  return slopeHeight + hillHeight
}

// 论文算法实现：Terrain-Aware Backtracking
const SolarPanel = ({
  position,
  sunPosition,
  showDetails,
  currentTime,
  useRealTerrain = false,
  neighbors = [],
  enableBacktracking = true,
  rowPitch = 3.0, // 行间距（米）
  moduleWidth = 2.0, // 组件宽度（米）
  showPole = false // 是否显示支撑杆（只在桩位显示）
}) => {
  const meshRef = useRef()
  const lastValidRotation = useRef(0)
  const shadingIndicatorRef = useRef()
  const shadingMarginRef = useRef(Infinity)
  
  // 计算支撑杆高度和位置
  let actualGroundY, totalPoleHeight
  
  if (useRealTerrain) {
    const fixedPoleHeight = 3.5 // 增加到3.5米防止嵌入
    totalPoleHeight = fixedPoleHeight
    actualGroundY = position[1] - fixedPoleHeight
  } else {
    const groundY = -1
    const terrainHeight = getTerrainHeight(position[0], position[2])
    actualGroundY = groundY + terrainHeight
    totalPoleHeight = position[1] - actualGroundY
  }
  
  // 论文算法核心参数
  const MAX_ANGLE = 60 // 最大追踪角度（度）
  const CROSS_DISTANCE_EPSILON = 0.5
  const ALONG_DISTANCE_DECAY = 150.0 // 沿轴距离衰减因子
  
  useFrame(() => {
    if (meshRef.current && sunPosition && currentTime !== undefined) {
      const sunHeight = sunPosition[1]
      
      if (sunHeight > 5) {
        const sunX = sunPosition[0]
        const sunZ = sunPosition[2]
        const panelX = position[0]
        const panelZ = position[2]
        
        const dx = sunX - panelX
        const dz = sunZ - panelZ
        const horizontalDist = Math.sqrt(dx * dx + dz * dz)
        
        // 1. 计算太阳高度角和方位角（度）
        const solarElevation = Math.atan2(sunHeight - position[1], horizontalDist) * (180 / Math.PI)
        const solarAzimuth = Math.atan2(sunX, sunZ) * (180 / Math.PI)
        
        // 2. 计算基准追踪角度（pvlib singleaxis简化版）
        // 假设追踪轴朝南（axis_azimuth = 180度）
        const axisAzimuth = 180
        const axisTilt = 0 // 假设水平安装
        
        // GCR计算（Ground Coverage Ratio）
        const gcr = Math.min(Math.max(moduleWidth / rowPitch, 0.05), 0.9)
        
        // 理想追踪角度（未考虑遮挡）
        let idealTrackerAngle = Math.atan2(dx, dz) * (180 / Math.PI)
        
        // 标准回溯角度计算（根据GCR）
        const backtrackAngle = Math.atan2(
          Math.sin(solarElevation * Math.PI / 180) * Math.cos((solarAzimuth - axisAzimuth) * Math.PI / 180),
          (1 - gcr) / gcr + Math.cos(solarElevation * Math.PI / 180)
        ) * (180 / Math.PI)
        
        // 限制在最大角度内
        let targetAngle = Math.sign(idealTrackerAngle) * Math.min(Math.abs(idealTrackerAngle), MAX_ANGLE)
        
        // 3. 地形感知遮挡检测（论文核心）
        let shadingMargin = Infinity
        let isShaded = false
        
        if (enableBacktracking && neighbors.length > 0) {
          // 计算cross_component（太阳相对追踪轴的横向分量）
          const crossComponent = Math.sin((solarAzimuth - axisAzimuth) * Math.PI / 180)
          
          for (const neighbor of neighbors) {
            const [nx, ny, nz] = neighbor
            
            // 计算横向距离（cross_axis_distance）和沿轴距离（along_axis_distance）
            const relX = nx - panelX
            const relZ = nz - panelZ
            
            // 简化：假设追踪轴沿东西方向
            let crossAxisDistance = relZ // 南北方向为横向
            let alongAxisDistance = relX // 东西方向为沿轴
            
            // 过滤：横向距离过远或过近
            if (Math.abs(crossAxisDistance) < CROSS_DISTANCE_EPSILON || Math.abs(crossAxisDistance) > 20) continue
            if (Math.abs(alongAxisDistance) > 250) continue
            
            // 判断邻居在哪一侧（相对太阳）
            const neighborSide = Math.sign(crossAxisDistance)
            const sunSide = Math.sign(crossComponent)
            
            // 只考虑太阳方向的邻居
            if (Math.abs(crossComponent) > 1e-6 && neighborSide !== sunSide) continue
            
            // 4. 计算遮挡角度（neighbor_blocking_angle）
            let cross = crossAxisDistance
            if (Math.abs(cross) < CROSS_DISTANCE_EPSILON) {
              cross = cross === 0 ? CROSS_DISTANCE_EPSILON : Math.sign(cross) * CROSS_DISTANCE_EPSILON
            }
            
            // 垂直高度差
            let vertical = ny - position[1]
            
            // 坡度补偿（这里简化，假设坡度为0）
            // vertical += Math.tan(slopeRow * Math.PI / 180) * cross
            
            // 沿轴距离衰减因子
            const alongFactor = Math.min(Math.abs(alongAxisDistance) / ALONG_DISTANCE_DECAY, 1.0)
            vertical -= vertical * 0.2 * alongFactor
            
            // 遮挡角度（度）
            const blockingAngle = Math.atan2(vertical, Math.abs(cross)) * (180 / Math.PI)
            
            // 5. 计算遮挡裕度（shading margin）
            const margin = solarElevation - blockingAngle
            
            if (margin < shadingMargin) {
              shadingMargin = margin
            }
          }
          
          // 6. 应用回溯限制（论文算法核心）
          if (shadingMargin < 0) {
            isShaded = true
            // 当遮挡裕度为负时，限制追踪角度
            const limitAngle = Math.abs(shadingMargin)
            targetAngle = Math.sign(targetAngle) * Math.min(Math.abs(targetAngle), limitAngle)
          }
        }
        
        shadingMarginRef.current = shadingMargin
        
        // 更新可视化指示器
        if (shadingIndicatorRef.current && showDetails) {
          if (isShaded) {
            // 红色：有遮挡
            shadingIndicatorRef.current.material.color.setHex(0xff4444)
            shadingIndicatorRef.current.material.emissive.setHex(0x661111)
          } else if (shadingMargin < 10) {
            // 黄色：接近遮挡
            shadingIndicatorRef.current.material.color.setHex(0xffaa00)
            shadingIndicatorRef.current.material.emissive.setHex(0x664400)
          } else {
            // 绿色：无遮挡
            shadingIndicatorRef.current.material.color.setHex(0x4CAF50)
            shadingIndicatorRef.current.material.emissive.setHex(0x113311)
          }
        }
        
        // 转换为弧度并应用平滑旋转
        const targetRadians = targetAngle * (Math.PI / 180)
        const currentRotation = meshRef.current.rotation.y
        const rotationSpeed = 0.008
        
        let newRotation = THREE.MathUtils.lerp(currentRotation, targetRadians, rotationSpeed)
        
        const maxRotationPerFrame = 0.01
        const rotationDelta = newRotation - currentRotation
        if (Math.abs(rotationDelta) > maxRotationPerFrame) {
          newRotation = currentRotation + Math.sign(rotationDelta) * maxRotationPerFrame
        }
        
        meshRef.current.rotation.y = newRotation
        lastValidRotation.current = newRotation
      } else {
        // 夜间
        const currentRotation = meshRef.current.rotation.y
        meshRef.current.rotation.y = THREE.MathUtils.lerp(currentRotation, 0, 0.005)
        
        if (shadingIndicatorRef.current && showDetails) {
          shadingIndicatorRef.current.material.color.setHex(0x666666)
          shadingIndicatorRef.current.material.emissive.setHex(0x000000)
        }
      }
      
      meshRef.current.rotation.x = 0
      meshRef.current.rotation.z = 0
    }
  })
  
  return (
    <group position={position} ref={meshRef}>
      {/* 支撑杆 - 只在桩位显示，简化几何 */}
      {showDetails && showPole && (
        <mesh position={[0, actualGroundY - position[1] + totalPoleHeight / 2, 0]}>
          <cylinderGeometry args={[0.05, 0.05, totalPoleHeight, 6]} />
          <meshBasicMaterial color="#777" />
        </mesh>
      )}
      
      {/* 简化光伏板 - 保持算法精度，降低渲染负担 */}
      <mesh position={[0, 0, 0]} castShadow receiveShadow>
        <boxGeometry args={[moduleWidth, 0.05, 1.2]} />
        <meshStandardMaterial 
          color="#1a1a2e" 
          metalness={0.6} 
          roughness={0.2}
        />
      </mesh>
      
      {/* 论文算法可视化：遮挡裕度指示器 */}
      {enableBacktracking && (
        <mesh ref={shadingIndicatorRef} position={[0, 0.08, 0]}>
          <sphereGeometry args={[0.1, 12, 12]} />
          <meshStandardMaterial 
            color="#4CAF50"
            emissive="#113311"
            emissiveIntensity={0.6}
          />
        </mesh>
      )}
    </group>
  )
}

// 真实地形网格（使用企业数据）
// realTerrainData中的point[1]已经包含了heightScale的影响
const TerrainWithRealData = ({ realTerrainData }) => {
  const terrainGeometry = useMemo(() => {
    if (!realTerrainData || realTerrainData.length < 3) {
      console.warn('地形数据不足，跳过渲染')
      return null
    }
    
    console.log('开始构建真实地形网格，数据点数:', realTerrainData.length)

    const pointMap = new Map()
    const POLE_HEIGHT = 3.5 // 增加到3.5米，与太阳能板位置计算保持一致
    
    // 为每个太阳能板位置创建地面点
    for (const item of realTerrainData) {
      const pos = item.position || item // 兼容新旧数据结构
      const [x, panelY, z] = pos
      
      // 地面高度 = 太阳能板Y坐标 - 支撑杆高度
      const groundY = panelY - POLE_HEIGHT
      
      // 在太阳能板位置精确添加地面点（不聚合）
      const key = `${x.toFixed(3)}_${z.toFixed(3)}`
      
      if (!pointMap.has(key)) {
        pointMap.set(key, { x, z, sumY: groundY, count: 1 })
      } else {
        // 如果同一位置有多个点，取最低的地面高度（确保不遮挡）
        const entry = pointMap.get(key)
        entry.sumY = Math.min(entry.sumY / entry.count, groundY)
        entry.count = 1
      }
    }

    const dataPoints = Array.from(pointMap.values()).map(({ x, z, sumY, count }) => ({
      x,
      z,
      y: sumY / count
    }))

    if (dataPoints.length < 3) {
      console.warn('真实地形数据点过少，无法构建网格')
      return null
    }

    // 🔧 扩展地形边界：在数据范围外围添加边界点
    let minX = Infinity, maxX = -Infinity
    let minZ = Infinity, maxZ = -Infinity
    let minY = Infinity, maxY = -Infinity
    
    dataPoints.forEach(p => {
      minX = Math.min(minX, p.x)
      maxX = Math.max(maxX, p.x)
      minZ = Math.min(minZ, p.z)
      maxZ = Math.max(maxZ, p.z)
      minY = Math.min(minY, p.y)
      maxY = Math.max(maxY, p.y)
    })
    
    // 扩展范围：在每个方向增加30%的边界
    const expandRatio = 0.3
    const expandX = (maxX - minX) * expandRatio
    const expandZ = (maxZ - minZ) * expandRatio
    // 使用最小高度再降低，确保地形不会高过任何太阳能板
    const boundaryY = minY - 1.5 // 边界比最低点再低1.5米，确保不会"陷入"
    
    const expandedMinX = minX - expandX
    const expandedMaxX = maxX + expandX
    const expandedMinZ = minZ - expandZ
    const expandedMaxZ = maxZ + expandZ
    
    // 在扩展的边界上生成网格点
    const boundaryPoints = []
    const gridStep = Math.max((maxX - minX) / 10, (maxZ - minZ) / 10, 3) // 边界网格步长
    
    // 四条边界线上添加点
    for (let x = expandedMinX; x <= expandedMaxX; x += gridStep) {
      boundaryPoints.push({ x, z: expandedMinZ, y: boundaryY }) // 北边界
      boundaryPoints.push({ x, z: expandedMaxZ, y: boundaryY }) // 南边界
    }
    for (let z = expandedMinZ; z <= expandedMaxZ; z += gridStep) {
      boundaryPoints.push({ x: expandedMinX, z, y: boundaryY }) // 西边界
      boundaryPoints.push({ x: expandedMaxX, z, y: boundaryY }) // 东边界
    }
    
    // 合并数据点和边界点
    const points = [...dataPoints, ...boundaryPoints]
    
    console.log('🏔️ 地形扩展信息:', {
      原始点数: dataPoints.length,
      边界点数: boundaryPoints.length,
      总点数: points.length,
      原始范围: { x: [minX.toFixed(2), maxX.toFixed(2)], z: [minZ.toFixed(2), maxZ.toFixed(2)] },
      高度范围: { 
        最低地面: minY.toFixed(2), 
        最高地面: maxY.toFixed(2), 
        边界高度: boundaryY.toFixed(2),
        高度差: (maxY - minY).toFixed(2) 
      },
      扩展后范围: { x: [expandedMinX.toFixed(2), expandedMaxX.toFixed(2)], z: [expandedMinZ.toFixed(2), expandedMaxZ.toFixed(2)] }
    })
    
    console.log('💡 提示：太阳能板高度 = 地面高度 + 3.5米支撑杆')

    const coords2D = points.map((p) => [p.x, p.z])

    let delaunay
    try {
      delaunay = Delaunator.from(coords2D)
    } catch (error) {
      console.error('真实地形 Delaunay 构网失败:', error)
      return null
    }

    const { triangles } = delaunay

    const positions = new Float32Array(points.length * 3)
    const colors = new Float32Array(points.length * 3)
    const baseGreen = new THREE.Color(0x3a5a2a)
    const topGreen = new THREE.Color(0x7cb342)

    // 重新计算所有点（包括边界点）的范围，用于颜色归一化
    minY = Infinity
    maxY = -Infinity
    minX = expandedMinX
    maxX = expandedMaxX
    minZ = expandedMinZ
    maxZ = expandedMaxZ

    points.forEach((p, idx) => {
      positions[idx * 3] = p.x
      positions[idx * 3 + 1] = p.y
      positions[idx * 3 + 2] = p.z

      minY = Math.min(minY, p.y)
      maxY = Math.max(maxY, p.y)
    })

    const heightRange = Math.max(maxY - minY, 0.0001)

    points.forEach((p, idx) => {
      const normalized = (p.y - minY) / heightRange
      const color = baseGreen.clone().lerp(topGreen, normalized)
      colors[idx * 3] = color.r
      colors[idx * 3 + 1] = color.g
      colors[idx * 3 + 2] = color.b
    })

    const geometry = new THREE.BufferGeometry()
    
    // 使用 BufferAttribute 并确保设置正确的 needsUpdate
    const positionAttribute = new THREE.BufferAttribute(positions, 3)
    positionAttribute.needsUpdate = true
    geometry.setAttribute('position', positionAttribute)
    
    const colorAttribute = new THREE.BufferAttribute(colors, 3)
    colorAttribute.needsUpdate = true
    geometry.setAttribute('color', colorAttribute)
    
    // setIndex 直接接受 TypedArray 或 BufferAttribute
    const indexArray = triangles.length > 65535 
      ? new Uint32Array(triangles) 
      : new Uint16Array(triangles)
    geometry.setIndex(new THREE.BufferAttribute(indexArray, 1))
    
    geometry.computeVertexNormals()

    console.log('真实地形网格生成完成:', {
      pointCount: points.length,
      triangleCount: triangles.length / 3,
      bounds: {
        x: [minX, maxX],
        y: [minY, maxY],
        z: [minZ, maxZ]
      }
    })

    return geometry
  }, [realTerrainData])

  if (!terrainGeometry) {
    return null
  }

  return (
    <mesh geometry={terrainGeometry} receiveShadow castShadow>
      <meshStandardMaterial
        vertexColors
        roughness={0.9}
        metalness={0.0}
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}

// 带坡度的地形（增强可见性 - 添加高程颜色）
const TerrainWithSlope = ({ useFlat = false }) => {
  const terrainMesh = useMemo(() => {
    const geometry = new THREE.PlaneGeometry(100, 80, 60, 50)
    const positions = geometry.attributes.position.array
    const colors = new Float32Array(positions.length)
    
    let minZ = Infinity
    let maxZ = -Infinity
    
    // 第一遍：计算高度并找出最大最小值
    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i]
      const y = positions[i + 1]
      
      // 如果使用平面，则高度为0；否则使用地形函数
      const totalHeight = useFlat ? 0 : getTerrainHeight(x, y)
      positions[i + 2] = totalHeight
      
      minZ = Math.min(minZ, totalHeight)
      maxZ = Math.max(maxZ, totalHeight)
    }
    
    // 通知 Three.js 位置已更新
    geometry.attributes.position.needsUpdate = true
    
    // 第二遍：根据高度设置颜色（高程着色）
    for (let i = 0; i < positions.length; i += 3) {
      const height = positions[i + 2]
      const normalizedHeight = (height - minZ) / (maxZ - minZ)
      
      // 颜色渐变：低处深绿，高处浅绿
      const baseGreen = new THREE.Color(0x2d5016)  // 深绿
      const topGreen = new THREE.Color(0x8bc34a)   // 浅绿
      const color = baseGreen.lerp(topGreen, normalizedHeight)
      
      colors[i] = color.r
      colors[i + 1] = color.g
      colors[i + 2] = color.b
    }
    
    const colorAttribute = new THREE.BufferAttribute(colors, 3)
    colorAttribute.needsUpdate = true
    geometry.setAttribute('color', colorAttribute)
    
    geometry.computeVertexNormals()
    
    return { geometry, minZ, maxZ }
  }, [useFlat])
  
  return (
    <mesh 
      rotation={[-Math.PI / 2, 0, 0]} 
      position={[0, -1, 0]} 
      receiveShadow
      geometry={terrainMesh.geometry}
    >
      <meshStandardMaterial 
        vertexColors
        roughness={0.9}
        metalness={0.0}
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}

// 太阳（简化渲染）
const Sun = ({ position, size = 2 }) => {
  return (
    <>
      {/* 主光源 - 降低阴影质量以避免WebGL崩溃 */}
      <directionalLight 
        position={position} 
        intensity={3.5}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-camera-far={120}
        shadow-camera-left={-50}
        shadow-camera-right={50}
        shadow-camera-top={50}
        shadow-camera-bottom={-50}
        shadow-bias={-0.0001}
      />
      
      {/* 太阳可视化 */}
      <mesh position={position}>
        <sphereGeometry args={[size, 16, 16]} />
        <meshBasicMaterial color="#ffeb3b" />
      </mesh>
      
      {/* 太阳光晕 */}
      <pointLight position={position} intensity={2} color="#ff9500" distance={60} />
    </>
  )
}

// 光伏板阵列 - 支持真实地形数据和邻居检测
const SolarArray = ({ 
  rows = 6, 
  cols = 8, 
  sunPosition, 
  showDetails, 
  realTerrainData, 
  currentTime, 
  maxDisplayCount = 500,
  enableBacktracking = true 
}) => {
  const useRealTerrain = realTerrainData && realTerrainData.length > 0
  
  const positions = useMemo(() => {
    // 如果有真实地形数据，进行均匀采样
    if (realTerrainData && realTerrainData.length > 0) {
      const targetCount = Math.min(maxDisplayCount, realTerrainData.length)
      const sampleRate = Math.max(1, Math.floor(realTerrainData.length / targetCount))
      const sampled = realTerrainData.filter((_, idx) => idx % sampleRate === 0).slice(0, targetCount)
      
      // 🔧 减少支撑杆显示：采样后，进一步减少支撑杆（只保留1/3的支撑杆）
      const polesReductionRate = 3
      const sampledWithReducedPoles = sampled.map((item, idx) => {
        if (item.showPole && idx % polesReductionRate !== 0) {
          return { ...item, showPole: false }
        }
        return item
      })
      
      const totalPolesAfterReduction = sampledWithReducedPoles.filter(item => item.showPole).length
      
      console.log('✅ 企业真实数据采样:', { 
        企业总组件数: realTerrainData.length,
        采样率: `每${sampleRate}个取1个`,
        当前显示: sampled.length,
        支撑杆优化: `${totalPolesAfterReduction}个（进一步精简）`,
        说明: '100%企业真实数据，均匀采样显示'
      })
      
      return sampledWithReducedPoles
    }
    
    // 否则使用默认布局
    const result = []
    const spacing = 3
    const startX = -(cols - 1) * spacing / 2
    const startZ = -(rows - 1) * spacing / 2
    const groundY = -1  // 地形mesh的y位置
    const panelHeightAboveGround = 2.5  // 面板离地面的高度
    
    for (let i = 0; i < rows; i++) {
      for (let j = 0; j < cols; j++) {
        const x = startX + j * spacing
        const z = startZ + i * spacing
        // 使用统一的地形高度计算
        const terrainHeight = getTerrainHeight(x, z)
        const y = groundY + terrainHeight + panelHeightAboveGround
        
        // 默认布局：每个组件都显示支撑杆
        result.push({ position: [x, y, z], showPole: true })
      }
    }
    return result
  }, [rows, cols, realTerrainData, maxDisplayCount]) // maxDisplayCount变化时重新采样
  
  // 计算每个面板的邻居（用于遮挡检测）
  const neighborsMap = useMemo(() => {
    if (!enableBacktracking || positions.length === 0) return {}
    
    const map = {}
    const maxNeighborDistance = 15 // 最大邻居距离
    
    positions.forEach((item, idx) => {
      const neighbors = []
      const pos = item.position || item // 兼容新旧数据结构
      const [x, y, z] = pos
      
      // 查找附近的其他面板
      positions.forEach((otherItem, otherIdx) => {
        if (idx === otherIdx) return
        
        const otherPos = otherItem.position || otherItem // 兼容新旧数据结构
        const [ox, oy, oz] = otherPos
        const dx = ox - x
        const dz = oz - z
        const distance = Math.sqrt(dx * dx + dz * dz)
        
        // 只保留合理距离内的邻居（2-15米）
        if (distance > 2 && distance < maxNeighborDistance) {
          neighbors.push(otherPos)
        }
      })
      
      // 只保留最近的5个邻居（性能优化）
      neighbors.sort((a, b) => {
        const distA = Math.sqrt((a[0]-x)**2 + (a[2]-z)**2)
        const distB = Math.sqrt((b[0]-x)**2 + (b[2]-z)**2)
        return distA - distB
      })
      
      map[idx] = neighbors.slice(0, 5)
    })
    
    return map
  }, [positions, enableBacktracking])
  
  return (
    <>
      {positions.map((item, idx) => {
        const pos = item.position || item // 兼容新旧数据结构
        const showPole = item.showPole !== undefined ? item.showPole : true // 默认显示支撑杆
        
        return (
        <SolarPanel 
          key={idx} 
          position={pos} 
          sunPosition={sunPosition}
          showDetails={showDetails}
          currentTime={currentTime}
          useRealTerrain={useRealTerrain}
            neighbors={neighborsMap[idx] || []}
            enableBacktracking={enableBacktracking}
            rowPitch={3.0}
            moduleWidth={2.0}
            showPole={showPole}
        />
        )
      })}
    </>
  )
}

// 场景控制组件（增强平滑度）
const SceneController = ({ sunPosition, setSunPosition, timeOfDay, setTimeOfDay }) => {
  const lastSunPosition = useRef(sunPosition)
  
  useFrame((state) => {
    if (!timeOfDay.paused) {
      const dayDuration = 60 // 改为60秒一天，更慢更平滑
      const time = (state.clock.getElapsedTime() % dayDuration) / dayDuration
      setTimeOfDay({ ...timeOfDay, value: time })
      
      // 计算目标太阳位置（太阳从东到西移动）
      const targetSunX = (time - 0.5) * 50  // 东西方向移动范围 -25到+25
      const targetSunHeight = Math.sin(time * Math.PI) * 30 + 10  // 高度：最低10，最高40
      const targetSunZ = 15  // 固定在南侧，确保从相机方向照过来
      
      // 平滑插值太阳位置（避免突然跳变）
      const currentSun = lastSunPosition.current
      const smoothSunX = THREE.MathUtils.lerp(currentSun[0], targetSunX, 0.05)
      const smoothSunHeight = THREE.MathUtils.lerp(currentSun[1], targetSunHeight, 0.05)
      const smoothSunZ = THREE.MathUtils.lerp(currentSun[2], targetSunZ, 0.05)
      
      const newSunPosition = [smoothSunX, smoothSunHeight, smoothSunZ]
      setSunPosition(newSunPosition)
      lastSunPosition.current = newSunPosition
    }
  })
  
  return null
}

// 主场景（优化算法精度，简化渲染）
const Scene = ({ 
  rows, 
  cols, 
  sunPosition, 
  setSunPosition, 
  timeOfDay, 
  setTimeOfDay, 
  showDetails, 
  realTerrainData, 
  maxDisplayCount,
  enableBacktracking = true 
}) => {
  const hasRealData = realTerrainData && realTerrainData.length > 0
  
  // 简化天空
  const skyColor = useMemo(() => {
    const time = timeOfDay.value
    if (time < 0.25 || time > 0.75) return '#1a2332'
    else if (time < 0.3 || time > 0.7) return '#ff6b4a'
    else return '#87CEEB'
  }, [timeOfDay.value])
  
  return (
    <>
      {/* 简化场景渲染 */}
      <color attach="background" args={[skyColor]} />
      <ambientLight intensity={0.4} />
      <hemisphereLight intensity={0.3} groundColor="#3a5a3a" color="#87CEEB" />
      
      {/* 太阳 */}
      <Sun position={sunPosition} />
      
      {/* 地面 - 接收阴影 */}
      {hasRealData ? (
        <TerrainWithRealData realTerrainData={realTerrainData} />
      ) : (
        <TerrainWithSlope useFlat={false} />
      )}
      
      {/* 地面网格（辅助可视化） */}
      {showDetails && (
        <gridHelper args={[80, 40, '#94c973', '#94c973']} position={[0, -0.95, 0]} />
      )}
      
      {/* 光伏板阵列 - 投射阴影 */}
      <SolarArray 
        rows={rows} 
        cols={cols} 
        sunPosition={sunPosition} 
        showDetails={showDetails}
        realTerrainData={realTerrainData}
        currentTime={timeOfDay.value}
        maxDisplayCount={maxDisplayCount}
        enableBacktracking={enableBacktracking}
      />
      
      {/* 场景控制 */}
      <SceneController 
        sunPosition={sunPosition} 
        setSunPosition={setSunPosition}
        timeOfDay={timeOfDay}
        setTimeOfDay={setTimeOfDay}
      />
      
      {/* 相机控制 */}
      <OrbitControls 
        enableDamping
        dampingFactor={0.05}
        minDistance={10}
        maxDistance={100}
        maxPolarAngle={Math.PI / 2.1}
        target={[0, 0, 0]}
      />
      
      {/* 坐标轴（可选） */}
      {showDetails && <axesHelper args={[10]} />}
    </>
  )
}

// 主组件
const SolarPanel3D_Lite = () => {
  // 初始时间设为正午12点（0.5），阴影最明显
  const [sunPosition, setSunPosition] = useState([0, 35, 15])  // 调整太阳位置：正午时在正上方偏南
  const [timeOfDay, setTimeOfDay] = useState({ value: 0.5, paused: false })
  const [rows, setRows] = useState(6)
  const [cols, setCols] = useState(8)
  const [showDetails, setShowDetails] = useState(false) // 默认关闭详细模式（不显示支撑杆）
  const [realTerrainData, setRealTerrainData] = useState([])
  const [loading, setLoading] = useState(true)
  const [terrainInfo, setTerrainInfo] = useState({ tableCount: 403, pileCount: 3779, moduleCount: 0, moduleStats: {} })
  const [maxDisplayCount, setMaxDisplayCount] = useState(150) // 新增：控制最大显示数量（默认150个，保持清晰视野）
  const [enableBacktracking, setEnableBacktracking] = useState(true) // 新增：地形感知回溯开关
  
  // 加载真实地形数据
  useEffect(() => {
    const loadTerrainData = async () => {
      try {
        setLoading(true)
        const data = await terrainApi.getLayout()
        
        if (data && data.tables) {
          const { bounds = {} } = data.metadata || {}
          const pilesFlat = data.tables.flatMap(table => table.piles || [])
          
          if (pilesFlat.length === 0) {
            console.warn('没有桩位数据')
            return
          }
          
          // 计算实际数据范围
          const actualMinX = Math.min(...pilesFlat.map(p => p.x))
          const actualMaxX = Math.max(...pilesFlat.map(p => p.x))
          const actualMinY = Math.min(...pilesFlat.map(p => p.y))
          const actualMaxY = Math.max(...pilesFlat.map(p => p.y))
          const minGround = Math.min(...pilesFlat.map(pile => pile.z_ground ?? pile.z_top ?? 0))
          
          const centerX = (actualMinX + actualMaxX) / 2
          const centerY = (actualMinY + actualMaxY) / 2
          
          // 计算数据范围并自适应缩放，让数据适配到60x60的显示区域
          const rangeX = actualMaxX - actualMinX
          const rangeY = actualMaxY - actualMinY
          const maxRange = Math.max(rangeX, rangeY, 1)
          const targetSize = 60 // 目标显示尺寸（3D场景单位）
          const scale = targetSize / maxRange
          
          const heightScale = 3.0  // 高度缩放：3倍夸张显示地形起伏（真实6.9米→显示20.7米）
          
          console.log('地形数据范围:', {
            x: [actualMinX, actualMaxX],
            y: [actualMinY, actualMaxY],
            rangeX, rangeY,
            scale,
            totalPiles: pilesFlat.length
          })
          
          // 提取所有桩位数据
          // 使用固定的杆子高度，让所有太阳能板看起来更统一
          const fixedPoleHeight = 3.5  // 增加支撑杆高度到3.5米，防止嵌入地形
          const baseGroundY = -2  // 降低地形基准高度，确保太阳能板始终在地形之上
          
          // 🔧 修复：每个table（跟踪行）生成多个太阳能板
          // 企业说明：1个table = 1排 = N个太阳能板（N由preset_type决定，如"1x14"表示14个）
          let totalModules = 0
          const moduleStats = {} // 统计各preset_type的数量
          let presetParseFailCount = 0 // 统计preset_type解析失败的数量
          
          // 生成所有排的数据（不在这里采样，让UI层控制）
          const positions = data.tables.flatMap((table) => {
            if (!table.piles || table.piles.length === 0) return []
            
            const piles = table.piles
            
            // 1. 解析preset_type，得到组件数量（如"1x14" → 14, "1x27" → 27）
            let moduleCount = 1 // 默认1个
            let parseSuccess = false
            if (table.preset_type && typeof table.preset_type === 'string') {
              const match = table.preset_type.match(/1x(\d+)/)
              if (match) {
                moduleCount = parseInt(match[1], 10)
                parseSuccess = true
                
                // 异常检测：moduleCount过大
                if (moduleCount > 100) {
                  console.error(`❌ Table ${table.table_id} moduleCount异常大: ${moduleCount}，preset_type="${table.preset_type}"`)
                  moduleCount = 14 // 使用默认值
                }
              } else {
                console.warn(`⚠️ Table ${table.table_id} preset_type格式异常: "${table.preset_type}"`)
                presetParseFailCount++
              }
            } else {
              console.warn(`⚠️ Table ${table.table_id} 缺少preset_type`)
              presetParseFailCount++
            }
            
            // 2. 计算排的几何信息
            // 排的中心点（所有桩的平均位置）
            const avgX = piles.reduce((sum, p) => sum + p.x, 0) / piles.length
            const avgY = piles.reduce((sum, p) => sum + p.y, 0) / piles.length
            const avgGround = piles.reduce((sum, p) => sum + (p.z_ground ?? p.z_top ?? 0), 0) / piles.length
            
            // 如果只有1个组件，只在中心放1个
            if (moduleCount <= 1) {
              const x = (avgX - centerX) * scale
              const z = (avgY - centerY) * scale
              const terrainOffset = (avgGround - minGround) * heightScale
              const y = baseGroundY + terrainOffset + fixedPoleHeight
              
              // 验证数据有效性
              if (isFinite(x) && isFinite(y) && isFinite(z)) {
                totalModules += 1
                const presetKey = table.preset_type || 'unknown'
                moduleStats[presetKey] = (moduleStats[presetKey] || 0) + 1
                return [{ position: [x, y, z], showPole: true }] // 单个组件显示支撑杆
              } else {
                console.warn('⚠️ 跳过无效table:', table.table_id, { x, y, z })
                return []
              }
            }
            
            // ✅ 正确理解：桩位距离 ≠ 组件排列长度
            // 企业数据：桩位是支撑点，组件会延伸到桩位之外
            // 例如：1x81有17个桩，桩距92米，但81个组件需要137.7米
            
            const TYPICAL_MODULE_WIDTH = 2.0 // 典型组件宽度2米
            const MODULE_SPACING_RATIO = 0.85 // 组件间距系数
            
            // 使用理论长度而不是桩位距离
            const rowLength = moduleCount * TYPICAL_MODULE_WIDTH * MODULE_SPACING_RATIO
            
            // 确定排的方向（从第一个桩指向最后一个桩）
            const firstPile = piles[0]
            const lastPile = piles[piles.length - 1]
            const pilesDirX = lastPile.x - firstPile.x
            const pilesDirY = lastPile.y - firstPile.y
            const pilesDistance = Math.sqrt(pilesDirX * pilesDirX + pilesDirY * pilesDirY)
            
            let dirX, dirY
            if (pilesDistance > 1.0) {
              // 使用桩位方向，但长度为理论长度
              dirX = (pilesDirX / pilesDistance) * rowLength
              dirY = (pilesDirY / pilesDistance) * rowLength
            } else {
              // 桩位距离太小，默认南北方向
              dirX = 0
              dirY = rowLength
            }
            
            // 归一化方向向量
            const normDirX = dirX / rowLength
            const normDirY = dirY / rowLength
            
            // 3. 沿排方向均匀分布N个太阳能板
            const modulePositions = []
            const moduleSpacing = rowLength / (moduleCount - 1) // 组件间距
            
            // 🔧 修复：沿桩位方向插值地面高度，而不是使用平均值
            // 计算桩位方向的总长度（用于插值）
            const pilesVectorX = lastPile.x - firstPile.x
            const pilesVectorY = lastPile.y - firstPile.y
            const pilesTotalDist = Math.sqrt(pilesVectorX * pilesVectorX + pilesVectorY * pilesVectorY)
            
            // 🔧 预先计算哪些组件应该显示支撑杆
            // 策略：均匀分布piles.length个杆子到moduleCount个组件
            const poleIndices = new Set()
            for (let p = 0; p < piles.length; p++) {
              const poleIndex = Math.round((p / (piles.length - 1 || 1)) * (moduleCount - 1))
              poleIndices.add(poleIndex)
            }
            
            for (let i = 0; i < moduleCount; i++) {
              // 从排中心开始，沿方向向量向两侧分布
              const offset = (i / (moduleCount - 1) - 0.5) * rowLength // -rowLength/2 到 +rowLength/2
              const moduleX = avgX + normDirX * offset
              const moduleY = avgY + normDirY * offset
              
              // 🔧 地面高度插值：基于组件在桩位方向上的位置
              let moduleGround
              if (pilesTotalDist > 1.0) {
                // 计算组件相对于第一个桩的投影距离
                const relX = moduleX - firstPile.x
                const relY = moduleY - firstPile.y
                const projDist = (relX * pilesVectorX + relY * pilesVectorY) / pilesTotalDist
                const t = projDist / pilesTotalDist // 归一化位置 [0, 1]
                
                // 线性插值地面高度（超出范围时外推）
                const firstGround = piles[0].z_ground ?? piles[0].z_top ?? 0
                const lastGround = piles[piles.length - 1].z_ground ?? piles[piles.length - 1].z_top ?? 0
                moduleGround = firstGround + (lastGround - firstGround) * t
              } else {
                // 桩位距离太小，使用平均值
                moduleGround = avgGround
              }
              
              const x = (moduleX - centerX) * scale
              const z = (moduleY - centerY) * scale
              const terrainOffset = (moduleGround - minGround) * heightScale
              const y = baseGroundY + terrainOffset + fixedPoleHeight
              
              // 🔧 判断是否显示支撑杆：精确匹配预计算的索引
              const showPole = poleIndices.has(i)
              
              // 验证数据有效性，防止NaN或Infinity
              if (isFinite(x) && isFinite(y) && isFinite(z)) {
                modulePositions.push({ position: [x, y, z], showPole })
              } else {
                console.warn('⚠️ 跳过无效位置:', { x, y, z, moduleX, moduleY, moduleGround })
              }
            }
            
            // 统计信息
            totalModules += moduleCount
            const presetKey = table.preset_type || 'unknown'
            moduleStats[presetKey] = (moduleStats[presetKey] || 0) + 1
            
            return modulePositions
          }) // flatMap已经自动展平，不需要再调用.flat()
          
          // 统计支撑杆数量
          const totalPoles = positions.filter(item => item.showPole).length
          
          console.log('📊 企业真实数据统计:', {
            企业总跟踪行数: data.tables.length,
            企业总组件数: totalModules,
            企业总桩位: pilesFlat.length,
            生成位置数: positions.length,
            支撑杆数量: totalPoles,
            平均每排组件数: (totalModules / data.tables.length).toFixed(1),
            Preset类型分布: moduleStats,
            '⚠️ Preset解析失败': presetParseFailCount,
            说明: '✅ 桩位用于确定方向，组件按理论长度分布'
          })
          
          // 详细分析企业数据
          console.log('🔍 企业数据详细分析:')
          console.log('='.repeat(50))
          
          // 分析前10个table
          data.tables.slice(0, 10).forEach(table => {
            const piles = table.piles || []
            if (piles.length >= 2) {
              const first = piles[0]
              const last = piles[piles.length - 1]
              const dx = last.x - first.x
              const dy = last.y - first.y
              const dist = Math.sqrt(dx * dx + dy * dy)
              
              console.log(`Table ${table.table_id}:`)
              console.log(`  Preset: "${table.preset_type}"`)
              console.log(`  桩位数: ${piles.length}个`)
              console.log(`  第一个桩: (${first.x.toFixed(2)}, ${first.y.toFixed(2)})`)
              console.log(`  最后桩: (${last.x.toFixed(2)}, ${last.y.toFixed(2)})`)
              console.log(`  桩位距离: ${dist.toFixed(2)}米`)
              console.log(`  方向向量: (${dx.toFixed(2)}, ${dy.toFixed(2)})`)
            }
          })
          
          // 特别分析1x81类型
          const x81_tables = data.tables.filter(t => t.preset_type === '1x81')
          if (x81_tables.length > 0) {
            console.log('\n⚠️ 1x81类型详细分析:')
            x81_tables.slice(0, 5).forEach(table => {
              const piles = table.piles || []
              if (piles.length >= 2) {
                const first = piles[0]
                const last = piles[piles.length - 1]
                const dist = Math.sqrt((last.x - first.x)**2 + (last.y - first.y)**2)
                const theoreticalNeeded = 81 * 2.0 * 0.85  // 理论需要137.7米
                console.log(`Table ${table.table_id}: 桩距${dist.toFixed(2)}m, 理论需要${theoreticalNeeded.toFixed(2)}m, 比例${(dist/theoreticalNeeded*100).toFixed(1)}%`)
              }
            })
          }
          
          if (positions.length === 0) {
            console.error('❌ 未生成任何太阳能板位置！')
            return
          }
          
          // 提示：总数较大时的性能优化
          if (positions.length > 15000) {
            console.warn(`⚠️ 总组件数较多：${positions.length}个`)
            console.log('💡 建议：使用滑块控制显示数量以优化性能')
            console.log(`📊 数据构成：${totalModules}个组件 = ${data.tables.length}排 × 平均${(totalModules/data.tables.length).toFixed(1)}个/排`)
          }
          
          setRealTerrainData(positions)
          setMaxDisplayCount((prev) => Math.min(prev, positions.length))
          
          // 添加详细的调试信息
          if (pilesFlat.length > 0) {
          const firstPile = pilesFlat[0]
          const firstGround = firstPile.z_ground ?? firstPile.z_top ?? 0
          const firstTerrainOffset = (firstGround - minGround) * heightScale
          const firstPanelY = baseGroundY + firstTerrainOffset + fixedPoleHeight
          const firstPoleBottom = firstPanelY - fixedPoleHeight
          
          console.log('🔍 数据加载调试:', {
            heightScale,
            baseGroundY,
            fixedPoleHeight,
            第一个桩点: {
              原始z_ground: firstGround,
              minGround,
              terrainOffset: firstTerrainOffset,
              太阳能板Y: firstPanelY,
              杆子底部Y: firstPoleBottom
            }
          })
          }
          
          console.log('生成位置数量:', positions.length, '前3个位置:', positions.slice(0, 3))
          
          
          setTerrainInfo({
            tableCount: data.tables.length,
            pileCount: data.metadata?.total_piles || pilesFlat.length,
            moduleCount: totalModules,
            moduleStats: moduleStats
          })
        }
      } catch (error) {
        console.error('❌ 加载地形数据失败:', error)
        console.error('错误堆栈:', error.stack)
        alert(`加载地形数据失败: ${error.message}`)
      } finally {
        setLoading(false)
      }
    }
    
    loadTerrainData()
  }, [])
  
  const handleTimeChange = (value) => {
    const time = value / 100
    setTimeOfDay({ ...timeOfDay, value: time })
    
    // 计算目标太阳位置（与自动播放逻辑一致）
    const targetSunX = (time - 0.5) * 50  // 东西方向移动范围 -25到+25
    const targetSunHeight = Math.sin(time * Math.PI) * 30 + 10  // 高度：最低10，最高40
    const targetSunZ = 15  // 固定在南侧
    
    // 手动拖动时使用更平滑的插值（减少跳变）
    const currentSun = sunPosition
    
    // 降低插值速度，让手动拖动也更平滑
    const manualSpeed = 0.15 // 从0.5降低到0.15
    const smoothSunX = THREE.MathUtils.lerp(currentSun[0], targetSunX, manualSpeed)
    const smoothSunHeight = THREE.MathUtils.lerp(currentSun[1], targetSunHeight, manualSpeed)
    const smoothSunZ = THREE.MathUtils.lerp(currentSun[2], targetSunZ, manualSpeed)
    
    // 限制每次最大移动距离（防止拖动过快导致跳变）
    const maxMovePerUpdate = 3.0 // 最大3单位
    const deltaX = smoothSunX - currentSun[0]
    const deltaY = smoothSunHeight - currentSun[1]
    const deltaZ = smoothSunZ - currentSun[2]
    const distance = Math.sqrt(deltaX*deltaX + deltaY*deltaY + deltaZ*deltaZ)
    
    let finalSunX = smoothSunX
    let finalSunY = smoothSunHeight
    let finalSunZ = smoothSunZ
    
    if (distance > maxMovePerUpdate) {
      const ratio = maxMovePerUpdate / distance
      finalSunX = currentSun[0] + deltaX * ratio
      finalSunY = currentSun[1] + deltaY * ratio
      finalSunZ = currentSun[2] + deltaZ * ratio
    }
    
    setSunPosition([finalSunX, finalSunY, finalSunZ])
  }
  
  const currentHour = Math.floor(timeOfDay.value * 24)
  const displayCount = realTerrainData.length > 0 
    ? Math.min(maxDisplayCount, realTerrainData.length) 
    : rows * cols
  
  const sliderMax = realTerrainData.length > 0 ? realTerrainData.length : 2000
  
  // 调试信息
  useEffect(() => {
    console.log('🔍 渲染状态:', {
      realTerrainDataLength: realTerrainData.length,
      maxDisplayCount,
      displayCount,
      sliderMax,
      loading
    })
  }, [realTerrainData.length, maxDisplayCount, displayCount, sliderMax, loading])
  
  const displayMarks = useMemo(() => {
    if (!sliderMax || realTerrainData.length === 0) {
      return {
        50: '50',
        500: '500',
        1000: '1k',
        1500: '1.5k',
        2000: '2k'
      }
    }

    const formatMark = (value) => {
      if (value >= 1000) {
        return value % 1000 === 0
          ? `${value / 1000}k`
          : `${(value / 1000).toFixed(1)}k`
      }
      return value.toString()
    }

    const marks = {}
    
    // 根据最大值动态生成刻度
    if (sliderMax <= 500) {
      marks[100] = '100'
      marks[300] = '300'
      marks[sliderMax] = formatMark(sliderMax)
    } else if (sliderMax <= 2000) {
      marks[100] = '100'
      marks[500] = '500'
      marks[1000] = '1k'
      if (sliderMax >= 1500) marks[1500] = '1.5k'
      marks[sliderMax] = formatMark(sliderMax)
    } else if (sliderMax <= 10000) {
      marks[100] = '100'
      marks[500] = '500'
      marks[2000] = '2k'
      marks[5000] = '5k'
      if (sliderMax >= 8000) marks[8000] = '8k'
      marks[sliderMax] = formatMark(sliderMax)
    } else {
      // 超过10000的大规模场景
      marks[100] = '100'
      marks[1000] = '1k'
      marks[5000] = '5k'
      marks[10000] = '10k'
      if (sliderMax >= 15000) marks[15000] = '15k'
      marks[sliderMax] = formatMark(sliderMax)
    }

    return marks
  }, [sliderMax, realTerrainData.length])
  
  return (
    <div style={{ width: '100%', height: '100%', minHeight: '600px', position: 'relative' }}>
      {/* 加载提示 */}
      {loading && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 10,
          background: 'rgba(255,255,255,0.95)',
          padding: '20px 40px',
          borderRadius: '12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
        }}>
          <Spin size="large" />
          <div style={{ marginTop: '12px', fontSize: '14px', color: '#666' }}>
            正在加载真实地形数据...
          </div>
        </div>
      )}
      
      {/* 3D Canvas - 优化性能，专注算法 */}
      <Canvas 
        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
        camera={{ position: [25, 18, 25], fov: 50 }}
        shadows
        dpr={[1, 1.5]}
        gl={{ 
          antialias: true,
          powerPreference: 'high-performance',
        }}
      >
        <Scene 
          rows={rows} 
          cols={cols} 
          sunPosition={sunPosition}
          setSunPosition={setSunPosition}
          timeOfDay={timeOfDay}
          setTimeOfDay={setTimeOfDay}
          showDetails={showDetails}
          realTerrainData={realTerrainData}
          maxDisplayCount={maxDisplayCount}
          enableBacktracking={enableBacktracking}
        />
      </Canvas>
      
      {/* 信息面板 */}
      <div style={{
        position: 'absolute',
        top: 10,
        left: 10,
        background: 'rgba(0,0,0,0.8)',
        color: 'white',
        padding: '12px',
        borderRadius: '8px',
        fontSize: '12px',
        minWidth: '220px',
        zIndex: 10,
        pointerEvents: 'auto'
      }}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '13px', color: '#FF9800' }}>
          📚 论文算法演示版
        </div>
        {realTerrainData.length > 0 ? (
          <>
            <div style={{ color: '#4CAF50', fontWeight: '500' }}>✅ 100%企业真实数据</div>
            <div style={{ color: '#4CAF50', fontSize: '11px' }}>• 企业跟踪行：{terrainInfo.tableCount}排</div>
            <div style={{ color: '#4CAF50', fontSize: '11px' }}>• 企业总桩点：{terrainInfo.pileCount}个</div>
            <div style={{ color: '#4CAF50', fontSize: '11px' }}>• 企业总组件：{terrainInfo.moduleCount || realTerrainData.length}个</div>
            <div style={{ color: '#FF9800', fontSize: '11px', fontWeight: '500' }}>• 采样显示：{displayCount}个 
              <span style={{ fontSize: '10px', color: '#999' }}>(均匀采样)</span>
            </div>
          </>
        ) : (
          <>
            <div>• 模拟场景：{displayCount} 个</div>
          </>
        )}
        <div style={{ color: '#FFD700', fontWeight: '500', marginTop: '8px', fontSize: '12px' }}>
          ⭐ 论文算法特性：
        </div>
        {enableBacktracking && (
          <>
            <div style={{ fontSize: '10px', color: '#FFE082', marginLeft: '12px' }}>
              ✓ GCR 地面覆盖率计算
        </div>
            <div style={{ fontSize: '10px', color: '#FFE082', marginLeft: '12px' }}>
              ✓ 遮挡裕度（Shading Margin）
          </div>
            <div style={{ fontSize: '10px', color: '#FFE082', marginLeft: '12px' }}>
              ✓ 横向/沿轴距离过滤
            </div>
            <div style={{ fontSize: '10px', color: '#FFE082', marginLeft: '12px' }}>
              ✓ 沿轴距离衰减（20%）
            </div>
            <div style={{ fontSize: '10px', color: '#FFE082', marginLeft: '12px' }}>
              ✓ 邻居方向判定
            </div>
            <div style={{ fontSize: '10px', color: '#4CAF50', marginLeft: '12px', marginTop: '4px' }}>
              🟢 绿=无遮挡 | 🟡 黄=接近 | 🔴 红=回溯
            </div>
          </>
        )}
        {!enableBacktracking && (
          <div style={{ fontSize: '10px', color: '#999', marginLeft: '12px' }}>
            （算法已关闭，仅简单追踪）
          </div>
        )}
        <div style={{ color: '#66BB6A', fontWeight: '500', marginTop: '6px', fontSize: '11px' }}>
          • 地形高程着色 🏔️
        </div>
        <div style={{ fontSize: '10px', color: '#81C784', marginLeft: '12px' }}>
          深绿=低地 | 浅绿=高地
        </div>
        <div style={{ marginTop: '8px', color: '#FFD54F', fontWeight: 'bold' }}>
          ⏰ 当前时间：{currentHour.toString().padStart(2, '0')}:00
        </div>
        {currentHour >= 6 && currentHour <= 18 ? (
          currentHour >= 10 && currentHour <= 14 ? (
            <div style={{ 
              marginTop: '6px', 
              padding: '6px', 
              background: 'rgba(255, 215, 0, 0.2)',
              borderRadius: '4px',
              fontSize: '11px',
              color: '#FFE082'
            }}>
              ☀️ 正午时段，阴影最清晰！
            </div>
          ) : (
            <div style={{ 
              marginTop: '6px', 
              padding: '6px', 
              background: 'rgba(100, 181, 246, 0.2)',
              borderRadius: '4px',
              fontSize: '11px',
              color: '#90CAF9'
            }}>
              🌅 白天模式：跟踪太阳中
            </div>
          )
        ) : (
          <div style={{ 
            marginTop: '6px', 
            padding: '6px', 
            background: 'rgba(63, 81, 181, 0.2)',
            borderRadius: '4px',
            fontSize: '11px',
            color: '#9FA8DA'
          }}>
            🌙 夜间模式：回归水平位置
          </div>
        )}
      </div>
      
      {/* 控制面板 */}
      <div style={{
        position: 'absolute',
        bottom: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        background: 'rgba(255,255,255,0.95)',
        padding: '16px 24px',
        borderRadius: '12px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        minWidth: '400px',
        zIndex: 10,
        pointerEvents: 'auto'
      }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 时间控制 */}
          <div>
            <div style={{ marginBottom: '8px', fontSize: '13px', fontWeight: 500 }}>
              时间进度 ({currentHour}:00)
            </div>
            <Slider 
              value={timeOfDay.value * 100}
              onChange={handleTimeChange}
              min={0}
              max={100}
              marks={{
                0: '0时',
                25: '6时',
                50: '12时',
                75: '18时',
                100: '24时'
              }}
            />
          </div>
          
          {/* 场景设置 */}
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {/* 真实数据显示数量控制 */}
            {realTerrainData.length > 0 && (
              <div>
                <div style={{ marginBottom: '8px', fontSize: '13px', fontWeight: 500 }}>
                  显示数量: {displayCount} / {terrainInfo.moduleCount || realTerrainData.length} 
                  <span style={{ fontSize: '11px', color: displayCount <= 200 ? '#4CAF50' : displayCount <= 400 ? '#FF9800' : '#F44336', marginLeft: '8px', fontWeight: 'bold' }}>
                    {displayCount <= 200 ? '✓ 清晰' : displayCount <= 400 ? '⚠ 略密' : '⚠ 密集'}
                  </span>
                </div>
                <div style={{ fontSize: '10px', color: '#666', marginBottom: '8px' }}>
                  💡 从企业{terrainInfo.moduleCount || realTerrainData.length}个组件中均匀采样显示，拖动滑块可调整
                </div>
                <Slider 
                  value={maxDisplayCount}
                  onChange={(value) => {
                    console.log('滑块变化:', value)
                    setMaxDisplayCount(value)
                  }}
                  min={100}
                  max={sliderMax}
                  step={50}
                  marks={displayMarks}
                  tooltip={{ formatter: (value) => `${value}个组件` }}
                />
              </div>
            )}
            
          <Space size="large">
              {/* 模拟数据行列控制 */}
              {!realTerrainData.length && (
                <>
            <div>
              <span style={{ fontSize: '13px', marginRight: '8px' }}>
                行数: {rows}
              </span>
              <Slider 
                value={rows}
                onChange={setRows}
                min={3}
                max={12}
                style={{ width: '100px', display: 'inline-block' }}
              />
            </div>
            
            <div>
              <span style={{ fontSize: '13px', marginRight: '8px' }}>
                列数: {cols}
              </span>
              <Slider 
                value={cols}
                onChange={setCols}
                min={3}
                max={15}
                style={{ width: '100px', display: 'inline-block' }}
              />
            </div>
                </>
              )}
            
            <div style={{ 
              padding: '6px 8px', 
              background: showDetails ? '#fff3e0' : 'transparent',
              borderRadius: '4px',
              border: showDetails ? '1px solid #ff9800' : 'none'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontSize: '13px', marginRight: '8px' }}>详细模式</span>
              <Switch 
                checked={showDetails}
                onChange={setShowDetails}
                  size="small"
                />
              </div>
              {showDetails && (
                <div style={{ fontSize: '10px', color: '#f57c00', marginLeft: '0px' }}>
                  ⚠️ 显示支撑杆 (性能负担较大)
                </div>
              )}
            </div>
            
            <div>
              <span style={{ fontSize: '13px', marginRight: '8px', color: '#FF9800' }}>
                回溯算法
              </span>
              <Switch 
                checked={enableBacktracking}
                onChange={setEnableBacktracking}
                size="small"
              />
            </div>
            
            <div>
              <span style={{ fontSize: '13px', marginRight: '8px' }}>
                {timeOfDay.paused ? '已暂停' : '自动'}
              </span>
              <Switch 
                checked={!timeOfDay.paused}
                onChange={(checked) => setTimeOfDay({ ...timeOfDay, paused: !checked })}
                size="small"
              />
            </div>
            </Space>
          </Space>
        </Space>
      </div>
      
      {/* 操作提示 */}
      <div style={{
        position: 'absolute',
        top: 10,
        right: 10,
        background: 'rgba(255,255,255,0.95)',
        padding: '10px 12px',
        borderRadius: '8px',
        fontSize: '11px',
        color: '#666',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        zIndex: 10,
        pointerEvents: 'auto'
      }}>
        <div style={{ fontWeight: 'bold', marginBottom: '4px', color: '#333' }}>
          🖱️ 鼠标操作：
        </div>
        <div>• 左键拖拽：旋转视角</div>
        <div>• 滚轮：缩放</div>
        <div>• 右键拖拽：平移</div>
        <div style={{ 
          marginTop: '8px', 
          paddingTop: '8px', 
          borderTop: '1px solid #e0e0e0',
          color: '#FF9800',
          fontWeight: '500'
        }}>
          📚 论文算法实现：
        </div>
        <div style={{ fontSize: '10px', color: '#666' }}>
          参考论文：Terrain-Aware Backtracking
        </div>
        <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>
          <strong>核心步骤：</strong>
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          1. 计算GCR（moduleWidth/pitch）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          2. 过滤邻居（横向2-20m）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          3. 判断邻居侧（太阳方向）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          4. 计算遮挡角度（含衰减）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          5. 计算遮挡裕度（margin）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          6. 应用回溯限制
        </div>
        <div style={{ fontSize: '9px', color: '#999', marginTop: '4px' }}>
          ⚡ 算法优先 | 渲染简化
        </div>
      </div>
    </div>
  )
}

export default SolarPanel3D_Lite

