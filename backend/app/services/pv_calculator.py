import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pvlib
from pvlib import pvsystem, modelchain, location
import logging

logger = logging.getLogger(__name__)

class PVCalculator:
    """光伏系统计算器"""

    def __init__(self, latitude: float, longitude: float, altitude: float = 0.0, timezone: str = 'Asia/Shanghai'):
        self.location = location.Location(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            tz=timezone
        )

    def calculate_diffuse_fraction(
        self,
        ghi: float,
        dhi: float
    ) -> float:
        """计算漫射辐照度分数 fd = DHI / GHI。

        根据NREL论文，漫射分数用于部分遮挡功率模型 (Equation 4)。

        Args:
            ghi: 总水平辐照度 (W/m²)
            dhi: 散射水平辐照度 (W/m²)

        Returns:
            float: 漫射辐照度分数 (0-1)
        """
        if ghi <= 0:
            return 0.0
        return min(1.0, dhi / ghi)

    def calculate_diffuse_retention(
        self,
        shading_factor: float,
        sky_model: str = 'isotropic'
    ) -> float:
        """基于天空模型计算散射辐射保留率。

        根据NREL论文，阴影区域的散射辐射约为正常值的50-70%。
        不同天空模型有不同的计算方法。

        Args:
            shading_factor: 遮挡系数 (0-1, 1表示无遮挡)
            sky_model: 天空模型类型
                - 'isotropic': 各向同性模型（默认）
                - 'hay': Hay模型
                - 'perez': Perez模型

        Returns:
            float: 散射辐射保留率 (0.4-1.0)
        """
        # 遮挡分数 fs = 1 - shading_factor
        fs = 1.0 - shading_factor

        if sky_model == 'isotropic':
            # 各向同性模型: 散射来自天空各方向
            # 阴影区域仍可接收大部分散射
            # retention = 未遮挡部分的散射 + 遮挡部分的散射
            #           = (1-fs) * 1.0 + fs * diffuse_retention_in_shadow
            diffuse_retention_in_shadow = 0.6  # 阴影区域的散射保留率
            retention = shading_factor + fs * diffuse_retention_in_shadow
        elif sky_model == 'hay':
            # Hay模型: 考虑前向散射
            # 阴影区域的散射保留率较高
            diffuse_retention_in_shadow = 0.7
            retention = shading_factor + fs * diffuse_retention_in_shadow
        elif sky_model == 'perez':
            # Perez模型: 更复杂的天空分布
            diffuse_retention_in_shadow = 0.65
            retention = shading_factor + fs * diffuse_retention_in_shadow
        else:
            retention = 0.6  # 默认保守值

        return max(0.4, min(1.0, retention))

    def calculate_partial_shading_power(
        self,
        shading_fraction: float,
        diffuse_fraction: float,
        cells_per_column: int = 12
    ) -> float:
        """部分遮挡功率损失模型 (NREL 论文 Equation 4)。

        当光伏组件被部分遮挡时，功率损失取决于遮挡比例和
        电池串的结构。

        根据论文，功率损失模型如下:
        - 当 fs < 1/N 时（轻度遮挡）: Pnorm = 1 - (1-fd) * fs * N
        - 当 fs >= 1/N 时（重度遮挡）: Pnorm = fd

        Args:
            shading_fraction: 遮挡分数 fs (0-1, 被遮挡的面积比例)
            diffuse_fraction: 漫射辐照度分数 fd = DHI / GHI
            cells_per_column: 每列电池数 N (72电池模块 N=12, 96电池模块 N=16)

        Returns:
            float: 归一化功率 Pnorm (0-1)
        """
        fs = shading_fraction
        fd = diffuse_fraction
        N = cells_per_column

        # 数值稳定性检查
        if N <= 0:
            N = 12  # 默认值

        if fs < 1.0 / N:
            # 轻度遮挡: 功率损失与遮挡面积成正比
            # Pnorm = 1 - (1-fd) * fs * N
            pnorm = 1.0 - (1.0 - fd) * fs * N
        else:
            # 重度遮挡: 功率仅等于漫射分量
            # 此时旁路二极管激活，被遮挡的电池串被旁路
            pnorm = fd

        return max(0.0, min(1.0, pnorm))

    def calculate_solar_position(self, times: pd.DatetimeIndex) -> pd.DataFrame:
        """计算太阳位置"""
        return self.location.get_solarposition(times)
    
    def calculate_irradiance(self, times: pd.DatetimeIndex, 
                           tilt: float, azimuth: float,
                           ghi: Optional[pd.Series] = None,
                           dni: Optional[pd.Series] = None,
                           dhi: Optional[pd.Series] = None) -> pd.DataFrame:
        """计算斜面辐射"""
        
        solar_position = self.calculate_solar_position(times)
        
        # 如果没有提供辐射数据，使用默认模型
        if ghi is None or dni is None or dhi is None:
            # 使用PVlib的辐射模型
            clearsky = self.location.get_clearsky(times)
            ghi = clearsky['ghi']
            dni = clearsky['dni']
            dhi = clearsky['dhi']
        
        # 计算地外直接辐射(dni_extra)
        dni_extra = pvlib.irradiance.get_extra_radiation(times)
        
        # 计算斜面辐射
        irradiance = pvlib.irradiance.get_total_irradiance(
            surface_tilt=tilt,
            surface_azimuth=azimuth,
            solar_zenith=solar_position['apparent_zenith'],
            solar_azimuth=solar_position['azimuth'],
            dni=dni,
            ghi=ghi,
            dhi=dhi,
            dni_extra=dni_extra,
            model='haydavies'
        )
        
        return irradiance
    
    def calculate_pv_power(self, irradiance: pd.DataFrame,
                          module_params: Dict[str, Any],
                          inverter_params: Dict[str, Any],
                          temperature_ambient: pd.Series,
                          shading_factor: float = 0.0,
                          shading_factors: Optional[pd.Series] = None,
                          soiling_loss: float = 0.0,
                          degradation_rate: float = 0.0,
                          # NEW: NREL 论文参数
                          use_partial_shading_model: bool = False,
                          ghi: Optional[pd.Series] = None,
                          dhi: Optional[pd.Series] = None,
                          cells_per_column: int = 12,
                          sky_model: str = 'isotropic') -> pd.DataFrame:
        """计算光伏发电功率，考虑阴影、污秽和衰减损失。

        支持两种模式：
        1. 简单模式（默认）: 使用线性遮挡模型
        2. NREL 论文模式（use_partial_shading_model=True）: 使用部分遮挡功率模型 (Equation 4)

        Args:
            irradiance: 斜面辐照度数据
            module_params: 组件参数
            inverter_params: 逆变器参数
            temperature_ambient: 环境温度序列
            shading_factor: 固定阴影损失系数
            shading_factors: 时变阴影系数序列
            soiling_loss: 污秽损失系数
            degradation_rate: 衰减率
            use_partial_shading_model: 是否使用 NREL 部分遮挡功率模型
            ghi: 总水平辐照度（用于计算 fd）
            dhi: 散射水平辐照度（用于计算 fd）
            cells_per_column: 每列电池数 N（72电池模块 N=12）
            sky_model: 天空模型（isotropic, hay, perez）

        Returns:
            pd.DataFrame: 发电功率计算结果
        """
        irradiance = irradiance.copy()

        # 计算阴影乘数（0-1，1表示无阴影损失）
        if shading_factors is not None:
            shading_multiplier = shading_factors.reindex(irradiance.index)
            shading_multiplier = shading_multiplier.ffill().bfill().fillna(1.0)
            shading_multiplier = shading_multiplier.clip(lower=0.0, upper=1.0)
            if shading_factor > 0:
                shading_multiplier = shading_multiplier * (1 - shading_factor)
        else:
            multiplier = max(0.0, min(1.0, 1 - shading_factor)) if shading_factor > 0 else 1.0
            shading_multiplier = pd.Series(multiplier, index=irradiance.index)

        # 保存原始值用于计算
        poa_direct_orig = irradiance['poa_direct'].copy()
        poa_diffuse_orig = irradiance['poa_diffuse'].copy()

        # 计算散射辐射保留率（基于天空模型）
        # 使用向量化的方式处理
        diffuse_retention_series = shading_multiplier.apply(
            lambda sf: self.calculate_diffuse_retention(sf, sky_model)
        )

        if use_partial_shading_model and ghi is not None and dhi is not None:
            # 使用 NREL 论文部分遮挡功率模型 (Equation 4)
            # 计算漫射分数 fd
            ghi_aligned = ghi.reindex(irradiance.index).fillna(0)
            dhi_aligned = dhi.reindex(irradiance.index).fillna(0)

            # 对直接辐射应用完整遮挡系数
            irradiance['poa_direct'] = poa_direct_orig * shading_multiplier

            # 对散射辐射应用部分遮挡
            irradiance['poa_diffuse'] = poa_diffuse_orig * diffuse_retention_series

            # 计算遮挡分数 fs = 1 - shading_multiplier
            shading_fraction = 1.0 - shading_multiplier

            # 计算归一化功率系数 (Equation 4)
            power_normalization = pd.Series(index=irradiance.index, dtype=float)
            for idx in irradiance.index:
                fd = self.calculate_diffuse_fraction(
                    float(ghi_aligned.loc[idx]),
                    float(dhi_aligned.loc[idx])
                )
                fs = float(shading_fraction.loc[idx])
                pnorm = self.calculate_partial_shading_power(fs, fd, cells_per_column)
                power_normalization.loc[idx] = pnorm

        else:
            # 使用传统线性遮挡模型
            # 对直接辐射应用完整遮挡系数
            irradiance['poa_direct'] = poa_direct_orig * shading_multiplier

            # 对散射辐射应用部分遮挡
            diffuse_factor = diffuse_retention_series
            irradiance['poa_diffuse'] = poa_diffuse_orig * diffuse_factor

            power_normalization = pd.Series(1.0, index=irradiance.index)

        # 重新计算总辐射
        irradiance['poa_global'] = irradiance['poa_direct'] + irradiance['poa_diffuse']
        
        # 应用污秽损失
        if soiling_loss > 0:
            irradiance['poa_global'] = irradiance['poa_global'] * (1 - soiling_loss)
        
        # 使用pvlib底层函数直接计算发电功率，避免ModelChain兼容性问题
        try:
            # 获取有效辐照度
            poa_global_effective = irradiance['poa_global']
            
            # 使用SAPM模型计算直流功率
            effective_irradiance = poa_global_effective / 1000.0  # 转换为kW/m²
            
            # 计算模块温度
            module_temp = pvlib.temperature.sapm_cell(
                poa_global_effective,
                temperature_ambient,
                wind_speed=2.0,
                a=-3.47,
                b=-0.0594,
                deltaT=3
            )
            
            # 计算温度修正系数
            temp_diff = module_temp - 25
            power_temp_coeff = module_params.get('gamma_pdc', -0.004)
            temp_correction = 1 + power_temp_coeff * temp_diff

            # 计算直流功率
            pdc0 = module_params.get('pdc0', 400)
            dc_power = pdc0 * effective_irradiance * temp_correction

            # 应用部分遮挡功率归一化 (NREL Equation 4)
            dc_power = dc_power * power_normalization
            
            # 使用Sandia逆变器模型计算交流功率
            paco = inverter_params.get('Paco', 5000)
            vdco = inverter_params.get('Vdco', 400)
            pdco = inverter_params.get('Pdco', 5200)
            pso = inverter_params.get('Pso', 100)
            c0 = inverter_params.get('C0', -0.000002)
            c1 = inverter_params.get('C1', -0.0002)
            c2 = inverter_params.get('C2', -0.005)
            c3 = inverter_params.get('C3', 0.01)
            pnt = inverter_params.get('Pnt', 50)

            inverter_params_sandia = {
                'Paco': paco,
                'Pdco': pdco,
                'Vdco': vdco,
                'Pso': pso,
                'C0': c0,
                'C1': c1,
                'C2': c2,
                'C3': c3,
                'Pnt': pnt
            }

            vd_ratio = pdco / vdco if vdco and pdco else 1
            v_dc = dc_power / vd_ratio if vd_ratio else dc_power
            if vdco:
                v_dc = v_dc.clip(upper=vdco * 1.2)

            ac_power = pvlib.inverter.sandia(v_dc=v_dc, p_dc=dc_power, inverter=inverter_params_sandia)

            if isinstance(ac_power, pd.Series):
                missing = ac_power.isna()
            else:
                missing = pd.Series(False, index=dc_power.index)

            if missing.any():
                pvwatts_ac = pvlib.inverter.pvwatts(dc_power, pdco)
                ac_power.loc[missing] = pvwatts_ac.loc[missing]

            ac_power = ac_power.fillna(pvlib.inverter.pvwatts(dc_power, pdco))

            if isinstance(ac_power, pd.Series):
                low_mask = (ac_power <= 0) & (dc_power > 0)
                ac_power.loc[low_mask] = dc_power.loc[low_mask] * 0.95
            else:
                low_mask = (ac_power <= 0) & (dc_power > 0)
                ac_power[low_mask] = dc_power[low_mask] * 0.95

            ac_power = ac_power.clip(lower=0)
            
            logger.info("使用pvlib底层函数成功计算发电功率")
            
        except Exception as e:
            logger.error(f"使用pvlib底层函数计算发电功率失败: {e}")
            # 使用简化的估算方法作为后备方案
            logger.warning("使用简化的发电功率估算方法")

            # 简化的直流功率估算
            dc_power = irradiance['poa_global'] * module_params.get('pdc0', 400) / 1000

            # 应用部分遮挡功率归一化 (NREL Equation 4)
            dc_power = dc_power * power_normalization

            # 简化的交流功率估算（考虑逆变器效率）
            inverter_efficiency = 0.95  # 默认效率95%
            try:
                ac_power = pvlib.inverter.pvwatts(dc_power, inverter_params.get('Pdco', module_params.get('pdc0', 400)))
                if isinstance(ac_power, pd.Series):
                    low_mask = (ac_power <= 0) & (dc_power > 0)
                    if low_mask.any():
                        ac_power.loc[low_mask] = dc_power.loc[low_mask] * inverter_efficiency
                else:
                    low_mask = (ac_power <= 0) & (dc_power > 0)
                    if low_mask.any():
                        ac_power[low_mask] = dc_power[low_mask] * inverter_efficiency
            except Exception:
                ac_power = dc_power * inverter_efficiency

            # 简化的模块温度估算
            module_temp = temperature_ambient + irradiance['poa_global'] * 0.03
        
        # 应用性能衰减
        dc_power = dc_power * (1 - degradation_rate)
        ac_power = ac_power * (1 - degradation_rate)
        
        result_df = pd.DataFrame({
            'dc_power': dc_power,
            'ac_power': ac_power,
            'efficiency': ac_power / dc_power if dc_power.sum() > 0 else 0,
            'module_temperature': module_temp,
            'shading_multiplier': shading_multiplier,
            'irradiance_global': irradiance['poa_global'],
            'irradiance_direct': irradiance['poa_direct'],
            'irradiance_diffuse': irradiance['poa_diffuse']
        })

        numeric_cols = ['dc_power', 'ac_power', 'efficiency', 'module_temperature', 'shading_multiplier', 'irradiance_global', 'irradiance_direct', 'irradiance_diffuse']
        result_df[numeric_cols] = result_df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)
        return result_df
    
    def calculate_energy_yield(self, power_data: pd.DataFrame, 
                             time_resolution: str = 'hourly') -> Dict[str, float]:
        """计算发电量"""
        
        if time_resolution == 'hourly':
            # 小时数据直接积分
            energy_daily = power_data['ac_power'].resample('D').sum() / 1000  # kWh
            energy_monthly = power_data['ac_power'].resample('M').sum() / 1000
            energy_yearly = power_data['ac_power'].sum() / 1000
        else:
            # 需要根据时间分辨率调整
            energy_daily = power_data['ac_power'].sum() / 1000
            energy_monthly = energy_daily * 30
            energy_yearly = energy_daily * 365
        
        return {
            'daily_energy': energy_daily.mean() if hasattr(energy_daily, 'mean') else energy_daily,
            'monthly_energy': energy_monthly.mean() if hasattr(energy_monthly, 'mean') else energy_monthly,
            'yearly_energy': energy_yearly,
            'capacity_factor': energy_yearly / (power_data['ac_power'].max() * 8760 / 1000) if power_data['ac_power'].max() > 0 else 0
        }
    
    def calculate_shading_analysis(self, obstacles: List[Dict[str, Any]], 
                                 start_date: str, end_date: str) -> Dict[str, Any]:
        """计算阴影分析，考虑障碍物对光伏板的影响"""
        
        # 生成时间序列
        times = pd.date_range(start=start_date, end=end_date, freq='H', tz=self.location.tz)
        
        # 计算太阳位置
        solar_position = self.location.get_solarposition(times)
        
        # 初始化阴影分析结果
        shading_results = {
            'times': times,
            'shading_factors': [],
            'obstacle_impacts': []
        }
        
        for obstacle in obstacles:
            # 计算障碍物阴影影响
            shading_factor = self._calculate_obstacle_shading(obstacle, solar_position)
            shading_results['shading_factors'].append(shading_factor)
            shading_results['obstacle_impacts'].append({
                'name': obstacle.get('name', 'Unknown'),
                'max_shading': shading_factor.max(),
                'avg_shading': shading_factor.mean(),
                'shading_hours': len(shading_factor[shading_factor > 0.1])
            })
        
        # 计算总阴影影响
        if shading_results['shading_factors']:
            total_shading = pd.concat(shading_results['shading_factors'], axis=1).max(axis=1)
            shading_results['total_shading'] = total_shading
            shading_results['summary'] = {
                'max_total_shading': total_shading.max(),
                'avg_total_shading': total_shading.mean(),
                'total_shading_hours': len(total_shading[total_shading > 0.1])
            }
        
        return shading_results
    
    def _calculate_obstacle_shading(self, obstacle: Dict[str, Any], 
                                  solar_position: pd.DataFrame) -> pd.Series:
        """计算单个障碍物的阴影影响"""
        
        # 获取障碍物参数
        height = obstacle.get('height', 0)  # 障碍物高度(m)
        distance = obstacle.get('distance', 0)  # 障碍物距离(m)
        azimuth = obstacle.get('azimuth', 0)  # 障碍物方位角(度)
        
        # 计算阴影角度
        shading_angles = np.arctan(height / distance) if distance > 0 else 0
        
        # 计算太阳高度角与障碍物高度的关系
        sun_elevation = solar_position['elevation']
        sun_azimuth = solar_position['azimuth']
        
        # 计算阴影影响
        shading_factor = np.zeros(len(sun_elevation))
        
        for i, (elev, azim) in enumerate(zip(sun_elevation, sun_azimuth)):
            if elev > 0:  # 太阳在地平线以上
                # 计算太阳与障碍物的角度差
                azimuth_diff = abs(azim - azimuth)
                if azimuth_diff > 180:
                    azimuth_diff = 360 - azimuth_diff
                
                # 如果太阳在障碍物方向且高度角小于阴影角度，则产生阴影
                if azimuth_diff < 45 and elev < np.degrees(shading_angles):
                    shading_factor[i] = 1 - (elev / np.degrees(shading_angles))
        
        return pd.Series(shading_factor, index=solar_position.index)
    
    def calculate_economic_analysis(self, energy_yield: Dict[str, float],
                                  system_cost: float,
                                  electricity_price: float = 0.5,
                                  inflation_rate: float = 0.03,
                                  discount_rate: float = 0.08,
                                  lifetime: int = 25,
                                  opex_percentage: float = 0.01) -> Dict[str, float]:
        """计算经济性分析"""
        
        yearly_revenue = energy_yield['yearly_energy'] * electricity_price
        yearly_opex = system_cost * opex_percentage  # 年运维成本
        
        # 计算净现值(NPV)
        npv = -system_cost
        for year in range(1, lifetime + 1):
            # 考虑发电量衰减（每年0.5%）
            degraded_energy = energy_yield['yearly_energy'] * (1 - 0.005) ** (year - 1)
            revenue = degraded_energy * electricity_price * (1 + inflation_rate) ** (year - 1)
            net_cashflow = revenue - yearly_opex
            discounted_cashflow = net_cashflow / (1 + discount_rate) ** year
            npv += discounted_cashflow
        
        # 计算平准化度电成本(LCOE)
        total_energy = sum([energy_yield['yearly_energy'] * (1 - 0.005) ** year for year in range(lifetime)])
        total_cost = system_cost + sum([yearly_opex / (1 + discount_rate) ** year for year in range(1, lifetime + 1)])
        lcoe = total_cost / total_energy if total_energy > 0 else float('inf')
        
        # 计算投资回收期
        cumulative_cashflow = -system_cost
        payback_period = lifetime
        for year in range(1, lifetime + 1):
            degraded_energy = energy_yield['yearly_energy'] * (1 - 0.005) ** (year - 1)
            revenue = degraded_energy * electricity_price
            net_cashflow = revenue - yearly_opex
            cumulative_cashflow += net_cashflow
            if cumulative_cashflow >= 0:
                payback_period = year
                break
        
        return {
            'npv': npv,
            'lcoe': lcoe,
            'payback_period': payback_period,
            'irr': self._calculate_irr(system_cost, yearly_revenue - yearly_opex, lifetime, inflation_rate),
            'total_revenue': yearly_revenue * lifetime,
            'total_cost': system_cost + yearly_opex * lifetime,
            'roi': (yearly_revenue * lifetime - system_cost - yearly_opex * lifetime) / system_cost if system_cost > 0 else 0
        }
    
    def _calculate_irr(self, initial_cost: float, yearly_cashflow: float, 
                      years: int, growth_rate: float) -> float:
        """计算内部收益率(IRR)"""
        
        def npv_func(rate):
            npv = -initial_cost
            for year in range(1, years + 1):
                cashflow = yearly_cashflow * (1 + growth_rate) ** (year - 1)
                npv += cashflow / (1 + rate) ** year
            return npv
        
        # 使用二分法求解IRR
        low, high = 0.0, 0.5
        for _ in range(100):
            mid = (low + high) / 2
            if npv_func(mid) > 0:
                low = mid
            else:
                high = mid
            if high - low < 1e-6:
                break
        
        return (low + high) / 2

# 常用光伏组件参数模板
MODULE_TEMPLATES = {
    'mono_si': {
        'pdc0': 400,  # 额定功率(W)
        'V_mp': 37.2,  # 最大功率点电压(V)
        'I_mp': 10.75, # 最大功率点电流(A)
        'V_oc': 45.5,  # 开路电压(V)
        'I_sc': 11.35, # 短路电流(A)
        'alpha_sc': 0.0005,  # 电流温度系数
        'beta_oc': -0.003,   # 电压温度系数
        'gamma_pdc': -0.004, # 功率温度系数
        'cells_in_series': 72
    },
    'poly_si': {
        'pdc0': 380,
        'V_mp': 35.8,
        'I_mp': 10.61,
        'V_oc': 43.9,
        'I_sc': 11.12,
        'alpha_sc': 0.0006,
        'beta_oc': -0.0032,
        'gamma_pdc': -0.0042,
        'cells_in_series': 72
    }
}

# 常用逆变器参数模板
INVERTER_TEMPLATES = {
    'standard': {
        'Paco': 5000,      # 最大交流功率(W)
        'Vdco': 400,       # 额定直流电压(V)
        'Pdco': 5200,      # 额定直流功率(W)
        'Vmin': 150,       # 最小直流电压(V)
        'Vmax': 600,       # 最大直流电压(V)
        'Mppt_low': 150,   # MPPT下限(V)
        'Mppt_high': 550   # MPPT上限(V)
    }
}