import React, { useState, useEffect, useCallback } from 'react'
import ShadingHeatmap from './ShadingHeatmap'

/**
 * 回溯轨迹播放器组件
 * 播放真实的回溯角度和遮挡数据
 */
const BacktrackingPlayer = ({ 
  backtrackingData,  // { timestamps, angles, shadingFactors }
  terrainLayout,     // 地形布局数据
  isPlaying = false,
  playbackSpeed = 1.0,
  currentTimeIndex = 0,
  onTimeIndexChange,
  enableShadingHeatmap = true
}) => {
  const [localTimeIndex, setLocalTimeIndex] = useState(currentTimeIndex)

  // 播放逻辑
  useEffect(() => {
    if (!isPlaying || !backtrackingData || !backtrackingData.timestamps) {
      return
    }

    const interval = setInterval(() => {
      setLocalTimeIndex(prev => {
        const next = prev + 1
        if (next >= backtrackingData.timestamps.length) {
          return 0  // 循环播放
        }
        return next
      })
    }, 1000 / playbackSpeed)  // 根据播放速度调整间隔

    return () => clearInterval(interval)
  }, [isPlaying, playbackSpeed, backtrackingData])

  // 同步时间索引
  useEffect(() => {
    if (onTimeIndexChange) {
      onTimeIndexChange(localTimeIndex)
    }
  }, [localTimeIndex, onTimeIndexChange])

  // 如果没有地形数据，不渲染
  if (!terrainLayout || !terrainLayout.tables) {
    return null
  }

  // 使用数据或默认值
  const currentAngles = (backtrackingData && backtrackingData.angles) 
    ? backtrackingData.angles[localTimeIndex] || {} 
    : {}
  const currentShadingFactors = (backtrackingData && backtrackingData.shadingFactors) 
    ? backtrackingData.shadingFactors[localTimeIndex] || {} 
    : {}

  // 调试信息：检查有多少table被渲染
  React.useEffect(() => {
    if (terrainLayout && terrainLayout.tables) {
      const totalTables = terrainLayout.tables.length
      const tablesWithPiles = terrainLayout.tables.filter(t => t.piles && t.piles.length > 0).length
      const tablesWithoutPiles = totalTables - tablesWithPiles
      console.log(`[BacktrackingPlayer] 总跟踪器: ${totalTables}, 有桩位数据: ${tablesWithPiles}, 无桩位数据: ${tablesWithoutPiles}`)
      
      if (tablesWithoutPiles > 0) {
        const emptyTableIds = terrainLayout.tables
          .filter(t => !t.piles || t.piles.length === 0)
          .map(t => t.table_id)
        console.log(`[BacktrackingPlayer] 缺少桩位数据的跟踪器ID:`, emptyTableIds)
      }
    }
  }, [terrainLayout])

  return (
    <>
      {terrainLayout.tables.map(table => {
        if (!table.piles || table.piles.length === 0) {
          console.warn(`[BacktrackingPlayer] 跟踪器 ${table.table_id} 没有桩位数据，跳过渲染`)
          return null
        }

        // 计算行的中心位置
        const avgX = table.piles.reduce((sum, pile) => sum + pile.x, 0) / table.piles.length
        const avgY = table.piles.reduce((sum, pile) => sum + pile.y, 0) / table.piles.length
        const avgZ = table.piles.reduce((sum, pile) => sum + (pile.z_top || pile.z || 0), 0) / table.piles.length

        // 获取当前时刻的角度和遮挡因子
        const angle = currentAngles[table.table_id] || 0
        const shadingFactor = currentShadingFactors[table.table_id] || 1.0

        // 计算跟踪轴方位角（默认0度，即东西向）
        const axisAzimuth = table.axis_azimuth || 0
        
        // 转换为Three.js坐标系（Y是高度）
        // avgZ 是地面高度，加上支撑杆高度（默认1.5米）得到太阳能板的高度
        const panelHeight = avgZ + 1.5
        const position = [avgX, panelHeight, avgY]
        
        // 旋转：Y轴旋转（方位角）+ Z轴旋转（跟踪角度）
        const rotation = [
          0,                              // X轴旋转
          (axisAzimuth * Math.PI) / 180,  // Y轴旋转（方位角）
          (angle * Math.PI) / 180         // Z轴旋转（跟踪角度）
        ]

        return (
          <ShadingHeatmap
            key={table.table_id}
            tableId={table.table_id}
            position={position}
            rotation={rotation}
            shadingFactor={shadingFactor}
          />
        )
      })}
    </>
  )
}

/**
 * 播放控制面板
 */
export const PlayerControls = ({ 
  isPlaying, 
  onPlayPause,
  playbackSpeed,
  onSpeedChange,
  currentTime,
  totalTime,
  onSeek
}) => {
  return (
    <div style={{
      position: 'absolute',
      bottom: '20px',
      left: '20px',
      background: 'rgba(255, 255, 255, 0.95)',
      padding: '16px',
      borderRadius: '12px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
      minWidth: '300px'
    }}>
      <div style={{ marginBottom: '12px', fontWeight: 'bold', fontSize: '14px' }}>
        回溯轨迹播放器
      </div>
      
      {/* 时间显示 */}
      <div style={{ marginBottom: '12px', fontSize: '12px', color: '#666' }}>
        {currentTime} / {totalTime}
      </div>

      {/* 播放/暂停按钮 */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <button
          onClick={onPlayPause}
          style={{
            flex: 1,
            padding: '8px 16px',
            background: isPlaying ? '#ff5722' : '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold'
          }}
        >
          {isPlaying ? '⏸ 暂停' : '▶ 播放'}
        </button>
      </div>

      {/* 播放速度 */}
      <div style={{ marginBottom: '8px' }}>
        <label style={{ fontSize: '12px', color: '#666', marginRight: '8px' }}>
          播放速度: {playbackSpeed.toFixed(1)}x
        </label>
        <input
          type="range"
          min="0.1"
          max="5.0"
          step="0.1"
          value={playbackSpeed}
          onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
          style={{ width: '100%' }}
        />
      </div>

      {/* 进度条 */}
      {onSeek && (
        <div>
          <input
            type="range"
            min="0"
            max="100"
            value={(currentTime / totalTime) * 100 || 0}
            onChange={(e) => onSeek(parseInt(e.target.value))}
            style={{ width: '100%' }}
          />
        </div>
      )}
    </div>
  )
}

export default BacktrackingPlayer



