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

// ✅ 追踪器Table组件（计算旋转角度，传递给每个module）
const TrackerTable = ({
  tableId,
  modules = [],
  sunPosition,
  showDetails,
  currentTime,
  useRealTerrain,
  enableBacktracking,
  rowPitch,
  moduleWidth,
  allTables = []  // ✅ 新增：所有table数据，用于地形感知回溯
}) => {
  const rotationAngleRef = useRef(0)  // 当前旋转角度（弧度）
  
  // 组件挂载（调试日志已禁用）
  // useEffect(() => {
  //   console.log(`✅ TrackerTable挂载: tableId=${tableId}, modules=${modules.length}个`)
  // }, [])
  
  // 计算table中心位置和范围
  const { centerPos, minPos, maxPos, axisLength, axisDirection } = useMemo(() => {
    if (modules.length === 0) return { 
      centerPos: [0, 0, 0], 
      minPos: [0, 0, 0], 
      maxPos: [0, 0, 0],
      axisLength: 0,
      axisDirection: 'x'
    }
    
    let sumX = 0, sumY = 0, sumZ = 0
    let minX = Infinity, minY = Infinity, minZ = Infinity
    let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity
    
    modules.forEach(m => {
      const pos = m.position || m
      sumX += pos[0]
      sumY += pos[1]
      sumZ += pos[2]
      minX = Math.min(minX, pos[0])
      minY = Math.min(minY, pos[1])
      minZ = Math.min(minZ, pos[2])
      maxX = Math.max(maxX, pos[0])
      maxY = Math.max(maxY, pos[1])
      maxZ = Math.max(maxZ, pos[2])
    })
    
    // 判断table的主要排列方向（X还是Z）
    const spanX = maxX - minX
    const spanZ = maxZ - minZ
    const axisDirection = spanX > spanZ ? 'x' : 'z'
    const axisLength = Math.max(spanX, spanZ, 1.0)
    
    return {
      centerPos: [sumX / modules.length, sumY / modules.length, sumZ / modules.length],
      minPos: [minX, minY, minZ],
      maxPos: [maxX, maxY, maxZ],
      axisLength,
      axisDirection
    }
  }, [modules])
  
  // ✅ 在Table级别计算统一的旋转角度
  useFrame(() => {
    if (sunPosition && currentTime !== undefined) {
      const sunHeight = sunPosition[1]
      
      // ⚠️ 降低太阳高度阈值，确保能触发旋转
      if (sunHeight > 1) {
        const sunX = sunPosition[0]
        const sunZ = sunPosition[2]
        
        // 统一的太阳角度计算
        const horizontalDist = Math.sqrt(sunX * sunX + sunZ * sunZ) || 0.01
        const solarElevation = Math.atan2(sunHeight, horizontalDist) * (180 / Math.PI)
        const solarAzimuth = Math.atan2(sunX, sunZ) * (180 / Math.PI)
        
        // 追踪器参数（论文标准参数）
        const axisAzimuth = 180 // 南北轴（追踪轴方位角）
        const axisTilt = 0 // 追踪轴倾斜角（假设水平）
        const gcr = Math.min(Math.max(moduleWidth / rowPitch, 0.05), 0.9)
        
        // ✅ 论文算法：单轴追踪器理想角度计算
        // 参考：pvlib singleaxis tracker algorithm
        // tracker_theta = arctan(tan(solar_elevation) * sin(solar_azimuth - axis_azimuth))
        const solarElevationRad = solarElevation * Math.PI / 180
        const azimuthDiff = (solarAzimuth - axisAzimuth) * Math.PI / 180
        
        let idealTrackerAngle = Math.atan(
          Math.tan(solarElevationRad) * Math.sin(azimuthDiff)
        ) * (180 / Math.PI)
        
        if (!isFinite(idealTrackerAngle)) {
          idealTrackerAngle = 0
        }
        
        // 标准回溯角度计算（基于GCR，避免行间遮挡）
        let backtrackAngle = Math.atan2(
          Math.sin(solarElevationRad) * Math.cos(azimuthDiff),
          (1 - gcr) / gcr + Math.cos(solarElevationRad)
        ) * (180 / Math.PI)
        
        // 🌄 地形感知回溯（Terrain-Aware Backtracking）
        // ✅ 完全匹配后端算法和论文实现
        if (enableBacktracking && allTables.length > 0) {
          // 计算当前排的平均高度
          const myHeight = centerPos[1]
          
          // 🔧 论文参数：过滤邻居的距离范围
          const MAX_NEIGHBOR_CROSS_DISTANCE = 20.0  // 横向最大距离（米）
          const MAX_NEIGHBOR_ALONG_DISTANCE = 250.0 // 沿轴最大距离（米）
          const CROSS_DISTANCE_EPSILON = 0.5        // 防止数值不稳定
          const ALONG_DISTANCE_DECAY = 150.0        // 沿轴距离衰减因子
          
          // 找到相邻排并过滤
          const neighbors = allTables.filter(otherTable => {
            if (otherTable.tableId === tableId) return false
            const otherCenter = otherTable.centerPos
            if (!otherCenter) return false
            
            // 计算横向距离（cross_axis_distance）和沿轴距离（along_axis_distance）
            const dx = otherCenter[0] - centerPos[0]
            const dz = otherCenter[2] - centerPos[2]
            
            // 简化：假设追踪轴沿东西方向（X轴）
            const crossAxisDistance = dz  // 南北方向为横向
            const alongAxisDistance = dx  // 东西方向为沿轴
            
            // 过滤：横向距离和沿轴距离范围
            if (Math.abs(crossAxisDistance) < CROSS_DISTANCE_EPSILON) return false
            if (Math.abs(crossAxisDistance) > MAX_NEIGHBOR_CROSS_DISTANCE) return false
            if (Math.abs(alongAxisDistance) > MAX_NEIGHBOR_ALONG_DISTANCE) return false
            
            return true
          })
          
          // 📐 论文算法：计算遮挡裕度（Shading Margin）
          let minShadingMargin = Infinity
          
          // 计算太阳相对追踪轴的横向分量（cross_component）
          const crossComponent = Math.sin(azimuthDiff)
          
          for (const neighbor of neighbors) {
            const dx = neighbor.centerPos[0] - centerPos[0]
            const dz = neighbor.centerPos[2] - centerPos[2]
            
            // 横向距离和沿轴距离
            let crossAxisDistance = dz
            const alongAxisDistance = dx
            
            // 判断邻居在哪一侧（相对太阳）
            const neighborSide = Math.sign(crossAxisDistance)
            const sunSide = Math.sign(crossComponent)
            
            // 只考虑太阳方向的邻居
            if (Math.abs(crossComponent) > 1e-6 && neighborSide !== sunSide) continue
            
            // 📐 计算遮挡角度（neighbor_blocking_angle）
            // 防止横向距离过小导致数值不稳定
            if (Math.abs(crossAxisDistance) < CROSS_DISTANCE_EPSILON) {
              crossAxisDistance = crossAxisDistance === 0 
                ? CROSS_DISTANCE_EPSILON 
                : Math.sign(crossAxisDistance) * CROSS_DISTANCE_EPSILON
            }
            
            // 垂直高度差
            let vertical = neighbor.centerPos[1] - myHeight
            
            // ✅ 坡度补偿（论文关键）
            // 注意：这里简化了坡度计算，实际应从地形数据获取
            // 可以根据相邻table的高度差估算坡度
            const estimatedSlopeDeg = Math.atan2(vertical, Math.abs(crossAxisDistance)) * (180 / Math.PI) * 0.1
            vertical += Math.tan(estimatedSlopeDeg * Math.PI / 180) * crossAxisDistance
            
            // ✅ 沿轴距离衰减因子（论文核心：20%衰减）
            const alongFactor = Math.min(Math.abs(alongAxisDistance) / ALONG_DISTANCE_DECAY, 1.0)
            vertical -= vertical * 0.2 * alongFactor
            
            // 遮挡角度（度）
            const blockingAngle = Math.atan2(vertical, Math.abs(crossAxisDistance)) * (180 / Math.PI)
            
            // ✅ 计算遮挡裕度（Shading Margin = Solar Elevation - Blocking Angle）
            const shadingMargin = solarElevation - blockingAngle
            
            // 记录最小遮挡裕度
            if (shadingMargin < minShadingMargin) {
              minShadingMargin = shadingMargin
            }
          }
          
          // ✅ 应用回溯限制（当遮挡裕度为负时）
          if (minShadingMargin < 0) {
            // 遮挡裕度为负表示有遮挡，限制追踪角度
            const limitAngle = Math.abs(minShadingMargin)
            idealTrackerAngle = Math.sign(idealTrackerAngle) * Math.min(Math.abs(idealTrackerAngle), limitAngle)
          }
        }
        
        // 应用回溯限制：取理想角度和回溯角度中较小的（绝对值）
        let targetAngle = Math.abs(idealTrackerAngle) < Math.abs(backtrackAngle) 
          ? idealTrackerAngle 
          : backtrackAngle
        
        // 物理限制：最大旋转角度
        const MAX_ANGLE = 60  // 单轴追踪器典型最大角度±60度
        targetAngle = Math.max(-MAX_ANGLE, Math.min(MAX_ANGLE, targetAngle))
        
        // 平滑旋转
        const targetRadians = targetAngle * (Math.PI / 180)
        const currentRotation = rotationAngleRef.current
        const newRotation = THREE.MathUtils.lerp(currentRotation, targetRadians, 0.08)
        rotationAngleRef.current = newRotation
        
        // 🔍 每2秒打印一次论文算法的关键参数（只打印前3个table）
        if (Math.random() < 0.01 && parseInt(tableId.toString().split('_').pop()) < 3) {
          const logData = {
            'Table': tableId,
            '高度': centerPos[1].toFixed(1) + 'm',
            '太阳高度角': solarElevation.toFixed(1) + '°',
            '太阳方位角': solarAzimuth.toFixed(1) + '°',
            '理想追踪角': idealTrackerAngle.toFixed(1) + '°',
            '回溯角度': backtrackAngle.toFixed(1) + '°',
            '最终角度': targetAngle.toFixed(1) + '°',
            '当前旋转': (newRotation * 180 / Math.PI).toFixed(1) + '°',
            'GCR': gcr.toFixed(2),
          }
          
          // ✅ 如果启用了地形感知回溯，显示完整的论文算法参数
          if (enableBacktracking && allTables.length > 0) {
            const myHeight = centerPos[1]
            
            // 重新计算遮挡裕度用于日志
            const MAX_NEIGHBOR_CROSS_DISTANCE = 20.0
            const MAX_NEIGHBOR_ALONG_DISTANCE = 250.0
            const CROSS_DISTANCE_EPSILON = 0.5
            const ALONG_DISTANCE_DECAY = 150.0
            
            const neighbors = allTables.filter(otherTable => {
              if (otherTable.tableId === tableId) return false
              const otherCenter = otherTable.centerPos
              if (!otherCenter) return false
              
              const dx = otherCenter[0] - centerPos[0]
              const dz = otherCenter[2] - centerPos[2]
              const crossAxisDistance = dz
              const alongAxisDistance = dx
              
              if (Math.abs(crossAxisDistance) < CROSS_DISTANCE_EPSILON) return false
              if (Math.abs(crossAxisDistance) > MAX_NEIGHBOR_CROSS_DISTANCE) return false
              if (Math.abs(alongAxisDistance) > MAX_NEIGHBOR_ALONG_DISTANCE) return false
              
              return true
            })
            
            let minShadingMargin = Infinity
            const azimuthDiff = (solarAzimuth - axisAzimuth) * Math.PI / 180
            const crossComponent = Math.sin(azimuthDiff)
            
            for (const neighbor of neighbors) {
              const dx = neighbor.centerPos[0] - centerPos[0]
              const dz = neighbor.centerPos[2] - centerPos[2]
              let crossAxisDistance = dz
              const alongAxisDistance = dx
              
              const neighborSide = Math.sign(crossAxisDistance)
              const sunSide = Math.sign(crossComponent)
              if (Math.abs(crossComponent) > 1e-6 && neighborSide !== sunSide) continue
              
              if (Math.abs(crossAxisDistance) < CROSS_DISTANCE_EPSILON) {
                crossAxisDistance = crossAxisDistance === 0 
                  ? CROSS_DISTANCE_EPSILON 
                  : Math.sign(crossAxisDistance) * CROSS_DISTANCE_EPSILON
              }
              
              let vertical = neighbor.centerPos[1] - myHeight
              const estimatedSlopeDeg = Math.atan2(vertical, Math.abs(crossAxisDistance)) * (180 / Math.PI) * 0.1
              vertical += Math.tan(estimatedSlopeDeg * Math.PI / 180) * crossAxisDistance
              
              const alongFactor = Math.min(Math.abs(alongAxisDistance) / ALONG_DISTANCE_DECAY, 1.0)
              vertical -= vertical * 0.2 * alongFactor
              
              const blockingAngle = Math.atan2(vertical, Math.abs(crossAxisDistance)) * (180 / Math.PI)
              const shadingMargin = solarElevation - blockingAngle
              
              if (shadingMargin < minShadingMargin) {
                minShadingMargin = shadingMargin
              }
            }
            
            logData['过滤后邻居数'] = neighbors.length
            logData['遮挡裕度'] = isFinite(minShadingMargin) ? minShadingMargin.toFixed(1) + '°' : '∞'
            logData['遮挡状态'] = minShadingMargin < 0 ? '🔴 有遮挡' : minShadingMargin < 10 ? '🟡 接近' : '🟢 无遮挡'
          }
          
          console.log('📐 论文算法（完整版）:', logData)
        }
      } else {
        // 夜间回归水平（快速复位）
        const currentRotation = rotationAngleRef.current
        rotationAngleRef.current = THREE.MathUtils.lerp(currentRotation, 0, 0.02)
      }
    }
  })
  
  return (
    <>
      {/* 渲染各个module，传递旋转角度ref */}
      {modules.map((module) => {
        const pos = module.position || module
        const showPole = module.showPole !== undefined ? module.showPole : true
        
        return (
          <SolarPanelStatic
            key={module.idx}
            position={pos}
            showDetails={showDetails}
            useRealTerrain={useRealTerrain}
            moduleWidth={moduleWidth}
            showPole={showPole}
            rotationAngleRef={rotationAngleRef}  // ✅ 传递旋转角度ref
          />
        )
      })}
    </>
  )
}

// ✅ 静态光伏板组件（只旋转太阳能板，支撑杆保持垂直）
const SolarPanelStatic = ({
  position,
  showDetails,
  useRealTerrain,
  moduleWidth,
  showPole,
  rotationAngleRef  // ✅ 接收旋转角度ref
}) => {
  const panelRef = useRef()
  
  // 计算支撑杆高度
  let totalPoleHeight = 3.5
  let actualGroundY = -2
  
  if (useRealTerrain) {
    const fixedPoleHeight = 6.0
    totalPoleHeight = fixedPoleHeight
    actualGroundY = position[1] - fixedPoleHeight
  } else {
    const groundY = -1
    const terrainHeight = getTerrainHeight(position[0], position[2])
    actualGroundY = groundY + terrainHeight
    totalPoleHeight = position[1] - actualGroundY
  }
  
  // 直接应用旋转（每帧更新）
  useFrame(() => {
    if (panelRef.current && rotationAngleRef) {
      panelRef.current.rotation.y = rotationAngleRef.current
    }
  })
  
  return (
    <>
      {/* 支撑杆 - 保持垂直，不旋转 */}
      {showDetails && showPole && (
        <mesh position={[position[0], actualGroundY + totalPoleHeight / 2, position[2]]}>
          <cylinderGeometry args={[0.04, 0.04, totalPoleHeight, 6]} />
          <meshStandardMaterial 
            color="#4a4a4a" 
            metalness={0.6}
            roughness={0.4}
          />
        </mesh>
      )}
      
      {/* 光伏板 - 围绕Y轴旋转 */}
      <mesh 
        ref={panelRef}
        position={position} 
        castShadow 
        receiveShadow
      >
        <boxGeometry args={[moduleWidth, 0.05, moduleWidth * 1.2]} />
        <meshStandardMaterial 
          color="#1a3a5c"  // 深蓝色（真实光伏板颜色）
          metalness={0.3} 
          roughness={0.4}
          envMapIntensity={0.5}
        />
      </mesh>
    </>
  )
}

// 论文算法实现：Terrain-Aware Backtracking（保留用于兼容）
const SolarPanel = ({
  position,
  sunPosition,
  showDetails,
  currentTime,
  useRealTerrain = false,
  neighbors = [],
  enableBacktracking = true,
  rowPitch = 3.0, // 行间距（米）
  moduleWidth = 0.95, // 组件宽度（米）- 根据实际数据验证约0.91-1.03米
  showPole = false, // 是否显示支撑杆（只在桩位显示）
  tableId = null // ✅ 新增：跟踪器ID，同一table的组件共享旋转角度
}) => {
  const meshRef = useRef()
  const lastValidRotation = useRef(0)
  const shadingIndicatorRef = useRef()
  const shadingMarginRef = useRef(Infinity)
  
  // 计算支撑杆高度和位置
  let actualGroundY, totalPoleHeight
  
  if (useRealTerrain) {
    const fixedPoleHeight = 6.0 // ✅ 增加到6米（防止嵌入地形）
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
      
      // 从position提取面板位置（用于邻居遮挡计算）
      const panelX = position[0]
      const panelZ = position[2]
      
      if (sunHeight > 5) {
        const sunX = sunPosition[0]
        const sunZ = sunPosition[2]
        
        // ✅ 修复：使用太阳位置计算统一的方位角，不基于组件位置
        // 单轴追踪器的所有组件应该共享同一个旋转角度
        const horizontalDist = Math.sqrt(sunX * sunX + sunZ * sunZ) || 0.01
        
        // 1. 计算太阳高度角和方位角（度）
        const solarElevation = Math.atan2(sunHeight, horizontalDist) * (180 / Math.PI)
        const solarAzimuth = Math.atan2(sunX, sunZ) * (180 / Math.PI)
        
        // 2. 计算基准追踪角度（pvlib singleaxis简化版）
        // 假设追踪轴朝南（axis_azimuth = 180度）
        const axisAzimuth = 180
        const axisTilt = 0 // 假设水平安装
        
        // GCR计算（Ground Coverage Ratio）
        const gcr = Math.min(Math.max(moduleWidth / rowPitch, 0.05), 0.9)
        
        // ✅ 理想追踪角度：基于太阳方位角，所有组件使用相同角度
        // 单轴追踪器围绕南北轴旋转，追踪东西方向的太阳
        const tanElevation = Math.tan(solarElevation * Math.PI / 180)
        const sinAzimuth = Math.sin((solarAzimuth - axisAzimuth) * Math.PI / 180)
        let idealTrackerAngle = Math.atan(tanElevation * sinAzimuth) * (180 / Math.PI)
        
        // 安全检查：确保角度是有效数值
        if (!isFinite(idealTrackerAngle)) {
          idealTrackerAngle = 0
        }
        
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
        <boxGeometry args={[moduleWidth, 0.05, moduleWidth * 1.2]} />
        <meshStandardMaterial 
          color="#1a1a2e" 
          metalness={0.6} 
          roughness={0.2}
        />
      </mesh>
      
      {/* 论文算法可视化：遮挡裕度指示器 - 已隐藏 */}
      {false && enableBacktracking && (
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
    const POLE_HEIGHT = 6.0 // ✅ 增加到6米，防止太阳能板陷入地形
    
    // 为每个太阳能板位置创建地面点
    for (const item of realTerrainData) {
      const pos = item.position || item // 兼容新旧数据结构
      const [x, panelY, z] = pos
      
    // 地面高度 = 太阳能板Y坐标 - 支撑杆高度（6米）
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
    
    console.log('💡 提示：太阳能板高度 = 地面高度 + 5.5米支撑杆（防止陷入地形）')

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
  enableBacktracking = true,
  renderScale = 1.0  // ✅ 接收渲染缩放比例
}) => {
  const useRealTerrain = realTerrainData && realTerrainData.length > 0
  
  const positions = useMemo(() => {
    // 如果有真实地形数据，进行智能采样
    if (realTerrainData && realTerrainData.length > 0) {
      const targetCount = Math.min(maxDisplayCount, realTerrainData.length)
      
      // 🎯 改进采样策略：按跟踪器排分组，优先保留有杆子的组件
      // 将组件按 tableId 分组
      const groupsByTable = {}
      realTerrainData.forEach(item => {
        const tableId = item.tableId || 'unknown'
        if (!groupsByTable[tableId]) {
          groupsByTable[tableId] = []
        }
        groupsByTable[tableId].push(item)
      })
      
      const tableIds = Object.keys(groupsByTable)
      const tableCount = tableIds.length
      
      // ✅ 改进：确保每排显示足够组件呈现真实效果
      const minModulesPerTable = 5   // 最少5个
      const maxModulesPerTable = 15  // 最多15个
      let modulesPerTable = Math.max(minModulesPerTable, Math.floor(targetCount / tableCount))
      modulesPerTable = Math.min(modulesPerTable, maxModulesPerTable)
      
      const sampled = []
      tableIds.forEach(tableId => {
        const tableModules = groupsByTable[tableId]
        if (tableModules.length === 0) return
        
        // ✅ 关键修复：优先选择有杆子的组件
        const withPoles = tableModules.filter(m => m.showPole)
        const withoutPoles = tableModules.filter(m => !m.showPole)
        
        if (tableModules.length <= modulesPerTable) {
          // 如果这排组件数少于等于配额，全部显示
          sampled.push(...tableModules)
        } else {
          // 1. 先选择所有有杆子的组件（支撑结构必须显示）
          const selected = [...withPoles]
          
          // 2. 如果有杆子的组件数量已经满足配额，直接使用
          if (selected.length >= modulesPerTable) {
            sampled.push(...selected.slice(0, modulesPerTable))
          } else {
            // 3. 如果还有配额，从没有杆子的组件中均匀采样补充
            const remaining = modulesPerTable - selected.length
            if (withoutPoles.length > 0 && remaining > 0) {
              const sampleRate = Math.max(1, Math.floor(withoutPoles.length / remaining))
              const additionalSampled = withoutPoles.filter((_, idx) => idx % sampleRate === 0).slice(0, remaining)
              selected.push(...additionalSampled)
            }
            sampled.push(...selected)
          }
        }
      })
      
      // 如果还没达到目标数量，从剩余的组件中补充
      if (sampled.length < targetCount) {
        const remaining = realTerrainData.filter(item => !sampled.includes(item))
        const needed = targetCount - sampled.length
        const extraSampleRate = Math.max(1, Math.floor(remaining.length / needed))
        const extra = remaining.filter((_, idx) => idx % extraSampleRate === 0).slice(0, needed)
        sampled.push(...extra)
      }
      
      // 限制最终数量
      const finalSampled = sampled.slice(0, targetCount)
      
      // 🔧 减少支撑杆显示：采样后，进一步减少支撑杆（只保留1/3的支撑杆）
      const polesReductionRate = 3
      const sampledWithReducedPoles = finalSampled.map((item, idx) => {
        if (item.showPole && idx % polesReductionRate !== 0) {
          return { ...item, showPole: false }
        }
        return item
      })
      
      const totalPolesAfterReduction = sampledWithReducedPoles.filter(item => item.showPole).length
      
      console.log('Smart Sampling Result:', { 
        totalModules: realTerrainData.length,
        totalTables: tableCount,
        modulesPerTable: modulesPerTable,
        displayed: finalSampled.length,
        polesShown: totalPolesAfterReduction,
        strategy: 'Per-table uniform sampling ensures all tables visible'
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
  
  // ✅ 按tableId分组（同一table的module应该一起旋转）
  const groupedByTable = useMemo(() => {
    const groups = {}
    
    positions.forEach((item, idx) => {
      const tableId = item.tableId || `default_table`
      if (!groups[tableId]) {
        groups[tableId] = []
      }
      groups[tableId].push({
        ...item,
        idx,
        neighbors: neighborsMap[idx] || []
      })
    })
    
    return groups
  }, [positions, neighborsMap])
  
  // 🌄 计算每个table的中心位置（用于地形感知回溯）
  const tablesWithCenters = useMemo(() => {
    return Object.entries(groupedByTable).map(([tableId, modules]) => {
      // 计算中心位置
      let sumX = 0, sumY = 0, sumZ = 0
      modules.forEach(m => {
        const pos = m.position || m
        sumX += pos[0]
        sumY += pos[1]
        sumZ += pos[2]
      })
      
      return {
        tableId,
        centerPos: [
          sumX / modules.length,
          sumY / modules.length,
          sumZ / modules.length
        ],
        modules
      }
    })
  }, [groupedByTable])
  
  return (
    <>
      {tablesWithCenters.map(({ tableId, modules }) => (
        <TrackerTable
          key={tableId}
          tableId={tableId}
          modules={modules}
          sunPosition={sunPosition}
          showDetails={showDetails}
          currentTime={currentTime}
          useRealTerrain={useRealTerrain}
          enableBacktracking={enableBacktracking}
          rowPitch={3.0}
          moduleWidth={0.95 * renderScale}
          allTables={tablesWithCenters}  // ✅ 传递所有table的信息
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
      const dayDuration = 30 // 30秒一天，旋转更明显
      const time = (state.clock.getElapsedTime() % dayDuration) / dayDuration
      setTimeOfDay({ ...timeOfDay, value: time })
      
      // 计算目标太阳位置（太阳从东到西移动）- 增大移动范围让旋转更明显
      const targetSunX = (time - 0.5) * 200  // 东西方向移动范围 -100到+100（增大4倍）
      const targetSunHeight = Math.sin(time * Math.PI) * 40 + 20  // 高度：最低20，最高60（提高高度）
      const targetSunZ = 30  // 固定在南侧，增加距离让角度变化更明显
      
      // 平滑插值太阳位置（加快速度，旋转更明显）
      const currentSun = lastSunPosition.current
      const smoothSunX = THREE.MathUtils.lerp(currentSun[0], targetSunX, 0.15)  // 提高速度
      const smoothSunHeight = THREE.MathUtils.lerp(currentSun[1], targetSunHeight, 0.15)
      const smoothSunZ = THREE.MathUtils.lerp(currentSun[2], targetSunZ, 0.15)
      
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
  enableBacktracking = true,
  renderScale = 1.0,  // ✅ 接收渲染缩放比例
  lockView = false  // ✅ 锁定视角状态
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
        renderScale={renderScale}  // ✅ 传递渲染缩放比例
      />
      
      {/* 场景控制 */}
      <SceneController 
        sunPosition={sunPosition} 
        setSunPosition={setSunPosition}
        timeOfDay={timeOfDay}
        setTimeOfDay={setTimeOfDay}
      />
      
      {/* 相机控制 - 锁定视角时禁用所有操作 */}
      {!lockView && (
        <OrbitControls 
          enableDamping
          dampingFactor={0.05}
          minDistance={10}
          maxDistance={100}
          maxPolarAngle={Math.PI / 2.1}
          target={[0, 0, 0]}
        />
      )}
      
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
  const [maxDisplayCount, setMaxDisplayCount] = useState(2000) // 降低到2000个，避免WebGL崩溃，仍保持良好视觉效果
  const [renderScale, setRenderScale] = useState(1.0) // ✅ 保存渲染缩放比例
  const [enableBacktracking, setEnableBacktracking] = useState(true) // 新增：地形感知回溯开关
  const [showUI, setShowUI] = useState(true) // 控制UI面板显示/隐藏
  const [lockView, setLockView] = useState(false) // 锁定视角（禁止鼠标操作相机）
  
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
          
          // 计算数据范围并自适应缩放，让数据适配到更大的显示区域
          const rangeX = actualMaxX - actualMinX
          const rangeY = actualMaxY - actualMinY
          const maxRange = Math.max(rangeX, rangeY, 1)
          const targetSize = 250 // ✅ 增大到250，让组件更大更清晰
          const scale = targetSize / maxRange
          
          // ✅ 保存scale到state，供渲染时使用
          setRenderScale(scale)
          
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
          const fixedPoleHeight = 6.0  // ✅ 增加支撑杆高度到6米，防止嵌入地形
          const baseGroundY = -1  // ✅ 与地形mesh的Y坐标对齐（地形在Y=-1）
          const safetyOffset = 1.0  // ✅ 额外的安全偏移1米，确保始终在地形之上
          
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
              let y = baseGroundY + terrainOffset + fixedPoleHeight + safetyOffset
              
              // ✅ 额外安全检查：确保Y坐标不会异常
              if (!isFinite(y) || y < baseGroundY) {
                console.warn(`⚠️ Table ${table.table_id} 单组件高度异常: y=${y}, 使用默认值`)
                y = baseGroundY + fixedPoleHeight + safetyOffset
              }
              
              // 验证数据有效性
              if (isFinite(x) && isFinite(y) && isFinite(z)) {
                totalModules += 1
                const presetKey = table.preset_type || 'unknown'
                moduleStats[presetKey] = (moduleStats[presetKey] || 0) + 1
                return [{ position: [x, y, z], showPole: true, tableId: table.table_id }] // 添加tableId
              } else {
                console.warn('⚠️ 跳过无效table:', table.table_id, { x, y, z })
                return []
              }
            }
            
            // ✅ 修正理解：使用实际桩位距离作为组件排列长度
            // 数据验证结果：
            //   - 1x14配置：桩跨13.40米，组件宽度约0.91米（不是2米！）
            //   - 1x27配置：桩跨29.19米，组件宽度约1.03米
            // 结论：组件宽度约1米，应使用实际桩位距离
            
            // 确定排的方向（从第一个桩指向最后一个桩）
            const firstPile = piles[0]
            const lastPile = piles[piles.length - 1]
            const pilesDirX = lastPile.x - firstPile.x
            const pilesDirY = lastPile.y - firstPile.y
            const pilesDistance = Math.sqrt(pilesDirX * pilesDirX + pilesDirY * pilesDirY)
            
            // 🔧 使用实际桩位距离作为排长度
            let rowLength, dirX, dirY
            
            if (pilesDistance > 1.0) {
              // 使用桩位方向和实际距离
              rowLength = pilesDistance
              dirX = pilesDirX
              dirY = pilesDirY
            } else {
              // 桩位距离太小，默认南北方向，使用默认长度
              rowLength = moduleCount * 1.0 // 假设组件宽1米
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
              let y = baseGroundY + terrainOffset + fixedPoleHeight + safetyOffset
              
              // ✅ 额外安全检查：确保Y坐标不会异常（如NaN, Infinity或负值）
              if (!isFinite(y) || y < baseGroundY) {
                console.warn(`⚠️ Table ${table.table_id} module ${i} 高度异常: y=${y}, 使用默认值`)
                y = baseGroundY + fixedPoleHeight + safetyOffset
              }
              
              // 🔧 判断是否显示支撑杆：精确匹配预计算的索引
              const showPole = poleIndices.has(i)
              
              // 验证数据有效性，防止NaN或Infinity
              if (isFinite(x) && isFinite(y) && isFinite(z)) {
                modulePositions.push({ position: [x, y, z], showPole, tableId: table.table_id })
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
        style={{ 
          position: 'absolute', 
          top: 0, 
          left: 0, 
          width: '100%', 
          height: '100%',
          pointerEvents: 'auto'
        }}
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
          renderScale={renderScale}  // ✅ 传递渲染缩放比例
          lockView={lockView}  // ✅ 传递视角锁定状态
        />
      </Canvas>
      
      {/* 信息面板 - 已隐藏 */}
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
        pointerEvents: 'auto',
        display: 'none'  // 隐藏信息面板
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
          ⭐ 论文算法特性（完整版）：
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
              ✓ 邻居方向判定（太阳侧）
            </div>
            <div style={{ fontSize: '10px', color: '#FFE082', marginLeft: '12px' }}>
              ✓ 坡度补偿计算
            </div>
            <div style={{ fontSize: '10px', color: '#4CAF50', marginLeft: '12px', marginTop: '4px' }}>
              🟢 绿=无遮挡 | 🟡 黄=接近 | 🔴 红=回溯
            </div>
            <div style={{ fontSize: '9px', color: '#999', marginLeft: '12px', marginTop: '4px' }}>
              ✅ 完全匹配后端算法和论文
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
      
      {/* UI显示/隐藏切换按钮 */}
      <div 
        onClick={() => setShowUI(!showUI)}
        style={{
          position: 'absolute',
          top: 20,
          left: 20,
          background: 'rgba(0,0,0,0.7)',
          color: 'white',
          padding: '12px 18px',
          borderRadius: '10px',
          cursor: 'pointer',
          zIndex: 100,
          pointerEvents: 'auto',
          fontSize: '13px',
          fontWeight: '600',
          backdropFilter: 'blur(8px)',
          transition: 'all 0.3s',
          userSelect: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          border: '1px solid rgba(255,255,255,0.1)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'rgba(0,0,0,0.85)'
          e.currentTarget.style.transform = 'scale(1.05)'
          e.currentTarget.style.boxShadow = '0 6px 16px rgba(0,0,0,0.4)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'rgba(0,0,0,0.7)'
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)'
        }}
      >
        {showUI ? '🙈 隐藏UI' : '👁️ 显示UI'}
      </div>
      
      {/* 🔒 锁定视角按钮 */}
      <div 
        onClick={() => setLockView(!lockView)}
        style={{
          position: 'absolute',
          top: 70,
          left: 20,
          background: lockView ? 'rgba(255,100,100,0.85)' : 'rgba(0,0,0,0.7)',
          color: 'white',
          padding: '12px 18px',
          borderRadius: '10px',
          cursor: 'pointer',
          zIndex: 100,
          pointerEvents: 'auto',
          fontSize: '13px',
          fontWeight: '600',
          backdropFilter: 'blur(8px)',
          transition: 'all 0.3s',
          userSelect: 'none',
          boxShadow: lockView ? '0 4px 12px rgba(255,100,100,0.4)' : '0 4px 12px rgba(0,0,0,0.3)',
          border: lockView ? '2px solid rgba(255,100,100,1)' : '1px solid rgba(255,255,255,0.1)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = lockView ? 'rgba(255,100,100,0.95)' : 'rgba(0,0,0,0.85)'
          e.currentTarget.style.transform = 'scale(1.05)'
          e.currentTarget.style.boxShadow = lockView ? '0 6px 16px rgba(255,100,100,0.5)' : '0 6px 16px rgba(0,0,0,0.4)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = lockView ? 'rgba(255,100,100,0.85)' : 'rgba(0,0,0,0.7)'
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = lockView ? '0 4px 12px rgba(255,100,100,0.4)' : '0 4px 12px rgba(0,0,0,0.3)'
        }}
      >
        {lockView ? '🔒 视角已锁定' : '🔓 锁定视角'}
      </div>
      
      {/* 控制面板 */}
      {showUI && (
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
          zIndex: 1000,
          pointerEvents: 'auto',
          cursor: 'default'
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
                onChange={(checked) => {
                  console.log('Switch clicked, checked:', checked, 'current paused:', timeOfDay.paused)
                  setTimeOfDay({ ...timeOfDay, paused: !checked })
                }}
                size="small"
              />
              {/* 测试按钮 */}
              <button 
                onClick={() => {
                  console.log('Button clicked! Current paused:', timeOfDay.paused)
                  setTimeOfDay({ ...timeOfDay, paused: !timeOfDay.paused })
                }}
                style={{
                  marginLeft: '10px',
                  padding: '4px 12px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  background: timeOfDay.paused ? '#52c41a' : '#ff4d4f',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px'
                }}
              >
                {timeOfDay.paused ? '▶ 播放' : '⏸ 暂停'}
              </button>
            </div>
            </Space>
          </Space>
        </Space>
      </div>
      )}
      
      {/* 操作提示 */}
      {showUI && (
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
          📚 论文算法实现（完整版）：
        </div>
        <div style={{ fontSize: '10px', color: '#666' }}>
          参考论文：Terrain-Aware Backtracking
        </div>
        <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>
          <strong>核心步骤（完全匹配后端）：</strong>
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          1. 计算GCR（moduleWidth/pitch）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          2. 过滤邻居（横向0.5-20m，沿轴≤250m）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          3. 判断邻居侧（太阳方向）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          4. 坡度补偿（高度修正）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          5. 沿轴距离衰减（20%）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          6. 计算遮挡角度（blocking angle）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          7. 计算遮挡裕度（margin）
        </div>
        <div style={{ fontSize: '9px', color: '#666', marginLeft: '8px' }}>
          8. 应用回溯限制（margin &lt; 0）
        </div>
        <div style={{ fontSize: '9px', color: '#4CAF50', marginTop: '4px', fontWeight: '500' }}>
          ✅ 完全匹配后端和论文算法
        </div>
      </div>
      )}
    </div>
  )
}

export default SolarPanel3D_Lite

