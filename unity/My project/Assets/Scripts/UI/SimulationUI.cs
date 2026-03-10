using UnityEngine;
using UnityEngine.UI;
using PVSimulator.Time;
using PVSimulator.Sun;
using PVSimulator.SolarPanel;
using PVSimulator.Terrain;
using PVSimulator.Export;

namespace PVSimulator.UI
{
    /// <summary>
    /// 模拟控制UI - 时间控制和信息显示
    /// </summary>
    public class SimulationUI : MonoBehaviour
    {
        [Header("控制器引用")]
        [SerializeField] private TimeController timeController;
        [SerializeField] private SunVisualizer sunVisualizer;
        [SerializeField] private SolarPanelController panelController;

        [Header("时间显示")]
        [SerializeField] private Text dateText;
        [SerializeField] private Text timeText;
        [SerializeField] private Text sunPositionText;

        [Header("播放控制")]
        [SerializeField] private Button playPauseButton;
        [SerializeField] private Text playPauseButtonText;
        [SerializeField] private Button stepForwardButton;
        [SerializeField] private Button stepBackwardButton;
        [SerializeField] private Button goToSunriseButton;
        [SerializeField] private Button goToNoonButton;
        [SerializeField] private Button goToSunsetButton;

        [Header("速度控制")]
        [SerializeField] private Slider speedSlider;
        [SerializeField] private Text speedText;
        [SerializeField] private float[] speedPresets = { 1f, 10f, 60f, 300f, 600f, 1800f };
        [SerializeField] private int currentSpeedIndex = 2;

        [Header("日期控制")]
        [SerializeField] private Dropdown monthDropdown;
        [SerializeField] private Dropdown dayDropdown;
        [SerializeField] private Dropdown hourDropdown;
        [SerializeField] private Button applyDateButton;

        [Header("追踪控制")]
        [SerializeField] private Toggle trackingToggle;
        [SerializeField] private Toggle backtrackingToggle;

        [Header("热力图控制")]
        [SerializeField] private ShadingHeatmap shadingHeatmap;
        [SerializeField] private Toggle heatmapToggle;

        [Header("地形控制")]
        [SerializeField] private TerrainMeshGenerator terrainGenerator;
        [SerializeField] private Toggle terrainToggle;
        [SerializeField] private Toggle terrainHeatmapToggle;

        [Header("数据导出")]
        [SerializeField] private DataExporter dataExporter;
        [SerializeField] private Button exportTrackingButton;
        [SerializeField] private Button exportShadingButton;
        [SerializeField] private Button exportReportButton;
        [SerializeField] private Button screenshotButton;
        [SerializeField] private Button exportSnapshotButton;

        [Header("信息面板")]
        [SerializeField] private Text trackingInfoText;
        [SerializeField] private GameObject infoPanel;

        [Header("遮挡统计显示")]
        [SerializeField] private GameObject shadingPanel;  // 遮挡面板（可开关）
        [SerializeField] private Toggle shadingPanelToggle;  // 面板开关
        [SerializeField] private Toggle shadingCalculationToggle;  // 计算开关
        [SerializeField] private Text shadingStatsText;
        [SerializeField] private Slider shadingFactorBar;
        [SerializeField] private Text shadingFactorText;
        [SerializeField] private Text energyLossText;
        [SerializeField] private Text averageAngleText;
        [SerializeField] private Image shadingIndicator;  // 颜色指示器

        private bool isPlaying = true;

        private void Awake()
        {
            FindReferences();
            InitializeUI();
        }

        private void FindReferences()
        {
            if (timeController == null)
                timeController = FindObjectOfType<TimeController>();
            if (sunVisualizer == null)
                sunVisualizer = FindObjectOfType<SunVisualizer>();
            if (panelController == null)
                panelController = FindObjectOfType<SolarPanelController>();
            if (shadingHeatmap == null)
                shadingHeatmap = FindObjectOfType<ShadingHeatmap>();
            if (terrainGenerator == null)
                terrainGenerator = FindObjectOfType<TerrainMeshGenerator>();
            if (dataExporter == null)
                dataExporter = FindObjectOfType<DataExporter>();
        }

        private void InitializeUI()
        {
            // 播放控制按钮
            if (playPauseButton != null)
                playPauseButton.onClick.AddListener(OnPlayPauseClicked);
            if (stepForwardButton != null)
                stepForwardButton.onClick.AddListener(OnStepForwardClicked);
            if (stepBackwardButton != null)
                stepBackwardButton.onClick.AddListener(OnStepBackwardClicked);
            if (goToSunriseButton != null)
                goToSunriseButton.onClick.AddListener(OnGoToSunriseClicked);
            if (goToNoonButton != null)
                goToNoonButton.onClick.AddListener(OnGoToNoonClicked);
            if (goToSunsetButton != null)
                goToSunsetButton.onClick.AddListener(OnGoToSunsetClicked);

            // 速度滑块
            if (speedSlider != null)
            {
                speedSlider.minValue = 0;
                speedSlider.maxValue = speedPresets.Length - 1;
                speedSlider.wholeNumbers = true;
                speedSlider.value = currentSpeedIndex;
                speedSlider.onValueChanged.AddListener(OnSpeedChanged);
            }

            // 日期下拉框
            InitializeDateDropdowns();
            if (applyDateButton != null)
                applyDateButton.onClick.AddListener(OnApplyDateClicked);

            // 追踪控制
            if (trackingToggle != null)
            {
                trackingToggle.isOn = true;
                trackingToggle.onValueChanged.AddListener(OnTrackingToggleChanged);
            }
            if (backtrackingToggle != null)
            {
                backtrackingToggle.isOn = true;
                backtrackingToggle.onValueChanged.AddListener(OnBacktrackingToggleChanged);
            }

            // 遮挡面板控制
            if (shadingPanelToggle != null)
            {
                shadingPanelToggle.isOn = true;  // 默认开启（显示遮挡系数）
                shadingPanelToggle.onValueChanged.AddListener(OnShadingPanelToggleChanged);
            }
            if (shadingCalculationToggle != null)
            {
                shadingCalculationToggle.isOn = true;  // 计算默认开启（热力图需要）
                shadingCalculationToggle.onValueChanged.AddListener(OnShadingCalculationToggleChanged);
            }
            // 遮挡面板默认显示（与 toggle 同步）
            if (shadingPanel != null)
                shadingPanel.SetActive(true);

            // 热力图控制
            if (heatmapToggle != null)
            {
                heatmapToggle.isOn = true;  // 默认开启
                heatmapToggle.onValueChanged.AddListener(OnHeatmapToggleChanged);
            }

            // 地形控制
            if (terrainToggle != null)
            {
                terrainToggle.isOn = true;  // 默认显示地形
                terrainToggle.onValueChanged.AddListener(OnTerrainToggleChanged);
            }
            if (terrainHeatmapToggle != null)
            {
                terrainHeatmapToggle.isOn = true;  // 默认开启高度热力图
                terrainHeatmapToggle.onValueChanged.AddListener(OnTerrainHeatmapToggleChanged);
            }

            // 数据导出按钮
            if (exportTrackingButton != null)
                exportTrackingButton.onClick.AddListener(OnExportTrackingClicked);
            if (exportShadingButton != null)
                exportShadingButton.onClick.AddListener(OnExportShadingClicked);
            if (exportReportButton != null)
                exportReportButton.onClick.AddListener(OnExportReportClicked);
            if (screenshotButton != null)
                screenshotButton.onClick.AddListener(OnScreenshotClicked);
            if (exportSnapshotButton != null)
                exportSnapshotButton.onClick.AddListener(OnExportSnapshotClicked);

            UpdatePlayPauseButton();
            UpdateSpeedDisplay();
        }

        private void InitializeDateDropdowns()
        {
            // 月份
            if (monthDropdown != null)
            {
                monthDropdown.ClearOptions();
                var months = new System.Collections.Generic.List<string>();
                for (int i = 1; i <= 12; i++)
                {
                    months.Add(i + "月");
                }
                monthDropdown.AddOptions(months);
                monthDropdown.value = 5; // 默认6月
            }

            // 日期
            if (dayDropdown != null)
            {
                dayDropdown.ClearOptions();
                var days = new System.Collections.Generic.List<string>();
                for (int i = 1; i <= 31; i++)
                {
                    days.Add(i + "日");
                }
                dayDropdown.AddOptions(days);
                dayDropdown.value = 20; // 默认21日
            }

            // 小时
            if (hourDropdown != null)
            {
                hourDropdown.ClearOptions();
                var hours = new System.Collections.Generic.List<string>();
                for (int i = 0; i < 24; i++)
                {
                    hours.Add(string.Format("{0:D2}:00", i));
                }
                hourDropdown.AddOptions(hours);
                hourDropdown.value = 6; // 默认6点
            }
        }

        private void OnEnable()
        {
            if (timeController != null)
            {
                timeController.OnTimeChanged.AddListener(OnTimeChanged);
                timeController.OnSunPositionChanged.AddListener(OnSunPositionChanged);
            }
        }

        private void OnDisable()
        {
            if (timeController != null)
            {
                timeController.OnTimeChanged.RemoveListener(OnTimeChanged);
                timeController.OnSunPositionChanged.RemoveListener(OnSunPositionChanged);
            }
        }

        private void Start()
        {
            UpdateAllDisplay();

            // 确保遮挡计算默认开启（用于热力图）
            if (panelController != null)
            {
                panelController.SetShadingCalculationEnabled(true);
                Debug.Log("[SimulationUI] 初始化：强制开启遮挡计算");
            }
        }

        private void OnTimeChanged(System.DateTime dateTime)
        {
            UpdateTimeDisplay(dateTime);
        }

        private void OnSunPositionChanged(SunPosition sunPos)
        {
            UpdateSunPositionDisplay(sunPos);
        }

        private void UpdateAllDisplay()
        {
            if (timeController != null)
            {
                UpdateTimeDisplay(timeController.CurrentDateTime);
                UpdateSunPositionDisplay(timeController.CurrentSunPosition);
            }
        }

        private void UpdateTimeDisplay(System.DateTime dateTime)
        {
            if (dateText != null)
                dateText.text = dateTime.ToString("yyyy年MM月dd日");
            if (timeText != null)
                timeText.text = dateTime.ToString("HH:mm");
        }

        private void UpdateSunPositionDisplay(SunPosition sunPos)
        {
            if (sunPositionText != null)
            {
                if (sunPos.isValid)
                {
                    sunPositionText.text = string.Format("太阳: 高度 {0:F1}° | 方位 {1:F1}°", sunPos.altitude, sunPos.azimuth);
                }
                else
                {
                    sunPositionText.text = "太阳在地平线以下";
                }
            }
        }

        #region 按钮事件

        private void OnPlayPauseClicked()
        {
            isPlaying = !isPlaying;

            if (timeController != null)
            {
                if (isPlaying)
                    timeController.Play();
                else
                    timeController.Pause();
            }

            UpdatePlayPauseButton();
        }

        private void OnStepForwardClicked()
        {
            if (timeController != null)
                timeController.StepForward();
        }

        private void OnStepBackwardClicked()
        {
            if (timeController != null)
                timeController.StepBackward();
        }

        private void OnGoToSunriseClicked()
        {
            if (timeController != null)
                timeController.GoToSunrise();
        }

        private void OnGoToNoonClicked()
        {
            if (timeController != null)
                timeController.GoToNoon();
        }

        private void OnGoToSunsetClicked()
        {
            if (timeController != null)
                timeController.GoToSunset();
        }

        private void OnSpeedChanged(float value)
        {
            currentSpeedIndex = Mathf.Clamp((int)value, 0, speedPresets.Length - 1);

            if (timeController != null)
            {
                timeController.SetTimeScale(speedPresets[currentSpeedIndex]);
            }

            UpdateSpeedDisplay();
        }

        private void OnApplyDateClicked()
        {
            if (timeController == null) return;

            int month = monthDropdown != null ? monthDropdown.value + 1 : 6;
            int day = dayDropdown != null ? dayDropdown.value + 1 : 21;
            int hour = hourDropdown != null ? hourDropdown.value : 6;

            try
            {
                int year = timeController.CurrentDateTime.Year;
                timeController.SetDate(year, month, day);
                timeController.SetHour(hour);
            }
            catch (System.Exception e)
            {
                Debug.LogWarning("[SimulationUI] 日期设置失败: " + e.Message);
            }
        }

        private void OnTrackingToggleChanged(bool enabled)
        {
            if (panelController != null)
                panelController.SetTrackingEnabled(enabled);
        }

        private void OnBacktrackingToggleChanged(bool enabled)
        {
            // 反向追踪开关
            if (panelController != null)
                panelController.SetBacktrackingEnabled(enabled);
            Debug.Log("[SimulationUI] 地形感知回溯: " + (enabled ? "启用" : "禁用"));
        }

        private void OnShadingPanelToggleChanged(bool enabled)
        {
            // 显示/隐藏遮挡面板
            if (shadingPanel != null)
                shadingPanel.SetActive(enabled);
        }

        private void OnShadingCalculationToggleChanged(bool enabled)
        {
            // 开启/关闭遮挡计算
            if (panelController != null)
                panelController.SetShadingCalculationEnabled(enabled);
            Debug.Log("[SimulationUI] 遮挡计算: " + (enabled ? "启用" : "禁用"));
        }

        private void OnHeatmapToggleChanged(bool enabled)
        {
            // 开启/关闭热力图
            if (shadingHeatmap != null)
                shadingHeatmap.SetHeatmapEnabled(enabled);
            Debug.Log("[SimulationUI] 热力图: " + (enabled ? "启用" : "禁用"));
        }

        private void OnTerrainToggleChanged(bool enabled)
        {
            // 显示/隐藏地形
            if (terrainGenerator != null)
                terrainGenerator.SetTerrainVisible(enabled);
            Debug.Log("[SimulationUI] 地形显示: " + (enabled ? "启用" : "禁用"));
        }

        private void OnTerrainHeatmapToggleChanged(bool enabled)
        {
            // 开启/关闭地形高度热力图
            if (terrainGenerator != null)
            {
                terrainGenerator.enableHeightHeatmap = enabled;
                terrainGenerator.UpdateHeatmapColors();
            }
            Debug.Log("[SimulationUI] 地形高度热力图: " + (enabled ? "启用" : "禁用"));
        }

        #region 数据导出

        private void OnExportTrackingClicked()
        {
            if (dataExporter != null)
                dataExporter.ExportTrackingAngles();
            else
                Debug.LogWarning("[SimulationUI] DataExporter 未设置");
        }

        private void OnExportShadingClicked()
        {
            if (dataExporter != null)
                dataExporter.ExportShadingFactors();
            else
                Debug.LogWarning("[SimulationUI] DataExporter 未设置");
        }

        private void OnExportReportClicked()
        {
            if (dataExporter != null)
                dataExporter.ExportFullReport();
            else
                Debug.LogWarning("[SimulationUI] DataExporter 未设置");
        }

        private void OnScreenshotClicked()
        {
            if (dataExporter != null)
                dataExporter.TakeQuickScreenshot();
            else
                Debug.LogWarning("[SimulationUI] DataExporter 未设置");
        }

        private void OnExportSnapshotClicked()
        {
            if (dataExporter != null)
                dataExporter.ExportSnapshot();
            else
                Debug.LogWarning("[SimulationUI] DataExporter 未设置");
        }

        #endregion

        #endregion

        private void UpdatePlayPauseButton()
        {
            if (playPauseButtonText != null)
            {
                playPauseButtonText.text = isPlaying ? "暂停" : "播放";
            }
        }

        private void UpdateSpeedDisplay()
        {
            if (speedText != null)
            {
                float speed = speedPresets[currentSpeedIndex];
                if (speed < 60)
                    speedText.text = speed.ToString("F0") + "x";
                else if (speed < 3600)
                    speedText.text = (speed / 60).ToString("F0") + "分钟/秒";
                else
                    speedText.text = (speed / 3600).ToString("F0") + "小时/秒";
            }
        }

        /// <summary>
        /// 切换信息面板显示
        /// </summary>
        public void ToggleInfoPanel()
        {
            if (infoPanel != null)
            {
                infoPanel.SetActive(!infoPanel.activeSelf);
            }
        }

        private void Update()
        {
            // 定期更新追踪信息（降低频率以提高性能）
            if (UnityEngine.Time.frameCount % 30 == 0)
            {
                UpdateTrackingInfo();
                UpdateShadingDisplay();
            }
        }

        private void UpdateTrackingInfo()
        {
            if (trackingInfoText == null || panelController == null)
                return;

            var info = panelController.GetTrackingInfo();
            if (info != null && info.Count > 0)
            {
                // 显示前5个跟踪器的信息（包含遮挡系数）
                System.Text.StringBuilder sb = new System.Text.StringBuilder();
                sb.AppendLine("跟踪器状态:");
                int count = Mathf.Min(5, info.Count);
                for (int i = 0; i < count; i++)
                {
                    string shadingStatus = info[i].shadingFactor >= 0.99f ? "OK" :
                                          info[i].shadingFactor >= 0.8f ? "轻" :
                                          info[i].shadingFactor >= 0.5f ? "中" : "重";
                    sb.AppendLine(string.Format("  {0}: {1:F1}° [{2}]",
                        info[i].tableId, info[i].currentTilt, shadingStatus));
                }
                if (info.Count > 5)
                {
                    sb.AppendLine("  ... 还有 " + (info.Count - 5) + " 个跟踪器");
                }
                trackingInfoText.text = sb.ToString();
            }
        }

        private void UpdateShadingDisplay()
        {
            if (panelController == null)
            {
                Debug.LogWarning("[SimulationUI] panelController 为空，无法更新遮挡显示");
                return;
            }

            var stats = panelController.GetStatistics();

            // 检查是否有有效数据（只要有行数就显示）
            bool hasData = stats.totalRows > 0;
            bool sunValid = stats.isValid;  // 太阳是否在地平线以上

            // 调试输出
            if (UnityEngine.Time.frameCount % 60 == 0)
            {
                Debug.Log($"[SimulationUI] 遮挡显示更新: hasData={hasData}, sunValid={sunValid}, totalRows={stats.totalRows}, sf={stats.averageShadingFactor:F2}, angle={stats.averageAngle:F1}");
            }

            // 更新遮挡统计文本
            if (shadingStatsText != null)
            {
                if (hasData)
                {
                    shadingStatsText.text = string.Format(
                        "总行数: {0} | 遮挡行: {1} ({2:F1}%)",
                        stats.totalRows, stats.shadedRowCount,
                        stats.totalRows > 0 ? (float)stats.shadedRowCount / stats.totalRows * 100 : 0
                    );
                }
                else
                {
                    shadingStatsText.text = "太阳在地平线以下";
                }
            }

            // 更新遮挡系数进度条
            if (shadingFactorBar != null)
            {
                if (hasData)
                {
                    shadingFactorBar.value = stats.averageShadingFactor;
                }
                else
                {
                    shadingFactorBar.value = 0;  // 太阳落山后进度条为空
                }
            }

            // 更新遮挡系数文本
            if (shadingFactorText != null)
            {
                if (hasData)
                {
                    shadingFactorText.text = string.Format("遮挡系数: {0:F2}", stats.averageShadingFactor);
                }
                else
                {
                    shadingFactorText.text = "遮挡系数: --";
                }
            }

            // 更新能量损失
            if (energyLossText != null)
            {
                if (hasData)
                {
                    energyLossText.text = string.Format("能量损失: {0:F1}%", stats.energyLossPercent);
                }
                else
                {
                    energyLossText.text = "能量损失: --";
                }
            }

            // 更新平均角度
            if (averageAngleText != null)
            {
                if (hasData)
                {
                    averageAngleText.text = string.Format("平均角度: {0:F1}°", stats.averageAngle);
                }
                else
                {
                    averageAngleText.text = "平均角度: --";
                }
            }

            // 更新颜色指示器
            if (shadingIndicator != null)
            {
                if (!hasData)
                {
                    // 太阳落山后显示灰色
                    shadingIndicator.color = new Color(0.5f, 0.5f, 0.5f, 1f);
                }
                else
                {
                    // 根据遮挡系数设置颜色
                    // 绿色(1.0) -> 黄色(0.7) -> 红色(0.4)
                    float sf = stats.averageShadingFactor;
                    Color color;
                    if (sf >= 0.9f)
                    {
                        color = Color.green;  // 无遮挡
                    }
                    else if (sf >= 0.7f)
                    {
                        // 绿到黄
                        float t = (sf - 0.7f) / 0.3f;
                        color = Color.Lerp(Color.yellow, Color.green, t);
                    }
                    else if (sf >= 0.4f)
                    {
                        // 黄到橙
                        float t = (sf - 0.4f) / 0.3f;
                        color = Color.Lerp(new Color(1f, 0.5f, 0f), Color.yellow, t);
                    }
                    else
                    {
                        // 橙到红
                        float t = sf / 0.4f;
                        color = Color.Lerp(Color.red, new Color(1f, 0.5f, 0f), t);
                    }
                    shadingIndicator.color = color;
                }
            }
        }
    }
}
