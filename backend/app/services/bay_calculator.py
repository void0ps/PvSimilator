"""
Bay级别的辐照度计算和加权平均

实现论文公式：
POA = 1/8 × POA₁ + 2/8 × POA₂ + 5/8 × POA₃
"""
from __future__ import annotations

from typing import Dict, List
import numpy as np
import pandas as pd
import pvlib

from app.models.bay import Bay
from app.services.ray_tracing import RayTracer, create_sun_vector


class BayCalculator:
    """
    Bay级别的PV计算器
    
    实现论文中的bay级别建模和加权平均方法
    """
    
    def __init__(
        self,
        use_ray_tracing: bool = True,
        diffuse_fraction: float = 0.38
    ):
        """
        初始化Bay计算器
        
        Args:
            use_ray_tracing: 是否使用射线追踪（否则使用几何近似）
            diffuse_fraction: 漫射比例（完全遮挡时的贡献）
        """
        self.use_ray_tracing = use_ray_tracing
        self.diffuse_fraction = diffuse_fraction
        self.ray_tracer = RayTracer() if use_ray_tracing else None
    
    def compute_bay_poa(
        self,
        bays: List[Bay],
        times: pd.DatetimeIndex,
        latitude: float,
        longitude: float,
        ghi: pd.Series,
        dni: pd.Series,
        dhi: pd.Series,
        rotation_angles: Dict[str, pd.Series]
    ) -> Dict[str, pd.Series]:
        """
        为每个bay计算POA辐照度
        
        Args:
            bays: Bay对象列表
            times: 时间索引
            latitude: 纬度
            longitude: 经度
            ghi: 全局水平辐照度
            dni: 直接法向辐照度
            dhi: 漫射水平辐照度
            rotation_angles: 每个bay的旋转角度 {bay_id: Series}
            
        Returns:
            每个bay的POA辐照度 {bay_id: Series}
        """
        # 计算太阳位置
        location = pvlib.location.Location(latitude, longitude)
        solar_position = location.get_solarposition(times)
        
        # 计算遮挡因子（如果使用射线追踪）
        if self.use_ray_tracing:
            shading_factors = self._compute_shading_factors_ray_tracing(
                bays,
                solar_position,
                rotation_angles
            )
        else:
            # 使用现有的几何方法（fallback）
            shading_factors = {bay.bay_id: pd.Series(1.0, index=times) for bay in bays}
        
        # 为每个bay计算POA
        bay_poa = {}
        for bay in bays:
            poa = self._compute_single_bay_poa(
                bay,
                times,
                solar_position,
                ghi,
                dni,
                dhi,
                rotation_angles[bay.bay_id],
                shading_factors[bay.bay_id]
            )
            bay_poa[bay.bay_id] = poa
        
        return bay_poa
    
    def _compute_shading_factors_ray_tracing(
        self,
        bays: List[Bay],
        solar_position: pd.DataFrame,
        rotation_angles: Dict[str, pd.Series]
    ) -> Dict[str, pd.Series]:
        """
        使用射线追踪计算遮挡因子
        
        Args:
            bays: Bay对象列表
            solar_position: 太阳位置DataFrame
            rotation_angles: 旋转角度字典
            
        Returns:
            每个bay的遮挡因子 {bay_id: Series}
        """
        n_timesteps = len(solar_position)
        bay_ids = [bay.bay_id for bay in bays]
        
        # 创建太阳向量列表
        sun_vectors = []
        for idx in solar_position.index:
            azimuth = solar_position.loc[idx, 'azimuth']
            elevation = solar_position.loc[idx, 'apparent_elevation']
            
            if elevation > 0:  # 只在太阳高于地平线时计算
                sun_vec = create_sun_vector(azimuth, elevation)
            else:
                sun_vec = np.array([0.0, 0.0, 0.0])  # 夜间
            
            sun_vectors.append(sun_vec)
        
        # 准备旋转角度矩阵 [n_timesteps x n_bays]
        rotation_matrix = []
        for idx in solar_position.index:
            angles_at_t = [rotation_angles[bay.bay_id].loc[idx] for bay in bays]
            rotation_matrix.append(angles_at_t)
        
        # 计算遮挡矩阵
        shading_matrix = self.ray_tracer.compute_shading_matrix(
            bays,
            sun_vectors,
            rotation_matrix
        )
        
        # 转换为遮挡因子字典
        shading_factors = {}
        for i, bay in enumerate(bays):
            # 遮挡矩阵：1=无遮挡，0=完全遮挡
            # 完全遮挡时使用漫射比例
            factors = shading_matrix[:, i]
            factors = np.where(factors == 0, self.diffuse_fraction, 1.0)
            
            shading_factors[bay.bay_id] = pd.Series(
                factors,
                index=solar_position.index
            )
        
        return shading_factors
    
    def _compute_single_bay_poa(
        self,
        bay: Bay,
        times: pd.DatetimeIndex,
        solar_position: pd.DataFrame,
        ghi: pd.Series,
        dni: pd.Series,
        dhi: pd.Series,
        rotation_angles: pd.Series,
        shading_factor: pd.Series
    ) -> pd.Series:
        """
        计算单个bay的POA辐照度
        
        Args:
            bay: Bay对象
            times: 时间索引
            solar_position: 太阳位置
            ghi: 全局水平辐照度
            dni: 直接法向辐照度
            dhi: 漫射水平辐照度
            rotation_angles: 该bay的旋转角度
            shading_factor: 该bay的遮挡因子
            
        Returns:
            POA辐照度Series
        """
        poa_list = []
        
        for idx in times:
            # 获取该时刻的参数
            tilt = rotation_angles.loc[idx] if idx in rotation_angles.index else 0.0
            
            # 考虑axis_tilt的影响（简化）
            effective_tilt = abs(tilt)  # + bay.axis_tilt
            
            # 方位角（假设跟踪轴为南北向）
            surface_azimuth = bay.axis_azimuth
            
            # 使用pvlib计算POA
            try:
                poa_components = pvlib.irradiance.get_total_irradiance(
                    surface_tilt=effective_tilt,
                    surface_azimuth=surface_azimuth,
                    solar_zenith=solar_position.loc[idx, 'apparent_zenith'],
                    solar_azimuth=solar_position.loc[idx, 'azimuth'],
                    dni=dni.loc[idx],
                    ghi=ghi.loc[idx],
                    dhi=dhi.loc[idx],
                    model='haydavies'
                )
                poa = poa_components['poa_global']
            except:
                poa = 0.0
            
            # 应用遮挡因子
            poa *= shading_factor.loc[idx] if idx in shading_factor.index else 1.0
            
            poa_list.append(poa)
        
        return pd.Series(poa_list, index=times)
    
    def weighted_average_poa(
        self,
        bay_poa: Dict[str, pd.Series],
        bays: List[Bay]
    ) -> pd.Series:
        """
        按模块数量加权平均POA
        
        实现论文公式：
        POA = (m₁/M)×POA₁ + (m₂/M)×POA₂ + ... + (mₙ/M)×POAₙ
        
        其中 mᵢ 是bay i的模块数量，M是总模块数量
        
        Args:
            bay_poa: 每个bay的POA {bay_id: Series}
            bays: Bay对象列表
            
        Returns:
            加权平均POA Series
        """
        # 计算总模块数
        total_modules = sum(bay.module_count for bay in bays)
        
        if total_modules == 0:
            # 没有模块，返回零
            first_bay_id = list(bay_poa.keys())[0]
            return pd.Series(0.0, index=bay_poa[first_bay_id].index)
        
        # 初始化加权POA
        first_bay_id = list(bay_poa.keys())[0]
        weighted_poa = pd.Series(0.0, index=bay_poa[first_bay_id].index)
        
        # 累加加权贡献
        for bay in bays:
            weight = bay.module_count / total_modules
            weighted_poa += bay_poa[bay.bay_id] * weight
        
        return weighted_poa
    
    def compute_plant_poa(
        self,
        bays: List[Bay],
        times: pd.DatetimeIndex,
        latitude: float,
        longitude: float,
        ghi: pd.Series,
        dni: pd.Series,
        dhi: pd.Series,
        rotation_angles: Dict[str, pd.Series]
    ) -> pd.Series:
        """
        计算整个电站的加权平均POA
        
        这是主要的公开接口，组合了bay级别计算和加权平均
        
        Args:
            bays: Bay对象列表
            times: 时间索引
            latitude: 纬度
            longitude: 经度
            ghi: 全局水平辐照度
            dni: 直接法向辐照度
            dhi: 漫射水平辐照度
            rotation_angles: 每个bay的旋转角度
            
        Returns:
            加权平均POA Series
        """
        # 1. 为每个bay计算POA
        bay_poa = self.compute_bay_poa(
            bays, times, latitude, longitude,
            ghi, dni, dhi, rotation_angles
        )
        
        # 2. 加权平均
        plant_poa = self.weighted_average_poa(bay_poa, bays)
        
        return plant_poa

















