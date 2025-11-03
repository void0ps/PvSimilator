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

// 单个光伏板组件（修复跟踪逻辑和支撑杆位置）
const SolarPanel = ({ position, sunPosition, showDetails, currentTime, useRealTerrain = false }) => {
  const meshRef = useRef()
  const lastValidRotation = useRef(0)
  
  // 计算支撑杆高度和位置
  let actualGroundY, totalPoleHeight
  
  if (useRealTerrain) {
    // 使用真实地形数据时：固定杆子高度2.5米
    const fixedPoleHeight = 2.5
    totalPoleHeight = fixedPoleHeight
    // 地面高度 = 太阳能板高度 - 固定杆子高度
    actualGroundY = position[1] - fixedPoleHeight
  } else {
    // 使用模拟地形时：根据地形计算
    const groundY = -1
    const terrainHeight = getTerrainHeight(position[0], position[2])
    actualGroundY = groundY + terrainHeight
    totalPoleHeight = position[1] - actualGroundY
  }
  
  useFrame(() => {
    if (meshRef.current && sunPosition && currentTime !== undefined) {
      // 计算太阳高度（判断是否在地平线上）
      const sunHeight = sunPosition[1]
      
      // 只在白天（太阳高度 > 5）跟踪太阳
      if (sunHeight > 5) {
        // 计算太阳方向（只考虑水平面）
        const sunX = sunPosition[0]
        const sunZ = sunPosition[2]
        const panelX = position[0]
        const panelZ = position[2]
        
        const dx = sunX - panelX
        const dz = sunZ - panelZ
        
        // 计算目标角度（东西向跟踪）
        let targetAzimuth = Math.atan2(dx, dz)
        
        // 限制旋转范围：-60度到+60度（±π/3）
        const maxRotation = Math.PI / 3
        targetAzimuth = Math.max(-maxRotation, Math.min(maxRotation, targetAzimuth))
        
        // 超平滑旋转（添加每帧最大角度限制）
        const currentRotation = meshRef.current.rotation.y
        const rotationSpeed = 0.008 // 降低到0.8%
        
        // 计算插值后的新角度
        let newRotation = THREE.MathUtils.lerp(
          currentRotation,
          targetAzimuth,
          rotationSpeed
        )
        
        // 限制每帧最大旋转角度（防止跳变）
        const maxRotationPerFrame = 0.01 // 约0.57度/帧
        const rotationDelta = newRotation - currentRotation
        if (Math.abs(rotationDelta) > maxRotationPerFrame) {
          newRotation = currentRotation + Math.sign(rotationDelta) * maxRotationPerFrame
        }
        
        meshRef.current.rotation.y = newRotation
        lastValidRotation.current = newRotation
      } else {
        // 夜间：缓慢回到水平位置（0度）
        const currentRotation = meshRef.current.rotation.y
        meshRef.current.rotation.y = THREE.MathUtils.lerp(
          currentRotation,
          0,
          0.005 // 更慢的夜间回归速度
        )
      }
      
      // 保持水平
      meshRef.current.rotation.x = 0
      meshRef.current.rotation.z = 0
    }
  })
  
  return (
    <>
      {/* 支架 - 从地面开始 */}
      {showDetails && (
        <mesh 
          position={[position[0], actualGroundY + totalPoleHeight / 2, position[2]]} 
          castShadow
        >
          <cylinderGeometry args={[0.05, 0.05, totalPoleHeight, 6]} />
          <meshStandardMaterial color="#666" />
        </mesh>
      )}
      
      {/* 光伏板 - 启用投射阴影 */}
      <mesh ref={meshRef} position={position} castShadow>
        <boxGeometry args={[2, 0.05, 1.2]} />
        <meshStandardMaterial 
          color="#1a1a2e" 
          metalness={0.8} 
          roughness={0.15}
          emissive="#0a0a1a"
          emissiveIntensity={0.1}
        />
      </mesh>
    </>
  )
}

// 真实地形网格（使用企业数据）
// realTerrainData中的point[1]已经包含了heightScale的影响
const TerrainWithRealData = ({ realTerrainData }) => {
  const terrainGeometry = useMemo(() => {
    if (!realTerrainData || realTerrainData.length < 3) {
      return null
    }

    const pointMap = new Map()
    for (const [x, panelY, z] of realTerrainData) {
      const key = `${x.toFixed(4)}_${z.toFixed(4)}`
      const groundY = panelY - 2.5
      if (!pointMap.has(key)) {
        pointMap.set(key, { x, z, sumY: groundY, count: 1 })
      } else {
        const entry = pointMap.get(key)
        entry.sumY += groundY
        entry.count += 1
      }
    }

    const points = Array.from(pointMap.values()).map(({ x, z, sumY, count }) => ({
      x,
      z,
      y: sumY / count
    }))

    if (points.length < 3) {
      console.warn('真实地形数据点过少，无法构建网格')
      return null
    }

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

    let minY = Infinity
    let maxY = -Infinity
    let minX = Infinity
    let maxX = -Infinity
    let minZ = Infinity
    let maxZ = -Infinity

    points.forEach((p, idx) => {
      positions[idx * 3] = p.x
      positions[idx * 3 + 1] = p.y
      positions[idx * 3 + 2] = p.z

      minY = Math.min(minY, p.y)
      maxY = Math.max(maxY, p.y)
      minX = Math.min(minX, p.x)
      maxX = Math.max(maxX, p.x)
      minZ = Math.min(minZ, p.z)
      maxZ = Math.max(maxZ, p.z)
    })

    const heightRange = Math.max(maxY - minY, 0.0001)

    points.forEach((p, idx) => {
      const normalized = (p.y - minY) / heightRange
      const color = baseGreen.clone().lerp(topGreen, normalized)
      colors[idx * 3] = color.r
      colors[idx * 3 + 1] = color.g
      colors[idx * 3 + 2] = color.b
    })

    const indexArray =
      triangles.length > 65535 ? new Uint32Array(triangles) : new Uint16Array(triangles)

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geometry.setIndex(indexArray)
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
    
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
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

// 太阳（优化阴影）
const Sun = ({ position, size = 1.5 }) => {
  return (
    <>
      {/* 主光源 - 增强阴影效果 */}
      <directionalLight 
        position={position} 
        intensity={3}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-far={100}
        shadow-camera-left={-40}
        shadow-camera-right={40}
        shadow-camera-top={40}
        shadow-camera-bottom={-40}
        shadow-bias={-0.0001}
      />
      
      {/* 太阳可视化 - 更大更明显 */}
      <mesh position={position}>
        <sphereGeometry args={[size, 20, 20]} />
        <meshBasicMaterial color="#ffeb3b" />
      </mesh>
      
      {/* 太阳光晕效果 */}
      <pointLight position={position} intensity={2} color="#ff9500" distance={50} />
    </>
  )
}

// 光伏板阵列 - 支持真实地形数据
const SolarArray = ({ rows = 6, cols = 8, sunPosition, showDetails, realTerrainData, currentTime, maxDisplayCount = 500 }) => {
  const useRealTerrain = realTerrainData && realTerrainData.length > 0
  
  const positions = useMemo(() => {
    // 如果有真实地形数据，使用真实数据（采样）
    if (realTerrainData && realTerrainData.length > 0) {
      console.log('采样参数:', { 
        totalData: realTerrainData.length, 
        maxDisplayCount,
        targetCount: Math.min(maxDisplayCount, realTerrainData.length)
      })
      
      // 使用 maxDisplayCount 而不是 rows * cols 来确定显示数量
      const targetCount = Math.min(maxDisplayCount, realTerrainData.length)
      // 采样：均匀采样
      const sampleRate = Math.max(1, Math.floor(realTerrainData.length / targetCount))
      const sampled = realTerrainData.filter((_, idx) => idx % sampleRate === 0)
      const result = sampled.slice(0, targetCount)
      
      console.log('采样结果:', { 
        sampleRate, 
        sampledCount: sampled.length, 
        finalCount: result.length,
        first3: result.slice(0, 3)
      })
      
      return result
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
        
        result.push([x, y, z])
      }
    }
    return result
  }, [rows, cols, realTerrainData, maxDisplayCount])
  
  return (
    <>
      {positions.map((pos, idx) => (
        <SolarPanel 
          key={idx} 
          position={pos} 
          sunPosition={sunPosition}
          showDetails={showDetails}
          currentTime={currentTime}
          useRealTerrain={useRealTerrain}
        />
      ))}
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
      
      // 计算目标太阳位置
      const targetSunX = (time - 0.5) * 40
      const targetSunHeight = Math.sin(time * Math.PI) * 20 + 15  // 增加太阳高度范围
      const targetSunZ = -8
      
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

// 主场景（增强阴影和地形可见性）
const Scene = ({ rows, cols, sunPosition, setSunPosition, timeOfDay, setTimeOfDay, showDetails, realTerrainData, maxDisplayCount }) => {
  const hasRealData = realTerrainData && realTerrainData.length > 0
  
  return (
    <>
      {/* 天空和光照 - 降低环境光以突出阴影 */}
      <color attach="background" args={['#87CEEB']} />
      <ambientLight intensity={0.3} />
      <hemisphereLight intensity={0.3} groundColor="#3a5a3a" color="#87CEEB" />
      
      {/* 太阳 - 增强阴影 */}
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
        minDistance={8}
        maxDistance={60}
        maxPolarAngle={Math.PI / 2.2}
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
  const [sunPosition, setSunPosition] = useState([0, 30, -8])  // 增加太阳高度到30
  const [timeOfDay, setTimeOfDay] = useState({ value: 0.5, paused: false })
  const [rows, setRows] = useState(6)
  const [cols, setCols] = useState(8)
  const [showDetails, setShowDetails] = useState(false)
  const [realTerrainData, setRealTerrainData] = useState([])
  const [loading, setLoading] = useState(true)
  const [terrainInfo, setTerrainInfo] = useState({ tableCount: 403, pileCount: 3779 })
  const [maxDisplayCount, setMaxDisplayCount] = useState(500) // 新增：控制最大显示数量
  
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
          const fixedPoleHeight = 2.5  // 固定的支撑杆高度（3D单位）
          const baseGroundY = -1  // 地形网格的基准高度（与 TerrainWithSlope 一致）
          
          const positions = data.tables.flatMap((table) => {
            return table.piles.map((pile) => {
              const ground = pile.z_ground ?? pile.z_top ?? 0
              const x = (pile.x - centerX) * scale
              const z = (pile.y - centerY) * scale
              // 地面高度变化（跟随真实地形起伏）
              const terrainOffset = (ground - minGround) * heightScale
              // 太阳能板位置 = 地形基准面(-1) + 地形偏移 + 固定杆子高度
              const y = baseGroundY + terrainOffset + fixedPoleHeight
              
              return [x, y, z]
            })
          })
          
          // 添加详细的调试信息
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
          
          console.log('生成位置数量:', positions.length, '前3个位置:', positions.slice(0, 3))
          
          setRealTerrainData(positions)
          setTerrainInfo({
            tableCount: data.tables.length,
            pileCount: data.metadata?.total_piles || positions.length
          })
        }
      } catch (error) {
        console.error('加载地形数据失败:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadTerrainData()
  }, [])
  
  const handleTimeChange = (value) => {
    const time = value / 100
    setTimeOfDay({ ...timeOfDay, value: time })
    
    // 计算目标太阳位置
    const targetSunX = (time - 0.5) * 40
    const targetSunHeight = Math.sin(time * Math.PI) * 20 + 15  // 增加太阳高度范围
    const targetSunZ = -8
    
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
  
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
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
      
      {/* 3D Canvas - 增强阴影渲染 */}
      <Canvas 
        camera={{ position: [20, 12, 20], fov: 50 }}
        shadows={{ enabled: true, type: THREE.PCFSoftShadowMap }}
        gl={{ 
          antialias: true,
          shadowMapEnabled: true
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
        minWidth: '220px'
      }}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '13px' }}>
          🌞 光伏板太阳跟踪演示
        </div>
        {realTerrainData.length > 0 ? (
          <>
            <div style={{ color: '#4CAF50', fontWeight: '500' }}>✓ 使用企业真实地形数据</div>
            <div style={{ color: '#4CAF50' }}>• 真实地形行数：{terrainInfo.tableCount}</div>
            <div style={{ color: '#4CAF50' }}>• 总桩点：{terrainInfo.pileCount}</div>
            <div style={{ color: '#FFA726' }}>• 当前显示：{displayCount} 个光伏板</div>
            <div style={{ fontSize: '10px', color: '#81C784', marginTop: '4px' }}>
              （地形高度来自真实桩位数据）
            </div>
          </>
        ) : (
          <>
            <div>• 模拟场景</div>
            <div>• 显示数量：{displayCount} 个</div>
          </>
        )}
        <div>• 东西向跟踪太阳</div>
        <div style={{ color: '#66BB6A', fontWeight: '500' }}>
          • 高程着色地形 🏔️
        </div>
        <div style={{ fontSize: '10px', color: '#81C784', marginLeft: '12px' }}>
          ↳ 深绿=低地 | 浅绿=高地
        </div>
        <div>• 实时阴影效果 ✓</div>
        {showDetails && (
          <div style={{ 
            fontSize: '10px', 
            color: '#81C784', 
            marginLeft: '12px',
            marginTop: '2px'
          }}>
            ↳ 网格辅助线已开启
          </div>
        )}
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
        minWidth: '400px'
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
                  显示数量: {displayCount} / {terrainInfo.pileCount} 
                  <span style={{ fontSize: '11px', color: '#999', marginLeft: '8px' }}>
                    （调整滑块增加/减少）
                  </span>
                </div>
                <Slider 
                  value={maxDisplayCount}
                  onChange={setMaxDisplayCount}
                  min={50}
                  max={Math.min(2000, realTerrainData.length)}
                  step={50}
                  marks={{
                    50: '50',
                    500: '500',
                    1000: '1k',
                    1500: '1.5k',
                    [Math.min(2000, realTerrainData.length)]: Math.min(2000, realTerrainData.length) >= 2000 ? '2k' : realTerrainData.length.toString()
                  }}
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
            
            <div>
              <span style={{ fontSize: '13px', marginRight: '8px' }}>详细模式</span>
              <Switch 
                checked={showDetails}
                onChange={setShowDetails}
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
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
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
          color: '#2196F3',
          fontWeight: '500'
        }}>
          💡 观察提示：
        </div>
        <div style={{ fontSize: '10px', color: '#666' }}>
          • <strong>开启自动播放</strong>看连续旋转
        </div>
        <div style={{ fontSize: '10px', color: '#666' }}>
          • 手动拖动<strong>请缓慢</strong>移动
        </div>
        <div style={{ fontSize: '10px', color: '#666' }}>
          • 12:00正午阴影最清晰
        </div>
        <div style={{ fontSize: '10px', color: '#666' }}>
          • 俯视角度观察最佳
        </div>
        <div style={{ fontSize: '10px', color: '#4CAF50', fontWeight: '500' }}>
          • 开启详细模式看网格
        </div>
        <div style={{ fontSize: '9px', color: '#999', marginTop: '4px' }}>
          ⚡ 60秒模拟一整天 | 最大0.57°/帧
        </div>
      </div>
    </div>
  )
}

export default SolarPanel3D_Lite

