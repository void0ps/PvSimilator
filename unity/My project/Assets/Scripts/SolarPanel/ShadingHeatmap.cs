using System.Collections.Generic;
using UnityEngine;

namespace PVSimulator.SolarPanel
{
    /// <summary>
    /// 遮挡热力图可视化 - 根据遮挡系数着色太阳能板
    /// </summary>
    public class ShadingHeatmap : MonoBehaviour
    {
        // Shader属性ID缓存（避免字符串查找）
        private static readonly int BaseColorID = Shader.PropertyToID("_BaseColor");
        private static readonly int ColorID = Shader.PropertyToID("_Color");

        [ContextMenu("手动初始化")]
        private void ContextMenuInitialize()
        {
            Initialize();
        }

        [ContextMenu("切换热力图")]
        private void ContextMenuToggle()
        {
            ToggleHeatmap();
        }

        [ContextMenu("测试：全部变红")]
        private void ContextMenuTestRed()
        {
            if (allRenderers.Count == 0)
            {
                Debug.LogWarning("[ShadingHeatmap] 请先初始化");
                return;
            }
            if (propertyBlock == null) propertyBlock = new MaterialPropertyBlock();

            int count = 0;
            foreach (var renderer in allRenderers)
            {
                if (renderer != null)
                {
                    SetRendererColor(renderer, Color.red);
                    count++;
                }
            }

            // 输出第一个渲染器的材质信息用于调试
            if (allRenderers.Count > 0 && allRenderers[0] != null)
            {
                var mat = allRenderers[0].sharedMaterial;
                Debug.Log($"[ShadingHeatmap] 第一个渲染器材质: {mat?.name ?? "null"}, shader: {mat?.shader?.name ?? "null"}");
            }
        }

        [ContextMenu("测试：全部变绿")]
        private void ContextMenuTestGreen()
        {
            if (allRenderers.Count == 0)
            {
                Debug.LogWarning("[ShadingHeatmap] 请先初始化");
                return;
            }
            if (propertyBlock == null) propertyBlock = new MaterialPropertyBlock();

            foreach (var renderer in allRenderers)
            {
                if (renderer != null)
                {
                    SetRendererColor(renderer, Color.green);
                }
            }
        }

        [ContextMenu("重置为深蓝色")]
        private void ContextMenuReset()
        {
            ResetToNormalColor();
        }
        [Header("引用")]
        [SerializeField] private SolarPanelController panelController;
        [SerializeField] private SolarPanelGenerator panelGenerator;

        [Header("热力图设置")]
        [SerializeField] private bool enableHeatmap = true;
        [SerializeField] private float updateInterval = 0.5f;  // 更新间隔（秒）

        [Header("颜色设置")]
        [Tooltip("无遮挡颜色 (shading_factor >= 0.9)")]
        [SerializeField] private Color noShadingColor = new Color(0.2f, 0.8f, 0.2f);     // 绿色
        [Tooltip("轻微遮挡颜色 (shading_factor 0.7-0.9)")]
        [SerializeField] private Color lightShadingColor = new Color(1.0f, 0.9f, 0.2f);  // 黄色
        [Tooltip("中等遮挡颜色 (shading_factor 0.4-0.7)")]
        [SerializeField] private Color mediumShadingColor = new Color(1.0f, 0.5f, 0.0f); // 橙色
        [Tooltip("严重遮挡颜色 (shading_factor < 0.4)")]
        [SerializeField] private Color heavyShadingColor = new Color(0.9f, 0.1f, 0.1f);  // 红色

        [Header("普通面板颜色")]
        [SerializeField] private Color normalPanelColor = new Color(0.05f, 0.1f, 0.35f); // 深蓝色

        private float lastUpdateTime = 0f;
        private bool isInitialized = false;

        // MaterialPropertyBlock 用于高效修改颜色
        private MaterialPropertyBlock propertyBlock;

        // 调试信息（Inspector 可见）
        [SerializeField, Tooltip("只读：渲染器数量")]
        private int debugRendererCount = 0;
        [SerializeField, Tooltip("只读：组数量")]
        private int debugGroupCount = 0;

        // 缓存：tableId -> 该组所有面板的 Renderer
        private Dictionary<string, List<Renderer>> groupRenderers = new Dictionary<string, List<Renderer>>();
        // 缓存：所有渲染器（用于快速重置颜色）
        private List<Renderer> allRenderers = new List<Renderer>();

        private void Awake()
        {
            if (panelController == null)
                panelController = FindObjectOfType<SolarPanelController>();
            if (panelGenerator == null)
                panelGenerator = FindObjectOfType<SolarPanelGenerator>();
        }

        private void Start()
        {
            // 延迟初始化，等待面板生成完成
            Invoke(nameof(Initialize), 1f);
        }

        /// <summary>
        /// 初始化 - 构建渲染器缓存
        /// </summary>
        public void Initialize()
        {
            if (panelGenerator == null)
            {
                Debug.LogWarning("[ShadingHeatmap] SolarPanelGenerator 未找到");
                return;
            }

            groupRenderers.Clear();
            allRenderers.Clear();

            var groups = panelGenerator.GetPanelGroups();
            if (groups == null || groups.Count == 0)
            {
                Debug.LogWarning("[ShadingHeatmap] 没有找到面板组");
                return;
            }

            foreach (var group in groups)
            {
                var renderers = new List<Renderer>();
                foreach (var panel in group.panels)
                {
                    if (panel != null)
                    {
                        // panel是panelContainer，需要在其子对象中找prefab实例
                        // 然后在prefab实例中找面板主体的Renderer
                        Renderer renderer = null;

                        // 遍历panelContainer的直接子对象（prefab实例）
                        foreach (Transform prefabInstance in panel.transform)
                        {
                            // 方案1：新prefab结构 - Panel/Solar_Panel1/Mesh9
                            Transform panelBody = prefabInstance.Find("Panel/Solar_Panel1/Mesh9");
                            if (panelBody != null)
                            {
                                renderer = panelBody.GetComponent<Renderer>();
                                if (renderer != null) break;
                            }

                            // 方案2：尝试找名为"Mesh4"的对象（旧prefab的面板主体）
                            panelBody = prefabInstance.Find("Mesh4");
                            if (panelBody != null)
                            {
                                renderer = panelBody.GetComponent<Renderer>();
                                if (renderer != null) break;
                            }

                            // 方案3：查找名为"Panel"的对象（自定义简单prefab的面板主体）
                            panelBody = prefabInstance.Find("Panel");
                            if (panelBody != null)
                            {
                                renderer = panelBody.GetComponent<Renderer>();
                                if (renderer != null) break;
                            }

                            // 方案4：查找包含"Mesh"但不包含"Pole"/"Tube"的对象
                            foreach (Transform child in prefabInstance)
                            {
                                if (child.name.StartsWith("Mesh") &&
                                    !child.name.Contains("Pole") &&
                                    !child.name.Contains("Tube"))
                                {
                                    renderer = child.GetComponent<Renderer>();
                                    if (renderer != null) break;
                                }
                            }
                            if (renderer != null) break;
                        }

                        // 备选方案：如果上面都没找到，用原来的逻辑
                        if (renderer == null)
                        {
                            renderer = panel.GetComponent<Renderer>();
                            if (renderer == null)
                            {
                                renderer = panel.GetComponentInChildren<Renderer>();
                            }
                        }

                        if (renderer != null)
                        {
                            renderers.Add(renderer);
                            allRenderers.Add(renderer);
                        }
                    }
                }
                groupRenderers[group.tableId] = renderers;
            }

            isInitialized = true;
            debugRendererCount = allRenderers.Count;
            debugGroupCount = groupRenderers.Count;

            // 初始化 MaterialPropertyBlock
            propertyBlock = new MaterialPropertyBlock();

            Debug.Log($"[ShadingHeatmap] 初始化完成: {groupRenderers.Count} 组, {allRenderers.Count} 个渲染器");
        }

        /// <summary>
        /// 根据追踪信息更新热力图
        /// </summary>
        public void UpdateHeatmap(List<TrackingInfo> trackingInfo)
        {
            if (!enableHeatmap)
            {
                return;
            }
            if (!isInitialized)
            {
                return;
            }
            if (trackingInfo == null || trackingInfo.Count == 0)
            {
                return;
            }
            if (propertyBlock == null)
            {
                propertyBlock = new MaterialPropertyBlock();
            }

            int updatedCount = 0;
            int missedCount = 0;

            foreach (var info in trackingInfo)
            {
                Color color = GetColorForShadingFactor(info.shadingFactor);

                // 尝试匹配 tableId
                if (groupRenderers.TryGetValue(info.tableId, out var renderers))
                {
                    foreach (var renderer in renderers)
                    {
                        if (renderer != null)
                        {
                            SetRendererColor(renderer, color);
                            updatedCount++;
                        }
                    }
                }
                else
                {
                    missedCount++;
                }
            }
        }

        /// <summary>
        /// 根据遮挡系数获取颜色
        /// </summary>
        public Color GetColorForShadingFactor(float sf)
        {
            // sf: 1.0 = 无遮挡, 0.0 = 完全遮挡
            if (sf >= 0.9f)
            {
                return noShadingColor;
            }
            else if (sf >= 0.7f)
            {
                float t = (sf - 0.7f) / 0.3f;
                return Color.Lerp(lightShadingColor, noShadingColor, t);
            }
            else if (sf >= 0.4f)
            {
                float t = (sf - 0.4f) / 0.3f;
                return Color.Lerp(mediumShadingColor, lightShadingColor, t);
            }
            else
            {
                float t = Mathf.Clamp01(sf / 0.4f);
                return Color.Lerp(heavyShadingColor, mediumShadingColor, t);
            }
        }

        /// <summary>
        /// 开启/关闭热力图
        /// </summary>
        public void SetHeatmapEnabled(bool enabled)
        {
            enableHeatmap = enabled;

            if (!enabled)
            {
                ResetToNormalColor();
            }
        }

        /// <summary>
        /// 重置为普通颜色
        /// </summary>
        public void ResetToNormalColor()
        {
            if (propertyBlock == null) propertyBlock = new MaterialPropertyBlock();

            foreach (var renderer in allRenderers)
            {
                if (renderer != null)
                {
                    SetRendererColor(renderer, normalPanelColor);
                }
            }
        }

        /// <summary>
        /// 设置渲染器颜色（尝试多个shader属性）
        /// </summary>
        private void SetRendererColor(Renderer renderer, Color color)
        {
            if (renderer == null) return;

            renderer.GetPropertyBlock(propertyBlock);
            propertyBlock.SetColor(BaseColorID, color);
            propertyBlock.SetColor(ColorID, color);
            renderer.SetPropertyBlock(propertyBlock);
        }

        /// <summary>
        /// 切换热力图开关
        /// </summary>
        public void ToggleHeatmap()
        {
            SetHeatmapEnabled(!enableHeatmap);
        }

        private void Update()
        {
            if (!enableHeatmap || !isInitialized || panelController == null)
                return;

            // 按间隔更新
            if (UnityEngine.Time.time - lastUpdateTime >= updateInterval)
            {
                lastUpdateTime = UnityEngine.Time.time;
                var info = panelController.GetTrackingInfo();
                UpdateHeatmap(info);
            }
        }

        /// <summary>
        /// 手动触发初始化（供外部调用）
        /// </summary>
        public void ManualInitialize()
        {
            Initialize();
        }
    }
}
