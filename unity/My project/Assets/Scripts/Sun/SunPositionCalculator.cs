using System;
using UnityEngine;

namespace PVSimulator.Sun
{
    /// <summary>
    /// 太阳位置计算器 - 使用简化算法
    /// </summary>
    public static class SunPositionCalculator
    {
        /// <summary>
        /// 计算太阳位置
        /// </summary>
        /// <param name="latitude">纬度（度）</param>
        /// <param name="longitude">经度（度）</param>
        /// <param name="dateTime">本地日期时间</param>
        /// <param name="timezone">时区偏移（小时）</param>
        /// <returns>太阳位置信息</returns>
        public static SunPosition CalculateSunPosition(double latitude, double longitude, DateTime dateTime, float timezone = 8f)
        {
            // 1. 计算一年中的第几天
            int dayOfYear = dateTime.DayOfYear;

            // 2. 计算太阳赤纬角（简化公式）
            // 赤纬角范围：-23.45° 到 +23.45°
            double declination = 23.45 * Math.Sin(DegToRad(360.0 / 365 * (dayOfYear - 81)));

            // 3. 计算时角
            // 太阳正午时角为0，上午为负，下午为正
            // 每小时15度
            double hours = dateTime.Hour + dateTime.Minute / 60.0 + dateTime.Second / 3600.0;

            // 真太阳时修正（简化）
            // 考虑经度与时区中心经度的差异
            double timezoneMeridian = timezone * 15; // 时区中心经度
            double longitudeCorrection = (longitude - timezoneMeridian) / 15.0; // 经度修正（小时）

            // 时差修正（简化，约±16分钟）
            double equationOfTime = 9.87 * Math.Sin(2 * DegToRad(360.0 / 365 * (dayOfYear - 81)))
                                   - 7.53 * Math.Cos(DegToRad(360.0 / 365 * (dayOfYear - 81)))
                                   - 1.5 * Math.Sin(DegToRad(360.0 / 365 * (dayOfYear - 81)));
            double equationCorrection = equationOfTime / 60.0; // 转换为小时

            // 真太阳时
            double solarTime = hours + longitudeCorrection + equationCorrection;

            // 时角（正午为0，上午负，下午正）
            double hourAngle = (solarTime - 12) * 15;

            // 4. 计算太阳高度角
            double latRad = DegToRad(latitude);
            double declRad = DegToRad(declination);
            double haRad = DegToRad(hourAngle);

            double sinAltitude = Math.Sin(latRad) * Math.Sin(declRad)
                               + Math.Cos(latRad) * Math.Cos(declRad) * Math.Cos(haRad);

            sinAltitude = Math.Clamp(sinAltitude, -1, 1);
            double altitude = RadToDeg(Math.Asin(sinAltitude));

            // 5. 计算太阳方位角（使用atan2确保连续性）
            double azimuth = 0;

            if (altitude > -0.83)
            {
                // 使用atan2计算方位角，确保连续变化
                // 正北=0°，正东=90°，正南=180°，正西=270°
                double sinAlt = Math.Sin(DegToRad(altitude));
                double cosAlt = Math.Cos(DegToRad(altitude));

                double y = Math.Sin(haRad) * Math.Cos(declRad);
                double x = Math.Cos(haRad) * Math.Sin(declRad) * Math.Cos(latRad) - Math.Sin(declRad) * Math.Sin(latRad);

                // 归一化并计算
                double len = Math.Sqrt(x * x + y * y);
                if (len > 0.001)
                {
                    // 使用atan2得到连续的方位角
                    azimuth = Math.Atan2(y, x) * 180.0 / Math.PI;
                    // 转换到气象学方位角（正北=0°，顺时针增加）
                    azimuth = 180.0 - azimuth;
                    // 归一化到0-360
                    while (azimuth < 0) azimuth += 360;
                    while (azimuth >= 360) azimuth -= 360;
                }
                else
                {
                    azimuth = hourAngle > 0 ? 180 : 0;
                }
            }
            else
            {
                azimuth = hourAngle > 0 ? 180 : 0;
            }

            // 6. 计算天顶角
            double zenith = 90 - altitude;

            return new SunPosition
            {
                altitude = (float)altitude,
                azimuth = (float)azimuth,
                zenith = (float)zenith,
                declination = (float)declination,
                hourAngle = (float)hourAngle,
                isValid = altitude > -0.83
            };
        }

        private static double DegToRad(double degrees) => degrees * Math.PI / 180.0;
        private static double RadToDeg(double radians) => radians * 180.0 / Math.PI;
    }

    /// <summary>
    /// 太阳位置信息
    /// </summary>
    [Serializable]
    public struct SunPosition
    {
        /// <summary>太阳高度角（度）- 0为地平线，90为天顶</summary>
        public float altitude;

        /// <summary>太阳方位角（度）- 正北为0，顺时针增加，正南为180°</summary>
        public float azimuth;

        /// <summary>太阳天顶角（度）- 90减去高度角</summary>
        public float zenith;

        /// <summary>太阳赤纬（度）</summary>
        public float declination;

        /// <summary>时角（度）</summary>
        public float hourAngle;

        /// <summary>太阳是否在地平线以上</summary>
        public bool isValid;

        /// <summary>
        /// 获取Unity世界坐标系中的太阳方向向量
        /// </summary>
        public Vector3 GetDirection()
        {
            // 太阳方向向量（从地面指向太阳）
            float altRad = altitude * Mathf.Deg2Rad;
            float aziRad = azimuth * Mathf.Deg2Rad;

            // Unity坐标系：Y轴向上，Z轴为正北
            // 方位角定义：北=0°，东=90°，南=180°，西=270°
            float x = Mathf.Cos(altRad) * Mathf.Sin(aziRad);
            float y = Mathf.Sin(altRad);
            float z = Mathf.Cos(altRad) * Mathf.Cos(aziRad);

            return new Vector3(x, y, z).normalized;
        }
    }
}
