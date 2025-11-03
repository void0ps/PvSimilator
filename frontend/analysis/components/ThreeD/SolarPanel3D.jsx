import React, { useRef, useState, useMemo, useEffect } from 'react'
import * as THREE from 'three'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'

import { terrainApi } from '../../services/api'

// 单个光伏板组件
const SolarPanel = ({ position, sunPosition }) => {
  const meshRef = useRef()
  
  // 跟踪太阳方向（仅东西向方位角跟踪）
  useFrame(() => {
    if (meshRef.current) {
      // 计算光伏板指向太阳的方向（仅水平方向）
      const direction = new THREE.Vector3()
        .subVectors(new THREE.Vector3(sunPosition[0], 0, sunPosition[2]), // 忽略高度，只考虑水平方向
                   new THREE.Vector3(position[0], 0, position[2]))
        .normalize()
      
      // 计算目标角度（方位角 - Y轴旋转，东西向跟踪）
      const targetAzimuth = Math.atan2(direction.x, direction.z)
      
      // 平滑旋转到目标角度（仅Y轴旋转，实现东西向跟随）
      meshRef.current.rotation.y = THREE.MathUtils.lerp(
        meshRef.current.rotation.y,
        targetAzimuth,
        0.05
      )
      
      // 保持光伏板水平（X轴旋转设为0，不进行高度角跟踪）
      meshRef.current.rotation.x = 0
    }
  })
  
  return (
    <mesh ref={meshRef} position={position} castShadow>
      <boxGeometry args={[2.5, 0.05, 1.5]} />
      <meshStandardMaterial color="#1a1a1a" metalness={0.8} roughness={0.2} />
    </mesh>
  )
}

// 简单的支架组件
const PanelMount = ({ position, useFixedHeight = true }) => {
  // 使用固定杆子高度，确保所有杆子长度一致
  const fixedPoleHeight = 2.5
  const poleHeight = useFixedHeight ? fixedPoleHeight : (position[1] - 0.5)
  const groundHeight = position[1] - poleHeight
  
  return (
    <group position={[position[0], groundHeight, position[2]]}>
      {/* 支撑杆 - 从地面开始 */}
      <mesh position={[0, poleHeight / 2, 0]} castShadow>
        <cylinderGeometry args={[0.05, 0.05, poleHeight, 8]} />
        <meshStandardMaterial color="#666666" />
      </mesh>
      {/* 顶部连接件 */}
      <mesh position={[0, poleHeight, 0]} castShadow>
        <boxGeometry args={[0.1, 0.1, 0.5]} />
        <meshStandardMaterial color="#444444" />
      </mesh>
    </group>
  )
}

// 太阳组件
const Sun = ({ position }) => {
  return (
    <>
      <directionalLight 
        position={position} 
        intensity={5} 
        color="#ffeb3b"
        castShadow
        shadow-mapSize-width={4096}
        shadow-mapSize-height={4096}
        shadow-camera-far={150}
        shadow-camera-left={-30}
        shadow-camera-right={30}
        shadow-camera-top={30}
        shadow-camera-bottom={-30}
        shadow-bias={-0.0005}
      />
      <pointLight position={position} intensity={3} color="#ff9500" distance={80} />
      <mesh position={position}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshStandardMaterial 
          color="#ff9500" 
          emissive="#ff9500" 
          emissiveIntensity={1.5}
          roughness={0.1}
          metalness={0.2}
        />
      </mesh>
    </>
  )
}

// 带坡度的立方体草地地形
const GrassTerrain = () => {
  const terrainGeometry = useMemo(() => {
    const geometry = new THREE.BoxGeometry(200, 2, 120, 30, 1, 30)
    const positions = geometry.attributes.position.array
    
    // 在顶部表面添加坡度效果
    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i]
      const z = positions[i + 2]
      const y = positions[i + 1]
      
      // 只修改顶部表面的顶点（y坐标接近1）
      if (y > 0.5) {
        // 创建坡度：从中心向四周逐渐降低
        const distanceFromCenter = Math.sqrt(x * x + z * z)
        const slopeHeight = Math.max(0, 3 - distanceFromCenter * 0.03)
        
        // 添加一些随机的小山丘
        const hillHeight = Math.sin(x * 0.05) * Math.cos(z * 0.05) * 1
        
        positions[i + 1] = y + slopeHeight + hillHeight
      }
    }
    
    // 必须更新几何体
    geometry.computeVertexNormals()
    geometry.computeBoundingBox()
    geometry.computeBoundingSphere()
    geometry.attributes.position.needsUpdate = true
    geometry.attributes.normal.needsUpdate = true
    
    return geometry
  }, [])
  
  return (
    <mesh 
      position={[0, 0, 0]} 
      receiveShadow
      geometry={terrainGeometry}
    >
      <meshStandardMaterial 
        color="#4CAF50" 
        roughness={0.8}
        metalness={0.1}
      />
    </mesh>
  )
}

// 计算地面高度函数
  const getGroundHeight = (x, z) => {
    // 创建坡度：从中心向四周逐渐降低
    const distanceFromCenter = Math.sqrt(x * x + z * z)
    const slopeHeight = Math.max(0, 3 - distanceFromCenter * 0.03) // 中心高，四周低
    
    // 添加一些随机的小山丘
    const hillHeight = Math.sin(x * 0.05) * Math.cos(z * 0.05) * 1
    
    // 立方体草地顶部在y=0位置，加上坡度高度
    return slopeHeight + hillHeight
  }
  
// 光伏板阵列
const buildDefaultPanels = () => {
  const positions = []
  const rows = 12
  const panelsPerRow = 6
  const panelWidth = 2.5
  const panelHeight = 1.5
  const spacing = 0
  const totalLength = rows * panelHeight + (rows - 1) * spacing
  const startZ = -totalLength / 2 + panelHeight / 2
  const startX = -((panelsPerRow - 1) * (panelWidth + spacing)) / 2

  for (let row = 0; row < rows; row++) {
    const rowOffset = row % 2 === 0 ? 0 : panelWidth / 2
    for (let panelIndex = 0; panelIndex < panelsPerRow; panelIndex++) {
      const z = startZ + row * (panelHeight + spacing)
      const x = startX + panelIndex * (panelWidth + spacing) + rowOffset
      const groundHeight = getGroundHeight(x, z)
      const mountHeight = 1.5
      positions.push({
        id: `${row}-${panelIndex}`,
        mountPosition: [x, groundHeight + mountHeight, z],
        panelPosition: [x, groundHeight + mountHeight + 1.1, z]
      })
    }
  }
  return positions
}

const SolarArray = ({ panelNodes, maxDisplayCount = 1000 }) => {
  const [sunPosition, setSunPosition] = useState([0, 15, 0])

  const panelPositions = useMemo(() => {
    if (panelNodes && panelNodes.length > 0) {
      // 如果节点数量超过最大显示数量，进行采样
      if (panelNodes.length > maxDisplayCount) {
        const sampleRate = Math.ceil(panelNodes.length / maxDisplayCount)
        return panelNodes.filter((_, idx) => idx % sampleRate === 0).slice(0, maxDisplayCount)
      }
      return panelNodes
    }
    return buildDefaultPanels()
  }, [panelNodes, maxDisplayCount])

  useFrame((state) => {
    // 模拟一天的时间（24小时周期）
    const dayDuration = 60 // 60秒模拟一天
    const timeOfDay = (state.clock.getElapsedTime() % dayDuration) / dayDuration // 0到1表示一天
    
    // 太阳轨迹：从东边升起（-X方向），经过天空最高点，到西边落下（+X方向）
    const sunX = (timeOfDay - 0.5) * 80 // 从-40到+40，模拟东升西落，匹配更大的背景
    
    // 太阳高度：早晨和傍晚较低，正午最高
    const sunHeight = Math.sin(timeOfDay * Math.PI) * 15 + 8 // 从8到23再到8
    
    // 太阳Z坐标保持相对固定，稍微向南偏移
    const sunZ = -5
    
    const currentSunPosition = [sunX, sunHeight, sunZ]
    setSunPosition(currentSunPosition)
  })
  
  return (
    <>
      <Sun position={sunPosition} />
      
      {panelPositions.map((pos) => {
        return (
          <group key={pos.id}>
            <PanelMount 
              position={pos.panelPosition}
              useFixedHeight={true}
            />
            <SolarPanel 
              position={pos.panelPosition}
              sunPosition={sunPosition}
            />
          </group>
        )
      })}
    </>
  )
}

// 天空盒组件
const Sky = () => {
  return (
    <>
      <color attach="background" args={['#87CEEB']} />
      <fog attach="fog" args={['#87CEEB', 20, 80]} />
      <hemisphereLight 
        intensity={1.2} 
        groundColor="#4a7c59" 
        color="#87CEEB" 
      />
      <ambientLight intensity={0.8} />
    </>
  )
}

// 主场景
const Scene = ({ panelNodes, maxDisplayCount }) => {
  return (
    <>
      <Sky />
      <GrassTerrain />
      <SolarArray panelNodes={panelNodes} maxDisplayCount={maxDisplayCount} />
      <OrbitControls />
      <axesHelper args={[10]} />
    </>
  )
}

// 主组件
const SolarPanel3D = () => {
  const [panelNodes, setPanelNodes] = useState([])
  const [layoutInfo, setLayoutInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [maxDisplayCount, setMaxDisplayCount] = useState(1000) // 默认显示1000个

  useEffect(() => {
    const loadLayout = async () => {
      try {
        setLoading(true)
        const data = await terrainApi.getLayout()
        if (!data || !data.tables) {
          throw new Error('地形数据为空')
        }

        const { bounds = {} } = data.metadata || {}
        const pilesFlat = data.tables.flatMap(table => table.piles || [])
        if (!pilesFlat.length) {
          throw new Error('地形数据缺少桩点信息')
        }
        
        // 计算实际数据范围
        const actualMinX = Math.min(...pilesFlat.map(p => p.x))
        const actualMaxX = Math.max(...pilesFlat.map(p => p.x))
        const actualMinY = Math.min(...pilesFlat.map(p => p.y))
        const actualMaxY = Math.max(...pilesFlat.map(p => p.y))
        const minGround = Math.min(...pilesFlat.map(pile => pile.z_ground ?? pile.z_top ?? 0))
        
        const centerX = (actualMinX + actualMaxX) / 2
        const centerY = (actualMinY + actualMaxY) / 2
        
        // 计算数据范围并自适应缩放
        const rangeX = actualMaxX - actualMinX
        const rangeY = actualMaxY - actualMinY
        const maxRange = Math.max(rangeX, rangeY, 1)
        const targetSize = 80 // 目标显示尺寸（3D场景单位）
        const scale = targetSize / maxRange
        
        const heightScale = 3.0  // 高度缩放：3倍夸张显示地形起伏
        
        console.log('SolarPanel3D 地形数据范围:', {
          x: [actualMinX, actualMaxX],
          y: [actualMinY, actualMaxY],
          rangeX, rangeY,
          scale,
          totalPiles: pilesFlat.length
        })

        // 使用固定的杆子高度，让所有太阳能板看起来更统一
        const fixedPoleHeight = 2.5  // 固定的支撑杆高度（3D单位）
        
        const nodes = data.tables.flatMap((table) => {
          return table.piles.map((pile) => {
            const ground = pile.z_ground ?? pile.z_top ?? 0
            const x = (pile.x - centerX) * scale
            const z = (pile.y - centerY) * scale
            // 地面高度（跟随地形起伏）
            const groundHeight = (ground - minGround) * heightScale
            // 太阳能板位置 = 地面高度 + 固定杆子高度
            const panelY = groundHeight + fixedPoleHeight

            return {
              id: `${table.table_id}-${pile.index}`,
              mountPosition: [x, groundHeight, z],
              panelPosition: [x, panelY, z]
            }
          })
        })

        setPanelNodes(nodes)
        setLayoutInfo({
          tableCount: data.tables.length,
          pileCount: data.metadata?.total_piles,
          bounds
        })
        setError(null)
      } catch (err) {
        console.error('加载地形数据失败', err)
        setError(err.message || '加载地形数据失败')
      } finally {
        setLoading(false)
      }
    }

    loadLayout()
  }, [])

  return (
    <div style={{ width: '100%', height: '700px', position: 'relative' }}>
      <Canvas 
        camera={{ position: [10, 5, 10], fov: 60 }}
        shadows
      >
        <Scene panelNodes={panelNodes} maxDisplayCount={maxDisplayCount} />
      </Canvas>
      
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
        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>🌞 光伏板太阳跟踪演示</div>
        {loading && <div style={{ color: '#FFB74D' }}>• 正在加载地形数据…</div>}
        {error && <div style={{ color: '#EF5350' }}>• 数据加载失败，使用演示场景</div>}
        {!loading && !error && layoutInfo && (
          <>
            <div style={{ color: '#4CAF50' }}>• 真实地形行数：{layoutInfo.tableCount}</div>
            <div style={{ color: '#4CAF50' }}>• 总桩点：{layoutInfo.pileCount}</div>
            <div style={{ color: '#FFA726' }}>
              • 当前显示：{Math.min(maxDisplayCount, panelNodes.length)} 个
            </div>
          </>
        )}
        <div>• 东西向跟踪太阳</div>
        <div>• 带坡度草地</div>
        <div>• 实时阴影效果</div>
      </div>
    </div>
  )
}

export default SolarPanel3D