import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class WeatherService:
    """天气数据服务"""
    
    def __init__(self):
        self.nasa_sse_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        self.nasa_power_hourly_url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
        self.meteonorm_url = "https://api.meteonorm.com/v1"
        
    async def get_nasa_sse_data(self, latitude: float, longitude: float, 
                               start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取NASA SSE气象数据"""
        
        try:
            params = {
                'parameters': 'T2M,WS10M,RH2M,PS,ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DIFF',
                'community': 'RE',
                'longitude': longitude,
                'latitude': latitude,
                'start': start_date,
                'end': end_date,
                'format': 'JSON'
            }
            
            if settings.nasa_sse_api_key:
                params['api_key'] = settings.nasa_sse_api_key
            
            response = requests.get(self.nasa_sse_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析NASA SSE数据
            weather_data = []
            properties = data.get('properties', {}).get('parameter', {})
            
            for date_str in properties.get('T2M', {}).keys():
                date = datetime.strptime(date_str, '%Y%m%d')
                
                weather_data.append({
                    'timestamp': date,
                    'temperature': properties.get('T2M', {}).get(date_str),
                    'wind_speed': properties.get('WS10M', {}).get(date_str),
                    'humidity': properties.get('RH2M', {}).get(date_str),
                    'pressure': properties.get('PS', {}).get(date_str),
                    'ghi': properties.get('ALLSKY_SFC_SW_DWN', {}).get(date_str),
                    'dhi': properties.get('ALLSKY_SFC_SW_DIFF', {}).get(date_str)
                })
            
            return pd.DataFrame(weather_data)
            
        except Exception as e:
            logger.error(f"获取NASA SSE数据失败: {e}")
            return None

    async def get_nasa_power_hourly_data(self, latitude: float, longitude: float,
                                         start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取NASA POWER小时级气象数据"""

        try:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            params = {
                "parameters": "T2M,WS10M,RH2M,PS,ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF",
                "community": "RE",
                "longitude": longitude,
                "latitude": latitude,
                "start": start_dt.strftime("%Y%m%d"),
                "end": end_dt.strftime("%Y%m%d"),
                "format": "JSON",
            }

            if settings.nasa_sse_api_key:
                params["api_key"] = settings.nasa_sse_api_key

            response = requests.get(self.nasa_power_hourly_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            properties = data.get("properties", {}).get("parameter", {})

            if not properties:
                logger.warning("NASA POWER小时数据返回为空")
                return None

            param_map = {
                "T2M": "temperature",
                "WS10M": "wind_speed",
                "RH2M": "humidity",
                "PS": "pressure",
                "ALLSKY_SFC_SW_DWN": "ghi",
                "ALLSKY_SFC_SW_DNI": "dni",
                "ALLSKY_SFC_SW_DIFF": "dhi",
            }

            records: Dict[datetime, Dict[str, Any]] = {}

            for param_name, series in properties.items():
                mapped_key = param_map.get(param_name)
                if series is None:
                    continue

                for timestamp_str, value in series.items():
                    if value is None:
                        continue

                    try:
                        if len(timestamp_str) == 10:  # YYYYMMDDHH
                            timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H")
                        elif len(timestamp_str) == 8:  # 回退到日级
                            timestamp = datetime.strptime(timestamp_str, "%Y%m%d")
                        else:
                            timestamp = pd.to_datetime(timestamp_str)
                    except Exception:
                        logger.debug(f"无法解析NASA小时数据时间戳: {timestamp_str}")
                        continue

                    entry = records.setdefault(timestamp, {"timestamp": timestamp})

                    key = mapped_key or param_name.lower()
                    entry[key] = value

            if not records:
                logger.warning("NASA POWER小时数据解析后为空")
                return None

            df = pd.DataFrame(records.values()).sort_values("timestamp")

            for col in ["temperature", "wind_speed", "humidity", "pressure", "ghi", "dni", "dhi"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            return df

        except Exception as e:
            logger.error(f"获取NASA POWER小时数据失败: {e}")
            return None
    
    async def get_meteonorm_data(self, latitude: float, longitude: float,
                                start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取Meteonorm气象数据"""
        
        if not settings.meteonorm_api_key:
            logger.warning("Meteonorm API密钥未配置")
            return None
            
        try:
            headers = {
                'Authorization': f'Bearer {settings.meteonorm_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'latitude': latitude,
                'longitude': longitude,
                'start': start_date,
                'end': end_date,
                'parameters': ['temperature', 'humidity', 'wind_speed', 'global_radiation', 'diffuse_radiation']
            }
            
            response = requests.post(
                f"{self.meteonorm_url}/data",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 解析Meteonorm数据
            weather_data = []
            for item in data.get('data', []):
                weather_data.append({
                    'timestamp': datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')),
                    'temperature': item.get('temperature'),
                    'humidity': item.get('humidity'),
                    'wind_speed': item.get('wind_speed'),
                    'ghi': item.get('global_radiation'),
                    'dhi': item.get('diffuse_radiation')
                })
            
            return pd.DataFrame(weather_data)
            
        except Exception as e:
            logger.error(f"获取Meteonorm数据失败: {e}")
            return None
    
    def generate_synthetic_data(self, latitude: float, longitude: float,
                               start_date: str, end_date: str) -> pd.DataFrame:
        """生成合成气象数据（当API不可用时）"""
        
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 基于纬度和季节生成合理的数据
        data = []
        for date in dates:
            # 季节性温度变化
            day_of_year = date.timetuple().tm_yday
            base_temp = 15 + 10 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
            
            # 纬度影响
            lat_effect = (latitude - 30) * 0.5
            base_temp -= lat_effect
            
            # 日温度变化
            daily_variation = 8 * np.sin(2 * np.pi * date.hour / 24) if hasattr(date, 'hour') else 0
            
            temperature = base_temp + daily_variation + np.random.normal(0, 3)
            
            # 辐射数据（基于季节和天气）
            seasonal_factor = 0.7 + 0.3 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
            weather_factor = max(0.3, np.random.beta(2, 2))  # 模拟天气变化
            
            ghi = 800 * seasonal_factor * weather_factor + np.random.normal(0, 50)
            dhi = ghi * (0.3 + 0.2 * np.random.random())  # 散射辐射比例
            
            data.append({
                'timestamp': date,
                'temperature': max(-20, min(45, temperature)),
                'humidity': max(20, min(95, 60 + np.random.normal(0, 15))),
                'wind_speed': max(0, min(20, 3 + np.random.exponential(2))),
                'pressure': 1013 + np.random.normal(0, 10),
                'ghi': max(0, ghi),
                'dhi': max(0, dhi),
                'dni': max(0, ghi - dhi)  # 直接辐射
            })
        
        return pd.DataFrame(data)
    
    async def get_weather_data(self, latitude: float, longitude: float,
                              start_date: str, end_date: str,
                              source: str = 'nasa_sse',
                              time_resolution: str = 'daily') -> pd.DataFrame:
        """获取气象数据（优先使用API，失败时使用合成数据）"""
        
        df = None
        used_api = True
        resolution = None
        
        if source == 'nasa_sse':
            if time_resolution == 'hourly':
                df = await self.get_nasa_power_hourly_data(latitude, longitude, start_date, end_date)
                resolution = 'hourly' if df is not None else None

            if df is None or df.empty:
                df = await self.get_nasa_sse_data(latitude, longitude, start_date, end_date)
                resolution = resolution or 'daily'
        elif source == 'meteonorm':
            df = await self.get_meteonorm_data(latitude, longitude, start_date, end_date)
            resolution = 'hourly' if df is not None and not df.empty else None
        
        # 如果API获取失败，使用合成数据
        if df is None or df.empty:
            logger.warning(f"使用合成气象数据 ({source} API不可用)")
            df = self.generate_synthetic_data(latitude, longitude, start_date, end_date)
            used_api = False
            resolution = 'daily'
        
        # 数据清洗和填充
        df = self._clean_weather_data(df)
        
        if not resolution and 'timestamp' in df.columns:
            try:
                ts_sorted = pd.to_datetime(df['timestamp']).sort_values()
                if len(ts_sorted) > 1:
                    delta = ts_sorted.diff().dropna().dt.total_seconds().min()
                    if pd.notna(delta):
                        resolution = 'hourly' if delta <= 3600 else 'daily'
            except Exception:
                resolution = None

        # 标记是否使用了合成数据
        df.attrs['used_synthetic_data'] = not used_api
        if resolution:
            df.attrs['resolution'] = resolution
        
        return df
    
    def _clean_weather_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗气象数据"""
        
        # 确保时间戳为datetime类型
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 设置时间索引
        df = df.set_index('timestamp').sort_index()
        
        # 填充缺失值
        numeric_cols = ['temperature', 'humidity', 'wind_speed', 'pressure', 'ghi', 'dhi', 'dni']
        for col in numeric_cols:
            if col in df.columns:
                # 使用前向填充，然后后向填充
                df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
                
                # 如果仍有缺失值，使用插值
                if df[col].isna().any():
                    df[col] = df[col].interpolate()
        
        return df.reset_index()
    
    def calculate_hourly_data(self, daily_df: pd.DataFrame, start_date: str, end_date: str, time_resolution: str = 'hourly') -> pd.DataFrame:
        """将日数据转换为小时数据，确保与PV计算器时间序列完全匹配"""
        
        if daily_df.empty:
            return pd.DataFrame()
        
        # 根据时间分辨率创建目标时间序列
        if time_resolution == 'hourly':
            # 创建完整的小时时间序列，与PV计算器完全匹配
            start_time = pd.to_datetime(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = pd.to_datetime(end_date).replace(hour=23, minute=0, second=0, microsecond=0)
            hourly_index = pd.date_range(start=start_time, end=end_time, freq='H', inclusive='both')
        else:
            # 对于其他时间分辨率，使用原始逻辑
            start_time = daily_df['timestamp'].min().replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = daily_df['timestamp'].max().replace(hour=23, minute=0, second=0, microsecond=0)
            hourly_index = pd.date_range(start=start_time, end=end_time, freq='H', inclusive='both')
        
        logger.info(f"转换日数据到小时数据: 原始数据长度={len(daily_df)}, 目标小时数={len(hourly_index)}")
        
        hourly_data = []
        
        for timestamp in hourly_index:
            # 找到对应的日期
            date = timestamp.date()
            daily_row = daily_df[daily_df['timestamp'].dt.date == date]
            
            if not daily_row.empty:
                row = daily_row.iloc[0].copy()
                hour = timestamp.hour
                
                # 调整温度（日变化）
                if 'temperature' in row:
                    daily_min = row['temperature'] - 5
                    daily_max = row['temperature'] + 5
                    # 正弦曲线模拟日温度变化
                    temp_variation = (daily_max - daily_min) * 0.5 * np.sin(2 * np.pi * (hour - 6) / 24)
                    row['temperature'] = row['temperature'] + temp_variation
                
                # 调整辐射（日变化）
                if 'ghi' in row:
                    # 太阳高度角影响
                    solar_noon = 12  # 正午
                    hour_diff = abs(hour - solar_noon)
                    radiation_factor = max(0, np.cos(np.pi * hour_diff / 12))
                    row['ghi'] = row['ghi'] * radiation_factor
                    
                    if 'dhi' in row:
                        row['dhi'] = row['dhi'] * radiation_factor
                    if 'dni' in row:
                        row['dni'] = row['dni'] * radiation_factor
                
                row['timestamp'] = timestamp
                hourly_data.append(row)
            else:
                # 如果没有对应的日数据，创建默认数据
                default_row = {
                    'timestamp': timestamp,
                    'temperature': 20,
                    'humidity': 60,
                    'wind_speed': 3,
                    'pressure': 1013,
                    'ghi': 0,
                    'dhi': 0,
                    'dni': 0
                }
                hourly_data.append(default_row)
        
        result_df = pd.DataFrame(hourly_data)
        logger.info(f"小时数据转换完成: 结果数据长度={len(result_df)}")
        return result_df