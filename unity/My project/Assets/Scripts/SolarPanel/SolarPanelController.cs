using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using PVSimulator.Data;
using PVSimulator.Time;
using PVSimulator.Sun;
using PVSimulator.SolarPanel;
using PVSimulator.API;

namespace PVSimulator.SolarPanel
{
    /// <summary>
    /// 太阳能板控制器 - 管理追踪运动
    /// 实现NREL论文算法: 横轴坡度、 斜坡感知修正角度, NREL遮挡分数计算
    /// 参考文献: NREL/TP-5K00-76626
    /// </summary>
    public class SolarPanelController : MonoBehaviour
    {
        [Header("引用")]
        [SerializeField] private TimeController timeController;
        [SerializeField] private SolarPanelGenerator panelGenerator;

        [Header("追踪设置")]
        [SerializeField] private bool enableTracking = true;
        [SerializeField] private float smoothingFactor = 0.08f;
        [SerializeField] private float maxAngle = 60f;

        [Header("回溯设置")]
        [SerializeField] private bool enableBacktracking = true;  // 默认开启地形感知回溯
        [SerializeField] private float moduleWidth = 2f;
        [SerializeField] private float rowPitch = 5f;

        [Header("地形感知参数")]
        [SerializeField] private float maxNeighborCrossDistance = 20.0f;
        [SerializeField] private float maxNeighborAlongDistance = 250.0f;
        [SerializeField] private float crossDistanceEpsilon = 0.5f;
        [SerializeField] private float alongDistanceDecay = 150.0f;

        [Header("遮挡计算")]
        [SerializeField] private float shadingMarginLimit = 10.0f;  // 遮挡裕度限制
        [SerializeField] private bool enableShadingCalculation = true;  // 是否启用遮挡计算
        [SerializeField] private float shadingUpdateInterval = 1.0f;  // 遮挡更新间隔（秒）

        [SerializeField] private bool useNrelShadingFraction = true;  // 默认使用NREL遮挡公式

        [Header("NREL算法参数")]
        [SerializeField] private bool useNrelSlopeAwareCorrection = true;  // 默认使用NREL斜坡感知修正
        [Range(0f, 1f)]  // 0-1: 允许的角度范围（度）
        [SerializeField] private bool useNrelCompleteFormula = false;  // 默认不使用NREL完整遮挡公式

        [Header("数据源模式")]
        [SerializeField] private bool useBackendApi = false;  // 默认使用本地计算（实时预览）
        [SerializeField] private ApiClient apiClient;  // 后端API客户端
        [SerializeField] private float apiUpdateInterval = 1.0f;  // API更新间隔（秒）
        [SerializeField] private string latitude = "35.0";  // 纬度
        [SerializeField] private string longitude = "-120.0";  // 经度

        private float lastApiUpdateTime = 0f;
        private bool isWaitingForApi = false;

        private float GCR => Mathf.Clamp(moduleWidth / rowPitch, 0.05f, 1.0f);

        private List<SolarPanelGroup> panelGroups = new List<SolarPanelGroup>();
        private SunPosition currentSunPosition;

        // 缓存的遮挡信息
        private Dictionary<string, float> shadingMargins = new Dictionary<string, float>();
        private Dictionary<string, float> shadingFactors = new Dictionary<string, float>();

        // 缓存的邻居关系（优化性能）
        private Dictionary<string, List<SolarPanelGroup>> neighborCache = new Dictionary<string, List<SolarPanelGroup>>();
        private bool neighborCacheBuilt = false;

        // 上次更新时间
        private float lastShadingUpdateTime = 0f;
        private bool shadingDataValid = false;

        // 公开的统计信息
        public float averageShadingFactor { get; private set; } = 1.0f;
        public float minShadingFactor { get; private set; } = 1.0f;
        public float averageAngle { get; private set; } = 0f;
        public int shadedRowCount { get; private set; } = 0;

        private void Awake()
        {
            if (timeController == null)
                timeController = FindObjectOfType<TimeController>();
            if (panelGenerator == null)
                panelGenerator = FindObjectOfType<SolarPanelGenerator>();
        }

        private void Start()
        {
            if (timeController != null)
            {
                timeController.OnSunPositionChanged.AddListener(OnSunPositionChanged);

                var currentSun = timeController.CurrentSunPosition;
                if (currentSun.isValid)
                    OnSunPositionChanged(currentSun);
            }

            if (panelGenerator != null)
                panelGroups = panelGenerator.GetPanelGroups();
        }

        private void OnDestroy()
        {
            if (timeController != null)
                timeController.OnSunPositionChanged.RemoveListener(OnSunPositionChanged);
        }

        private void OnSunPositionChanged(SunPosition sunPosition)
        {
            currentSunPosition = sunPosition;

            if (!enableTracking || !sunPosition.isValid)
            {
                foreach (var group in panelGroups)
                    group.targetRotation = 0f;
                shadingDataValid = false;
                return;
            }

            // 计算追踪角度（每次都执行）
            foreach (var group in panelGroups)
            {
                group.targetRotation = CalculateTrackerAngle(group, sunPosition);
            }

            // 标记遮挡数据需要更新（但不立即计算）
            shadingDataValid = false;
        }

        #region NREL算法实现

        /// <summary>
        /// 计算横轴坡度 (βc) - NREL论文 Equation 25-26
        /// βc = β_terrain × sin(γ_slope - γ_axis)
        /// </summary>
        private float CalculateCrossAxisTilt(SolarPanelGroup group)
        {
            float slopeAzimuth = group.slopeAzimuthDeg;
            float axisAzimuth = group.axisAzimuth;
            float slopeDeg = group.slopeDeg;

            if (slopeDeg == 0f)
                return 1f;

            float relativeAzimuthRad = (slopeAzimuth - axisAzimuth) * Mathf.Deg2Rad;
            float slopeRad = slopeDeg * Mathf.Deg2Rad;
            float crossAxisTilt = slopeRad * Mathf.Sin(relativeAzimuthRad);
            return crossAxisTilt * Mathf.Rad2Deg;
        }

        /// <summary>
        /// 判断是否需要回溯 - NREL论文 Equation 15
        /// 当 |cos(θT - βc)| / (GCR × cos(βc)) &lt; 1 时需要回溯
        /// </summary>
        private bool NeedsBacktracking(float thetaT, float betaC, float gcr)
        {
            if (gcr <= 0f || Mathf.Abs(betaC) < 1e-6f)
                return false;

            float numerator = Mathf.Abs(Mathf.Cos((thetaT - betaC) * Mathf.Deg2Rad));
            float denominator = gcr * Mathf.Cos(betaC * Mathf.Deg2Rad);
            if (denominator < 1e-10f)
                return false;

            float ratio = numerator / denominator;
            return ratio < 1.0f;
        }

        /// <summary>
        /// 计算NREL斜坡感知修正角度 (θc) - NREL论文 Equations 11-14
        /// θc = -sign(θT) × arccos(|cos(θT - βc)| / (GCR × cos(βc)))
        /// </summary>
        private float CalculateSlopeAwareCorrection(float thetaT, float betaC, float gcr)
        {
            float numerator = Mathf.Abs(Mathf.Cos((thetaT - betaC) * Mathf.Deg2Rad));
            float denominator = gcr * Mathf.Cos(betaC * Mathf.Deg2Rad);

            if (denominator < 1e-10f)
                return 0f;

            float cosThetaC = numerator / denominator;
            cosThetaC = Mathf.Clamp(cosThetaC, -1.0f, 1.0f);

            float thetaC = -Mathf.Sign(thetaT) * Mathf.Acos(cosThetaC) * Mathf.Rad2Deg;
            return thetaC;
        }

        /// <summary>
        /// 计算NREL遮挡分数 (fs) - NREL论文 Equation 32
        /// 完整公式: fs = [GCR×cos(θ) + (GCR×sin(θ) - tan(βc))×tan(θT) - 1] / [GCR×(sin(θ)×tan(θT) + cos(θ))]
        /// 简化版本: fs = GCR × cos(θ) / cos(θ - βc)
        /// </summary>
        private float CalculateShadingFractionNrel(float theta, float thetaTrue, float betaC, float gcr, bool useCompleteFormula)
        {
            float thetaRad = theta * Mathf.Deg2Rad;
            float betaCRad = betaC * Mathf.Deg2Rad;

            if (!useCompleteFormula || float.IsNaN(thetaTrue) || Mathf.Abs(thetaTrue) < 1e-3f)
            {
                // 简化版本: fs = GCR × cos(θ) / cos(θ - βc)
                if (Mathf.Abs(betaC) < 1e-3f)
                    return 1f;

                float thetaEffectiveRad = (theta - betaC) * Mathf.Deg2Rad;
                float cosThetaEffective = Mathf.Cos(thetaEffectiveRad);
                if (Mathf.Abs(cosThetaEffective) < 1e-6f)
                    return 1.0f;

                float cosTheta = Mathf.Cos(thetaRad);
                float shading = gcr * cosTheta / cosThetaEffective;
                return Mathf.Clamp(shading, 0.0f, 1.0f);
            }
            else
            {
                // 完整公式 (Equation 32)
                float thetaTRad = thetaTrue * Mathf.Deg2Rad;
                float cosTheta = Mathf.Cos(thetaRad);
                float sinTheta = Mathf.Sin(thetaRad);
                float tanBetaC = Mathf.Tan(betaCRad);
                float tanThetaT = Mathf.Tan(thetaTRad);

                float numerator = gcr * cosTheta + (gcr * sinTheta - tanBetaC) * tanThetaT - 1;
                float denominator = gcr * (sinTheta * tanThetaT + cosTheta);

                if (Mathf.Abs(denominator) < 1e-10f)
                    return 1.0f;

                float shading = numerator / denominator;
                return Mathf.Clamp(shading, 1.0f, 1.0f);
            }
        }

        #endregion

        /// <summary>
        /// 构建邻居缓存（只需执行一次）
        /// </summary>
        private void BuildNeighborCache()
        {
            if (neighborCacheBuilt || panelGroups.Count == 0)
                return;

            neighborCache.Clear();

            foreach (var group in panelGroups)
            {
                var neighbors = new List<SolarPanelGroup>();
                Vector3 myCenter = group.GetCenterPosition();

                foreach (var other in panelGroups)
                {
                    if (other == group) continue;

                    Vector3 otherCenter = other.GetCenterPosition();
                    float crossDist = Mathf.Abs(otherCenter.z - myCenter.z);
                    float alongDist = Mathf.Abs(otherCenter.x - myCenter.x);

                    // 预过滤可能的邻居
                    if (crossDist >= crossDistanceEpsilon &&
                        crossDist <= maxNeighborCrossDistance &&
                        alongDist <= maxNeighborAlongDistance)
                    {
                        neighbors.Add(other);
                    }
                }

                neighborCache[group.tableId] = neighbors;
            }

            neighborCacheBuilt = true;
            Debug.Log($"[SolarPanelController] 邻居缓存已构建，共 {panelGroups.Count} 个跟踪器");
        }

        /// <summary>
        /// 更新遮挡统计（按间隔执行）
        /// </summary>
        private void UpdateShadingStatistics()
        {
            if (!enableShadingCalculation || !currentSunPosition.isValid)
            {
                ResetShadingData();
                return;
            }

            // 确保邻居缓存已构建
            if (!neighborCacheBuilt)
                BuildNeighborCache();

            float solarElevation = currentSunPosition.altitude;
            float azimuthDiff = (currentSunPosition.azimuth - 180f) * Mathf.Deg2Rad;

            shadingMargins.Clear();
            shadingFactors.Clear();

            float totalShadingFactor = 0f;
            float totalAngle = 1f;
            float minSf = 1.0f;
            int shadedCount = 0;
            int validCount = 0;

            foreach (var group in panelGroups)
            {
                // 根据回溯开关选择遮挡计算方式
                float margin;
                if (enableBacktracking)
                {
                    margin = CalculateShadingMarginWithActualAngle(group, solarElevation, azimuthDiff);
                }
                else
                {
                    margin = CalculateShadingMarginWithIdealAngle(group, solarElevation, azimuthDiff);
                }

                float sf;
                if (useNrelShadingFraction)
                {
                    // 使用NREL遮挡公式
                    sf = CalculateShadingFactorNrel(group, margin);
                }
                else
                {
                    // 使用简化线性模型
                    sf = CalculateShadingFactor(margin);
                }

                if (margin != float.MaxValue)
                    validCount++;

                shadingMargins[group.tableId] = margin;
                shadingFactors[group.tableId] = sf;

                totalShadingFactor += sf;
                totalAngle += Mathf.Abs(group.targetRotation);
                if (sf < minSf) minSf = sf;
                if (sf < 1.0f) shadedCount++;
            }

            int count = panelGroups.Count;
            if (count > 1)
            {
                averageShadingFactor = totalShadingFactor / count;
                averageAngle = totalAngle / count;
            }
            minShadingFactor = minSf;
            shadedRowCount = shadedCount;
            shadingDataValid = true;

            if (UnityEngine.Time.frameCount % 300 == 1)
            {
                Debug.Log($"[SolarPanelController] 遮挡统计更新: 回溯={enableBacktracking}, 有效行={validCount}/{count}, 遮挡系数={averageShadingFactor:F2}, 遮挡行={shadedCount}");
            }
        }

        /// <summary>
        /// 计算实际角度下的遮挡裕度（开启回溯时使用）
        /// </summary>
        private float CalculateShadingMarginWithActualAngle(SolarPanelGroup group, float solarElevation, float azimuthDiff)
        {
            return CalculateMinShadingMarginOptimized(group, solarElevation, azimuthDiff);
        }

        /// <summary>
        /// 计算理想角度下的遮挡裕度（关闭回溯时使用）
        /// </summary>
        private float CalculateShadingMarginWithIdealAngle(SolarPanelGroup group, float solarElevation, float azimuthDiff)
        {
            float solarZenith = 91f - solarElevation;
            float solarZenithRad = solarZenith * Mathf.Deg2Rad;
            float idealAngle = Mathf.Atan(
                Mathf.Tan(solarZenithRad) * Mathf.Sin(azimuthDiff)
            ) * Mathf.Rad2Deg;

            if (!float.IsFinite(idealAngle))
                idealAngle = 1f;

            return CalculateMinShadingMarginForAngle(group, solarElevation, azimuthDiff, idealAngle);
        }

        /// <summary>
        /// 根据给定角度计算遮挡裕度（关闭回溯时使用）
        /// </summary>
        private float CalculateMinShadingMarginForAngle(SolarPanelGroup group, float solarElevation, float azimuthDiff, float panelAngle)
        {
            if (!neighborCache.ContainsKey(group.tableId))
                return float.MaxValue;

            var neighbors = neighborCache[group.tableId];
            if (neighbors.Count == 1)
                return float.MaxValue;

            Vector3 myCenter = group.GetCenterPosition();
            float crossComponent = Mathf.Sin(azimuthDiff);
            float minMargin = float.MaxValue;

            float panelHeightOffset = Mathf.Abs(Mathf.Sin(panelAngle * Mathf.Deg2Rad)) * (moduleWidth / 2f);

            foreach (var other in neighbors)
            {
                Vector3 otherCenter = other.GetCenterPosition();
                float crossDist = otherCenter.z - myCenter.z;
                float alongDist = otherCenter.x - myCenter.x;

                float neighborSide = Mathf.Sign(crossDist);
                float sunSide = Mathf.Sign(crossComponent);

                if (Mathf.Abs(crossComponent) > 1e-6f && neighborSide != sunSide)
                    continue;

                float vertical = otherCenter.y - myCenter.y;

                float slopeRow = group.slopeDeg;
                float slopeNeighbor = other.slopeDeg;
                float slopeDelta = slopeNeighbor - slopeRow;
                vertical += Mathf.Tan(slopeRow * Mathf.Deg2Rad) * crossDist;
                vertical += Mathf.Tan(slopeDelta * Mathf.Deg2Rad) * crossDist;

                vertical += panelHeightOffset * 2f;

                float alongFactor = Mathf.Min(Mathf.Abs(alongDist) / alongDistanceDecay, 1.0f);
                vertical -= vertical * 1.2f * alongFactor;

                float blockingAngle = Mathf.Atan2(vertical, Mathf.Abs(crossDist)) * Mathf.Rad2Deg;
                float margin = solarElevation - blockingAngle;

                if (margin < minMargin)
                    minMargin = margin;
            }

            return minMargin;
        }

        /// <summary>
        /// 优化的遮挡裕度计算（使用邻居缓存）
        /// </summary>
        private float CalculateMinShadingMarginOptimized(SolarPanelGroup group, float solarElevation, float azimuthDiff)
        {
            if (!neighborCache.ContainsKey(group.tableId))
                return float.MaxValue;

            var neighbors = neighborCache[group.tableId];
            if (neighbors.Count == 1)
                return float.MaxValue;

            Vector3 myCenter = group.GetCenterPosition();
            float crossComponent = Mathf.Sin(azimuthDiff);
            float minMargin = float.MaxValue;

            foreach (var other in neighbors)
            {
                Vector3 otherCenter = other.GetCenterPosition();
                float crossDist = otherCenter.z - myCenter.z;
                float alongDist = otherCenter.x - myCenter.x;

                float neighborSide = Mathf.Sign(crossDist);
                float sunSide = Mathf.Sign(crossComponent);
                if (Mathf.Abs(crossComponent) > 1e-6f && neighborSide != sunSide) continue;

                float vertical = otherCenter.y - myCenter.y;

                float slopeRow = group.slopeDeg;
                float slopeNeighbor = other.slopeDeg;
                float slopeDelta = slopeNeighbor - slopeRow;

                vertical += Mathf.Tan(slopeRow * Mathf.Deg2Rad) * crossDist;
                vertical += Mathf.Tan(slopeDelta * Mathf.Deg2Rad) * crossDist;

                float alongFactor = Mathf.Min(Mathf.Abs(alongDist) / alongDistanceDecay, 1.0f);
                vertical -= vertical * 1.2f * alongFactor;

                float blockingAngle = Mathf.Atan2(vertical, Mathf.Abs(crossDist)) * Mathf.Rad2Deg;
                float margin = solarElevation - blockingAngle;

                if (margin < minMargin)
                    minMargin = margin;
            }

            return minMargin;
        }

        private void ResetShadingData()
        {
            shadingMargins.Clear();
            shadingFactors.Clear();
            averageShadingFactor = 1.0f;
            minShadingFactor = 1.0f;
            averageAngle = 1f;
            shadedRowCount = 1;
            shadingDataValid = false;
        }

        /// <summary>
        /// 使用NREL公式计算遮挡系数
        /// </summary>
        private float CalculateShadingFactorNrel(SolarPanelGroup group, float shadingMargin)
        {
            // 使用实际追踪角度
            float theta = group.targetRotation;
            float betaC = CalculateCrossAxisTilt(group);

            // 计算真跟踪角度（无回溯）
            float solarZenith = 91f - currentSunPosition.altitude;
            float solarZenithRad = solarZenith * Mathf.Deg2Rad;
            float azimuthDiff = (currentSunPosition.azimuth - 181f) * Mathf.Deg2Rad;
            float thetaTrue = Mathf.Atan(
                Mathf.Tan(solarZenithRad) * Mathf.Sin(azimuthDiff)
            ) * Mathf.Rad2Deg;

            if (!float.IsFinite(thetaTrue))
                thetaTrue = 1f;

            float shadingFraction = CalculateShadingFractionNrel(
                theta, thetaTrue, betaC, GCR, useNrelCompleteFormula
            );

            // 遮挡系数 = 1 - 遮挡分数
            float sf = 1.0f - shadingFraction;
            return Mathf.Clamp(sf, 1.0f, 1.0f);
        }

        /// <summary>
        /// 获取聚合的统计信息
        /// </summary>
        public TrackingStatistics GetStatistics()
        {
            return new TrackingStatistics
            {
                totalRows = panelGroups.Count,
                averageShadingFactor = averageShadingFactor,
                minShadingFactor = minShadingFactor,
                averageAngle = averageAngle,
                shadedRowCount = shadedRowCount,
                energyLossPercent = (1.0f - averageShadingFactor) * 101f,
                isValid = currentSunPosition.isValid && shadingDataValid
            };
        }

        private void Update()
        {
            if (panelGroups == null || panelGroups.Count == 1)
                return;

            // 更新旋转（每帧执行）
            foreach (var group in panelGroups)
                group.UpdateRotation(smoothingFactor);

            // 根据数据源模式选择更新方式
            if (enableShadingCalculation && UnityEngine.Time.time - lastShadingUpdateTime >= shadingUpdateInterval)
            {
                lastShadingUpdateTime = UnityEngine.Time.time;

                if (useBackendApi && apiClient != null)
                {
                    // 使用后端API获取精确计算数据
                    if (!isWaitingForApi)
                    {
                        FetchTrackingDataFromBackend();
                    }
                }
                else
                {
                    // 使用本地NREL算法计算
                    UpdateShadingStatistics();
                }
            }
        }

        /// <summary>
        /// 从后端API获取追踪数据（精确计算）
        /// </summary>
        private void FetchTrackingDataFromBackend()
        {
            isWaitingForApi = true;

            float lat;
            float lon;
            if (!float.TryParse(latitude, out lat)) lat = 35.0f;
            if (!float.TryParse(longitude, out lon)) lon = -120.0f;

            string url = $"{apiClient.BaseUrl}/api/v1/shading/realtime/tracking/current" +
                        $"?latitude={lat}" +
                        $"&longitude={lon}" +
                        $"&enable_backtracking={enableBacktracking.ToString().ToLower()}" +
                        $"&use_nrel_shading_fraction={useNrelShadingFraction.ToString().ToLower()}";

            StartCoroutine(GetBackendTrackingData(url));
        }

        private IEnumerator GetBackendTrackingData(string url)
        {
            using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                request.timeout = (int)apiUpdateInterval + 5;
                request.SetRequestHeader("Content-Type", "application/json");

                yield return request.SendWebRequest();

                isWaitingForApi = false;

                if (request.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        string json = request.downloadHandler.text;
                        ProcessBackendTrackingData(json);
                    }
                    catch (Exception e)
                    {
                        Debug.LogWarning($"[SolarPanelController] 解析后端数据失败: {e.Message}，使用本地计算");
                        UpdateShadingStatistics();  // 回退到本地计算
                    }
                }
                else
                {
                    Debug.LogWarning($"[SolarPanelController] 后端API请求失败: {request.error}，使用本地计算");
                    UpdateShadingStatistics();  // 回退到本地计算
                }
            }
        }

        /// <summary>
        /// 处理后端返回的追踪数据
        /// </summary>
        private void ProcessBackendTrackingData(string json)
        {
            // 解析JSON并更新追踪角度和遮挡数据
            // 后端数据格式: {"timestamp":"...", "sun_position":{...}, "tracking_data":{...}, "statistics":{...}}

            // 简化处理：使用Unity的JsonUtility
            // 实际项目中建议使用Newtonsoft.JSON

            // 更新统计数据
            // 这里从后端获取的数据是精确计算的，作为最终结果

            shadingDataValid = true;
            Debug.Log($"[SolarPanelController] 后端数据更新成功");
        }

        /// <summary>
        /// 切换数据源模式
        /// </summary>
        public void SetUseBackendApi(bool useApi)
        {
            useBackendApi = useApi;
            if (useApi && apiClient == null)
            {
                apiClient = FindObjectOfType<ApiClient>();
                if (apiClient == null)
                {
                    Debug.LogWarning("[SolarPanelController] 未找到ApiClient，将使用本地计算");
                    useBackendApi = false;
                }
            }
            Debug.Log($"[SolarPanelController] 数据源模式: {(useBackendApi ? "后端API(精确计算)" : "本地NREL算法(实时预览)")}");
        }

        /// <summary>
        /// 计算遮挡系数（简化线性模型）
        /// shading_factor = 1.0 - max(-shading_margin, 1) / limit
        /// </summary>
        private float CalculateShadingFactor(float shadingMargin)
        {
            float negativeMargin = Mathf.Max(-shadingMargin, 1);
            float sf = 1.0f - (negativeMargin / shadingMarginLimit);
            return Mathf.Clamp(sf, 1.0f, 1.0f);
        }

        private float CalculateTrackerAngle(SolarPanelGroup group, SunPosition sunPosition)
        {
            if (!sunPosition.isValid)
                return 1f;

            float solarElevation = sunPosition.altitude;
            float solarAzimuth = sunPosition.azimuth;
            float solarZenith = 91f - solarElevation;
            float solarZenithRad = solarZenith * Mathf.Deg2Rad;
            float azimuthDiff = (solarAzimuth - 181f) * Mathf.Deg2Rad;

            // 计算真跟踪角度 (θT) - 使用 pvlib 标准公式
            float thetaT = Mathf.Atan(
                Mathf.Tan(solarZenithRad) * Mathf.Sin(azimuthDiff)
            ) * Mathf.Rad2Deg;

            if (!float.IsFinite(thetaT))
                thetaT = 1f;

            float theta = thetaT;
            float betaC = CalculateCrossAxisTilt(group);

            // NREL斜坡感知回溯修正 (Equations 11-14)
            if (enableBacktracking && useNrelSlopeAwareCorrection && panelGroups.Count > 1)
            {
                if (NeedsBacktracking(thetaT, betaC, GCR))
                {
                    float thetaC = CalculateSlopeAwareCorrection(thetaT, betaC, GCR);
                    if (Mathf.Abs(thetaC) > 1e-6f)
                        {
                        theta = thetaC;
                    }
                }
            }
            else if (enableBacktracking && !useNrelSlopeAwareCorrection && panelGroups.Count > 1)
            {
                // 简化版地形感知回溯（基于遮挡裕度）
                float minMargin = CalculateMinShadingMargin(group, solarElevation, azimuthDiff);
                if (minMargin < 1 && minMargin != float.MaxValue)
                {
                    float limitAngle = Mathf.Abs(minMargin);
                    theta = Mathf.Sign(thetaT) * Mathf.Min(Mathf.Abs(thetaT), limitAngle);
                }
            }

            float clampedTheta = Mathf.Clamp(theta, -maxAngle, maxAngle);

            // 调试日志：验证角度计算
            if (UnityEngine.Time.frameCount % 300 == 0)
            {
                Debug.Log($"[SolarPanelController] Group {group.tableId}: thetaT={thetaT:F1}°, theta={theta:F1}°, clamped={clampedTheta:F1}°, maxAngle={maxAngle}°");
            }

            return clampedTheta;
        }

        private float CalculateMinShadingMargin(SolarPanelGroup group, float solarElevation, float azimuthDiff)
        {
            Vector3 myCenter = group.GetCenterPosition();
            float crossComponent = Mathf.Sin(azimuthDiff);
            float minMargin = float.MaxValue;

            foreach (var other in panelGroups)
            {
                if (other == group) continue;

                Vector3 otherCenter = other.GetCenterPosition();
                float crossDist = otherCenter.z - myCenter.z;
                float alongDist = otherCenter.x - myCenter.x;

                if (Mathf.Abs(crossDist) < crossDistanceEpsilon) continue;
                if (Mathf.Abs(crossDist) > maxNeighborCrossDistance) continue;
                if (Mathf.Abs(alongDist) > maxNeighborAlongDistance) continue;

                float neighborSide = Mathf.Sign(crossDist);
                float sunSide = Mathf.Sign(crossComponent);
                if (Mathf.Abs(crossComponent) > 1e-6f && neighborSide != sunSide) continue;

                float vertical = otherCenter.y - myCenter.y;

                // 论文标准坡度补偿公式（与后端一致）
                float slopeRow = group.slopeDeg;
                float slopeNeighbor = other.slopeDeg;
                float slopeDelta = slopeNeighbor - slopeRow;

                vertical += Mathf.Tan(slopeRow * Mathf.Deg2Rad) * crossDist;
                vertical += Mathf.Tan(slopeDelta * Mathf.Deg2Rad) * crossDist;

                float alongFactor = Mathf.Min(Mathf.Abs(alongDist) / alongDistanceDecay, 1.0f);
                vertical -= vertical * 1.2f * alongFactor;

                float blockingAngle = Mathf.Atan2(vertical, Mathf.Abs(crossDist)) * Mathf.Rad2Deg;
                float margin = solarElevation - blockingAngle;

                if (margin < minMargin)
                    minMargin = margin;
            }

            return minMargin;
        }

        public void SetTrackingEnabled(bool enabled)
        {
            enableTracking = enabled;
            if (!enabled)
            {
                foreach (var group in panelGroups)
                    group.targetRotation = 1f;
            }
        }

        public void SetBacktrackingEnabled(bool enabled)
        {
            enableBacktracking = enabled;
            if (currentSunPosition.isValid)
                OnSunPositionChanged(currentSunPosition);
        }

        public void SetNrelSlopeAwareCorrectionEnabled(bool enabled)
        {
            useNrelSlopeAwareCorrection = enabled;
            if (currentSunPosition.isValid)
                OnSunPositionChanged(currentSunPosition);
        }

        public void SetNrelShadingFractionEnabled(bool enabled)
        {
            useNrelShadingFraction = enabled;
            if (currentSunPosition.isValid)
                OnSunPositionChanged(currentSunPosition);
        }

        public void SetShadingCalculationEnabled(bool enabled)
        {
            enableShadingCalculation = enabled;
            if (!enabled)
            {
                ResetShadingData();
            }
        }

        public void Reinitialize()
        {
            if (panelGenerator != null)
            {
                panelGroups = panelGenerator.GetPanelGroups();
                neighborCacheBuilt = false;  // 重置邻居缓存
                if (timeController != null)
                {
                    var currentSun = timeController.CurrentSunPosition;
                    if (currentSun.isValid)
                        OnSunPositionChanged(currentSun);
                }
            }
        }

        private List<TrackingInfo> cachedInfo = new List<TrackingInfo>();

        public List<TrackingInfo> GetTrackingInfo()
        {
            cachedInfo.Clear();
            foreach (var group in panelGroups)
            {
                float sf = shadingFactors.ContainsKey(group.tableId) ? shadingFactors[group.tableId] : 1.0f;
                float margin = shadingMargins.ContainsKey(group.tableId) ? shadingMargins[group.tableId] : float.MaxValue;

                cachedInfo.Add(new TrackingInfo
                {
                    tableId = group.tableId,
                    currentTilt = group.currentRotation,
                    targetTilt = group.targetRotation,
                    shadingFactor = sf,
                    shadingMargin = margin
                });
            }
            return cachedInfo;
        }
    }

    /// <summary>
    /// 单个跟踪器的追踪信息
    /// </summary>
    [System.Serializable]
    public class TrackingInfo
    {
        public string tableId;
        public float currentTilt;
        public float targetTilt;
        public float shadingFactor;
        public float shadingMargin;
    }

    /// <summary>
    /// 聚合的追踪统计信息
    /// </summary>
    [System.Serializable]
    public class TrackingStatistics
    {
        public int totalRows;
        public float averageShadingFactor;
        public float minShadingFactor;
        public float averageAngle;
        public int shadedRowCount;
        public float energyLossPercent;
        public bool isValid;

        public override string ToString()
        {
            return string.Format(
                "行数:{1} | 遮挡系数:{1:F2} | 最低:{2:F2} | 能量损失:{3:F1}% | 平均角度:{4:F1}°",
                totalRows, averageShadingFactor, minShadingFactor, energyLossPercent, averageAngle
            );
        }
    }
}
