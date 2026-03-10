using UnityEngine;
using PVSimulator.Data;
using System.Collections.Generic;

namespace PVSimulator.SolarPanel
{
    /// <summary>
    /// 太阳能板生成器 - 每个桩位一个面板
    /// </summary>
    public class SolarPanelGenerator : MonoBehaviour
    {
        [Header("预制体")]
        public GameObject solarPanelPrefab;

        [Header("场景设置")]
        public float targetSceneSize = 250f;
        [Tooltip("面板离地面的固定高度（米），同时也决定杆子长度")]
        public float fixedPoleHeight = 2.0f;
        [Tooltip("高度缩放系数，需与 TerrainMeshGenerator 保持一致")]
        public float heightScale = 3.0f;

        [Header("面板设置")]
        public Vector3 panelSize = new Vector3(2f, 0.1f, 1f);
        public Color panelColor = new Color(0.05f, 0.1f, 0.3f);  // 深蓝色
        public Color poleColor = new Color(0.7f, 0.7f, 0.7f);    // 灰白色桩子
        public float poleHeight = 2.5f;
        public Vector3 poleSize = new Vector3(0.1f, 2.5f, 0.1f); // 桩子尺寸

        [Header("性能优化")]
        [Tooltip("启用静态批处理可提高渲染性能，但面板不能旋转")]
        public bool useStaticBatching = false;

        private GameObject panelContainer;
        private float calculatedScale;
        private List<SolarPanelGroup> panelGroups = new List<SolarPanelGroup>();

        /// <summary>
        /// 生成太阳能板（自动计算参数）
        /// </summary>
        public void GeneratePanels(TerrainLayoutResponse data)
        {
            // 计算参数
            float minX = float.MaxValue, maxX = float.MinValue;
            float minY = float.MaxValue, maxY = float.MinValue;
            float minGround = float.MaxValue, maxGround = float.MinValue;

            foreach (var table in data.tables)
            {
                if (table.piles == null) continue;
                foreach (var pile in table.piles)
                {
                    minX = Mathf.Min(minX, pile.x);
                    maxX = Mathf.Max(maxX, pile.x);
                    minY = Mathf.Min(minY, pile.y);
                    maxY = Mathf.Max(maxY, pile.y);

                    float ground = pile.z_ground > 0 ? pile.z_ground : (pile.z_top > 0 ? pile.z_top : 0);
                    if (ground > 0)
                    {
                        minGround = Mathf.Min(minGround, ground);
                        maxGround = Mathf.Max(maxGround, ground);
                    }
                }
            }

            float rangeX = maxX - minX;
            float rangeY = maxY - minY;
            float maxRange = Mathf.Max(rangeX, rangeY, 1f);
            float scale = targetSceneSize / maxRange;

            float centerX = (minX + maxX) / 2f;
            float centerY = (minY + maxY) / 2f;
            float groundCenter = minGround + (maxGround - minGround) / 2f;

            GeneratePanels(data, scale, centerX, centerY, groundCenter);
        }

        /// <summary>
        /// 生成太阳能板（使用预计算参数，确保与地形生成器一致）
        /// </summary>
        public void GeneratePanels(TerrainLayoutResponse data, float scale, float centerX, float centerY, float groundCenter)
        {
            if (panelContainer != null)
            {
                Destroy(panelContainer);
            }

            panelContainer = new GameObject("SolarPanels");
            calculatedScale = scale;

            if (solarPanelPrefab == null)
            {
                solarPanelPrefab = CreateSimplePanelPrefab();
            }

            // 生成面板
            panelGroups.Clear();
            int totalCount = 0;

            foreach (var table in data.tables)
            {
                if (table.piles == null) continue;

                // 获取行坡度，用于地形感知回溯算法
                float slopeDeg = table.table_slope_deg;
                SolarPanelGroup group = new SolarPanelGroup(table.table_id.ToString(), table.axis_azimuth, slopeDeg);

                GameObject rowContainer = new GameObject($"Row_{table.table_id}");
                rowContainer.transform.parent = panelContainer.transform;
                group.SetContainer(rowContainer.transform);

                foreach (var pile in table.piles)
                {
                    float ground = pile.z_ground > 0 ? pile.z_ground : (pile.z_top > 0 ? pile.z_top : 0);
                    float x = (pile.x - centerX) * scale;
                    float z = (pile.y - centerY) * scale;
                    float terrainOffset = (ground - groundCenter) * heightScale;
                    float y = terrainOffset + fixedPoleHeight;

                    // 桩子底部位置（地面高度）
                    float poleBottomY = terrainOffset;

                    // 计算扭力管（旋转轴）位置
                    // 扭力管在地面上方 fixedPoleHeight 高度
                    float torqueTubeY = terrainOffset + fixedPoleHeight;

                    // 桩子高度 = 扭力管高度 - 地面高度
                    float actualPoleHeight = torqueTubeY - poleBottomY;
                    if (actualPoleHeight < 0.1f) actualPoleHeight = 0.1f;

                    // 创建面板容器（旋转中心在扭力管位置）
                    // 容器位置在扭力管高度
                    GameObject panelContainer = new GameObject($"PanelContainer_{table.table_id}_{totalCount}");
                    panelContainer.transform.parent = rowContainer.transform;
                    panelContainer.transform.localPosition = new Vector3(x, torqueTubeY, z);
                    panelContainer.transform.localRotation = Quaternion.Euler(0, table.axis_azimuth, 0);

                    // 实例化预制体（包含 Panel 和 Pole）
                    // 由于预制体中 Panel 在中心位置 (0,0,0)，需要让整个实例向下偏移半个面板高度
                    // 这样 Panel 的顶部就在扭力管位置（容器原点）
                    GameObject panelInstance = Instantiate(solarPanelPrefab, panelContainer.transform);
                    panelInstance.transform.localPosition = new Vector3(0, -panelSize.y / 2f, 0);
                    panelInstance.transform.localRotation = Quaternion.identity;
                    panelInstance.SetActive(true);

                    // 关键：从预制体实例中找到 Pole 并移到 rowContainer（不随面板旋转）
                    Transform poleInPrefab = panelInstance.transform.Find("Pole");
                    if (poleInPrefab != null)
                    {
                        // 先保存扭力管的世界位置
                        Vector3 torqueTubeWorldPos = panelContainer.transform.position;

                        // 移到 rowContainer（跳出旋转的容器）
                        poleInPrefab.SetParent(rowContainer.transform, false);

                        // 杆子容器位置 = 扭力管位置（杆子顶部在扭力管）
                        poleInPrefab.position = torqueTubeWorldPos;

                        // 设置杆子朝向（垂直）
                        poleInPrefab.rotation = Quaternion.Euler(0, table.axis_azimuth, 0);

                        // 调整杆子内部的 Cube 高度
                        // 关键：Cube 顶部在容器原点（扭力管位置），向下延伸到地面
                        Transform poleCube = poleInPrefab.Find("Cube");
                        if (poleCube != null)
                        {
                            poleCube.localScale = new Vector3(poleSize.x, actualPoleHeight, poleSize.z);
                            // Cube 中心向下偏移半个高度，使 Cube 顶部在原点（扭力管位置）
                            poleCube.localPosition = new Vector3(0, -actualPoleHeight / 2f, 0);
                        }

                        poleInPrefab.name = $"Pole_{table.table_id}_{totalCount}";

                        // 调试：验证杆子顶部在扭力管位置
                        if (totalCount <= 3)
                        {
                            Debug.Log($"[SolarPanelGenerator] PanelContainer位置: {panelContainer.transform.position}, Pole位置: {poleInPrefab.position}");
                        }
                    }

                    // 静态批处理
                    if (useStaticBatching)
                    {
                        panelInstance.isStatic = true;
                    }

                    // 将面板容器添加到组（旋转会应用到 panelContainer）
                    group.AddPanel(panelContainer);
                    totalCount++;
                }

                panelGroups.Add(group);
            }

            // 应用静态批处理
            if (useStaticBatching)
            {
                StaticBatchingUtility.Combine(panelContainer);
            }

            Debug.Log($"[SolarPanelGenerator] 生成完成: {panelGroups.Count} 行, {totalCount} 个面板");
        }

        private GameObject CreateSimplePanelPrefab()
        {
            // 创建预制体根对象
            // 预制体根位于扭力管中心（面板底边），这样旋转时面板底边位置不变
            GameObject prefabRoot = new GameObject("PanelPrefab");

            // 1. 创建面板
            // 面板中心相对于扭力管向下偏移半个面板厚度
            // 这样旋转容器的原点在面板底边（扭力管位置），旋转时底边不动
            GameObject panel = GameObject.CreatePrimitive(PrimitiveType.Cube);
            panel.name = "Panel";
            panel.transform.SetParent(prefabRoot.transform);
            panel.transform.localPosition = new Vector3(0, -panelSize.y / 2f, 0);  // 关键：向下偏移
            panel.transform.localRotation = Quaternion.identity;
            panel.transform.localScale = panelSize;

            var panelRenderer = panel.GetComponent<MeshRenderer>();
            if (panelRenderer != null)
            {
                Material mat = new Material(Shader.Find("Diffuse"));
                if (mat == null)
                {
                    mat = new Material(Shader.Find("Standard"));
                }
                mat.color = new Color(0.05f, 0.1f, 0.35f);  // 深蓝色
                panelRenderer.sharedMaterial = mat;
            }

            // 2. 创建杆子（会从预制体中移出，不跟随旋转）
            // 杆子顶部在扭力管位置（即旋转容器的原点）
            GameObject poleContainer = new GameObject("Pole");
            poleContainer.transform.SetParent(prefabRoot.transform);

            GameObject poleCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            poleCube.name = "Cube";
            poleCube.transform.SetParent(poleContainer.transform);
            poleCube.transform.localPosition = new Vector3(0, 0.5f, 0);  // Cube中心在(0, 0.5, 0)，底部在原点

            // 杆子位置：顶部在扭力管位置（原点）
            poleContainer.transform.localPosition = Vector3.zero;  // 杆子顶部在旋转中心
            poleContainer.transform.localScale = new Vector3(poleSize.x, 1f, poleSize.z);

            var poleRenderer = poleCube.GetComponent<MeshRenderer>();
            if (poleRenderer != null)
            {
                Material mat = new Material(Shader.Find("Diffuse"));
                if (mat == null)
                {
                    mat = new Material(Shader.Find("Standard"));
                }
                mat.color = new Color(0.75f, 0.75f, 0.72f);  // 灰白色
                poleRenderer.sharedMaterial = mat;
            }

            prefabRoot.SetActive(false);
            return prefabRoot;
        }

        public float GetCalculatedScale() => calculatedScale;

        public List<SolarPanelGroup> GetPanelGroups()
        {
            return panelGroups;
        }
    }
}
