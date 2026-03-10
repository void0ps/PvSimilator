using System;
using UnityEngine;
using UnityEngine.Events;

namespace PVSimulator.Time
{
    /// <summary>
    /// 时间控制器 - 管理模拟时间流逝
    /// </summary>
    public class TimeController : MonoBehaviour
    {
        [Header("地理位置设置")]
        [SerializeField] private double latitude = 39.9042; // 北京纬度
        [SerializeField] private double longitude = 116.4074; // 北京经度
        [SerializeField] private float timezone = 8f; // UTC+8

        [Header("初始日期时间")]
        [SerializeField] private int startYear = 2024;
        [SerializeField] private int startMonth = 6;
        [SerializeField] private int startDay = 21; // 夏至
        [SerializeField] [Range(0, 23)] private int startHour = 6;
        [SerializeField] [Range(0, 59)] private int startMinute = 0;

        [Header("播放设置")]
        [SerializeField] private bool autoPlay = true;
        [SerializeField] [Range(0.1f, 3600f)] private float timeScale = 60f; // 1秒现实时间 = 多少秒模拟时间
        [SerializeField] [Range(1, 1440)] private int timeStepMinutes = 1; // 每步时间增量（分钟）

        [Header("日出日落时间范围")]
        [SerializeField] [Range(4, 8)] private int minHour = 5;
        [SerializeField] [Range(17, 22)] private int maxHour = 20;

        // 当前模拟时间
        private DateTime currentDateTime;
        private bool isPlaying;
        private float accumulatedTime;

        // 太阳位置缓存
        private Sun.SunPosition currentSunPosition;

        // 事件
        public UnityEvent<DateTime> OnTimeChanged;
        public UnityEvent<Sun.SunPosition> OnSunPositionChanged;
        public UnityEvent OnDayChanged;

        // 公开属性
        public DateTime CurrentDateTime => currentDateTime;
        public Sun.SunPosition CurrentSunPosition => currentSunPosition;
        public bool IsPlaying => isPlaying;
        public double Latitude => latitude;
        public double Longitude => longitude;
        public float TimeScale => timeScale;

        private void Awake()
        {
            InitializeTime();
        }

        private void Start()
        {
            if (autoPlay)
            {
                Play();
            }
        }

        private void InitializeTime()
        {
            try
            {
                currentDateTime = new DateTime(startYear, startMonth, startDay, startHour, startMinute, 0);
            }
            catch
            {
                currentDateTime = new DateTime(2024, 6, 21, 6, 0, 0);
            }
            UpdateSunPosition();
        }

        private void Update()
        {
            if (isPlaying)
            {
                accumulatedTime += UnityEngine.Time.deltaTime * timeScale;

                // 累积足够的时间则推进模拟时间
                int secondsToAdvance = (int)accumulatedTime;
                if (secondsToAdvance > 0)
                {
                    AdvanceTime(secondsToAdvance);
                    accumulatedTime -= secondsToAdvance;
                }
            }
        }

        /// <summary>
        /// 推进模拟时间
        /// </summary>
        private void AdvanceTime(int seconds)
        {
            DateTime previousDate = currentDateTime.Date;
            currentDateTime = currentDateTime.AddSeconds(seconds);

            // 检查是否跨天
            if (currentDateTime.Date != previousDate)
            {
                OnDayChanged?.Invoke();
            }

            UpdateSunPosition();
            OnTimeChanged?.Invoke(currentDateTime);
        }

        /// <summary>
        /// 更新太阳位置
        /// </summary>
        private void UpdateSunPosition()
        {
            currentSunPosition = Sun.SunPositionCalculator.CalculateSunPosition(
                latitude, longitude, currentDateTime, timezone);

            OnSunPositionChanged?.Invoke(currentSunPosition);
        }

        #region 公共控制方法

        /// <summary>
        /// 开始播放
        /// </summary>
        public void Play()
        {
            isPlaying = true;
        }

        /// <summary>
        /// 暂停播放
        /// </summary>
        public void Pause()
        {
            isPlaying = false;
        }

        /// <summary>
        /// 切换播放/暂停
        /// </summary>
        public void TogglePlay()
        {
            if (isPlaying) Pause();
            else Play();
        }

        /// <summary>
        /// 设置时间速度
        /// </summary>
        public void SetTimeScale(float scale)
        {
            timeScale = Mathf.Clamp(scale, 0.1f, 3600f);
        }

        /// <summary>
        /// 设置指定时间
        /// </summary>
        public void SetDateTime(DateTime dateTime)
        {
            currentDateTime = dateTime;
            accumulatedTime = 0;
            UpdateSunPosition();
            OnTimeChanged?.Invoke(currentDateTime);
        }

        /// <summary>
        /// 设置指定小时
        /// </summary>
        public void SetHour(int hour)
        {
            currentDateTime = new DateTime(
                currentDateTime.Year,
                currentDateTime.Month,
                currentDateTime.Day,
                hour,
                0, 0);
            accumulatedTime = 0;
            UpdateSunPosition();
            OnTimeChanged?.Invoke(currentDateTime);
        }

        /// <summary>
        /// 设置日期
        /// </summary>
        public void SetDate(int year, int month, int day)
        {
            currentDateTime = new DateTime(
                year, month, day,
                currentDateTime.Hour,
                currentDateTime.Minute,
                currentDateTime.Second);
            accumulatedTime = 0;
            UpdateSunPosition();
            OnTimeChanged?.Invoke(currentDateTime);
        }

        /// <summary>
        /// 设置地理位置
        /// </summary>
        public void SetLocation(double lat, double lon, float tz = 8f)
        {
            latitude = lat;
            longitude = lon;
            timezone = tz;
            UpdateSunPosition();
            OnSunPositionChanged?.Invoke(currentSunPosition);
        }

        /// <summary>
        /// 快进到下一个时间点
        /// </summary>
        public void StepForward()
        {
            AdvanceTime(timeStepMinutes * 60);
        }

        /// <summary>
        /// 后退到上一个时间点
        /// </summary>
        public void StepBackward()
        {
            currentDateTime = currentDateTime.AddMinutes(-timeStepMinutes);
            accumulatedTime = 0;
            UpdateSunPosition();
            OnTimeChanged?.Invoke(currentDateTime);
        }

        /// <summary>
        /// 跳转到日出时间
        /// </summary>
        public void GoToSunrise()
        {
            SetHour(minHour);
        }

        /// <summary>
        /// 跳转到正午
        /// </summary>
        public void GoToNoon()
        {
            SetHour(12);
        }

        /// <summary>
        /// 跳转到日落时间
        /// </summary>
        public void GoToSunset()
        {
            SetHour(maxHour);
        }

        /// <summary>
        /// 获取格式化的时间字符串
        /// </summary>
        public string GetFormattedTime()
        {
            return currentDateTime.ToString("yyyy-MM-dd HH:mm");
        }

        /// <summary>
        /// 获取太阳位置信息字符串
        /// </summary>
        public string GetSunPositionInfo()
        {
            return $"高度角: {currentSunPosition.altitude:F1}° | 方位角: {currentSunPosition.azimuth:F1}°";
        }

        #endregion
    }
}
