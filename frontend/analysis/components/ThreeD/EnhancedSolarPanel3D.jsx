import React, { useState, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stats } from '@react-three/drei'
import * as THREE from 'three'

import TerrainMesh from './TerrainMesh'
import BacktrackingPlayer, { PlayerControls } from './BacktrackingPlayer'
import { ShadingLegend } from './ShadingHeatmap'
import { terrainApi } from '../../services/api'

/**
 * 增强版太阳能板3D场景
 * 支持真实地形、回溯轨迹播放和遮挡热力图
 */
const EnhancedSolarPanel3D = ({ 
  simulationId = null,
  enableHeightMap = false,
  enableShadingHeatmap = true,
  showStats = false 
}) => {
  const [terrainData, setTerrainData] = useState(null)
  const [backtrackingData, setBacktrackingData] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0)
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 加载地形数据
  useEffect(() => {
    const loadTerrainData = async () => {
      try {
        setLoading(true)
        const data = await terrainApi.getLayout()
        setTerrainData(data)
        setError(null)
      } catch (err) {
        console.error('加载地形数据失败:', err)
        setError('无法加载地形数据')
      } finally {
        setLoading(false)
      }
    }

    loadTerrainData()
  }, [])

  // 加载回溯数据（如果提供了simulationId或需要默认数据）
  useEffect(() => {
    const loadBacktrackingData = async () => {
      try {
        if (simulationId) {
          // TODO: 调用实际的API获取回溯数据
          // const data = await simulationApi.getShadingData(simulationId)
        }
        
        // 生成完整的模拟数据，覆盖所有跟踪器
        if (!terrainData || !terrainData.tables) {
          return
        }

        const tableIds = terrainData.tables.map(t => t.table_id)
        const timestamps = [
          '2024-01-15T06:00:00', 
          '2024-01-15T09:00:00', 
          '2024-01-15T12:00:00', 
          '2024-01-15T15:00:00', 
          '2024-01-15T18:00:00'
        ]
        const anglesSequence = [-45, -20, 0, 20, 45]
        
        const mockData = {
          timestamps,
          angles: anglesSequence.map(angle => {
            const angleMap = {}
            tableIds.forEach(id => {
              angleMap[id] = angle
            })
            return angleMap
          }),
          shadingFactors: timestamps.map((_, timeIdx) => {
            const factorMap = {}
            tableIds.forEach((id, idx) => {
              // 根据位置和时间生成不同的遮挡因子
              const baseFactor = 0.75 + Math.random() * 0.25  // 0.75 - 1.0
              const timeFactor = timeIdx === 2 ? 1.0 : 0.85 + Math.random() * 0.15  // 正午最好
              factorMap[id] = Math.min(baseFactor * timeFactor, 1.0)
            })
            return factorMap
          })
        }
        
        setBacktrackingData(mockData)
      } catch (err) {
        console.error('加载回溯数据失败:', err)
      }
    }

    if (terrainData) {
      loadBacktrackingData()
    }
  }, [simulationId, terrainData])

  // 播放控制
  const handlePlayPause = () => {
    setIsPlaying(!isPlaying)
  }

  const handleSpeedChange = (speed) => {
    setPlaybackSpeed(speed)
  }

  const handleSeek = (percentage) => {
    if (backtrackingData && backtrackingData.timestamps) {
      const index = Math.floor((percentage / 100) * backtrackingData.timestamps.length)
      setCurrentTimeIndex(index)
    }
  }

  // 格式化时间
  const formatTime = (index) => {
    if (!backtrackingData || !backtrackingData.timestamps) return '00:00'
    const timestamp = backtrackingData.timestamps[index]
    if (!timestamp) return '00:00'
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  if (loading) {
    return (
      <div style={{ 
        width: '100%', 
        height: '600px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: '#f5f5f5',
        borderRadius: '8px'
      }}>
        <div>加载中...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ 
        width: '100%', 
        height: '600px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: '#f5f5f5',
        borderRadius: '8px',
        color: '#f44336'
      }}>
        <div>{error}</div>
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height: '600px', position: 'relative', borderRadius: '8px', overflow: 'hidden' }}>
      <Canvas
        shadows
        camera={{ position: [50, 40, 50], fov: 50 }}
        style={{ background: '#87CEEB' }}
      >
        {/* 基础光照 */}
        <ambientLight intensity={0.6} />
        <hemisphereLight intensity={0.8} groundColor="#4a7c59" color="#87CEEB" />
        
        {/* 太阳光 */}
        <directionalLight
          position={[30, 40, 20]}
          intensity={1.5}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
          shadow-camera-far={200}
          shadow-camera-left={-50}
          shadow-camera-right={50}
          shadow-camera-top={50}
          shadow-camera-bottom={-50}
        />

        {/* 真实地形 */}
        <TerrainMesh 
          terrainData={terrainData} 
          showHeightMap={enableHeightMap}
        />

        {/* 回溯播放器（显示跟踪器和遮挡热力图）*/}
        {terrainData && (
          <BacktrackingPlayer
            backtrackingData={backtrackingData}
            terrainLayout={terrainData}
            isPlaying={isPlaying}
            playbackSpeed={playbackSpeed}
            currentTimeIndex={currentTimeIndex}
            onTimeIndexChange={setCurrentTimeIndex}
            enableShadingHeatmap={enableShadingHeatmap}
          />
        )}

        {/* 坐标轴辅助 */}
        <axesHelper args={[10]} />
        
        {/* 网格辅助 */}
        <gridHelper args={[200, 40, '#666666', '#888888']} />

        {/* 轨道控制 */}
        <OrbitControls 
          enableDamping
          dampingFactor={0.05}
          minDistance={10}
          maxDistance={200}
          maxPolarAngle={Math.PI / 2.1}
        />

        {/* 性能统计 */}
        {showStats && <Stats />}
      </Canvas>

      {/* 播放控制面板 */}
      {backtrackingData && (
        <PlayerControls
          isPlaying={isPlaying}
          onPlayPause={handlePlayPause}
          playbackSpeed={playbackSpeed}
          onSpeedChange={handleSpeedChange}
          currentTime={formatTime(currentTimeIndex)}
          totalTime={formatTime(backtrackingData.timestamps.length - 1)}
          onSeek={handleSeek}
        />
      )}

      {/* 遮挡热力图图例 */}
      {enableShadingHeatmap && backtrackingData && (
        <ShadingLegend />
      )}

      {/* 功能切换按钮 */}
      <div style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: '8px 16px',
            background: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          🔄 刷新数据
        </button>
      </div>

      {/* 信息面板 */}
      <div style={{
        position: 'absolute',
        top: '20px',
        left: '20px',
        background: 'rgba(255, 255, 255, 0.9)',
        padding: '12px',
        borderRadius: '8px',
        fontSize: '12px',
        maxWidth: '200px'
      }}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>场景信息</div>
        {terrainData && terrainData.tables && (
          <div>跟踪行数: {terrainData.tables.length}</div>
        )}
        {terrainData && terrainData.metadata && (
          <div>总桩点数: {terrainData.metadata.total_piles || 'N/A'}</div>
        )}
        {backtrackingData && (
          <div>时间点数: {backtrackingData.timestamps.length}</div>
        )}
      </div>
    </div>
  )
}

export default EnhancedSolarPanel3D



