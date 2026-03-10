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

                    // 实例化预制体
                    GameObject panelInstance = Instantiate(solarPanelPrefab, panelContainer.transform);
                    panelInstance.transform.localRotation = Quaternion.identity;

                    // ★ 关键：查找面板网格的 Y 偏移，调整预制体位置使面板中心在旋转原点
                    // 预制体中 Solar_Panel1 在 Y=1.34（扭力管上方），需要向下偏移使其在旋转中心
                    Transform panelMeshTransform = panelInstance.transform.Find("Panel/Solar_Panel1");
                    float panelYOffset = 0f;
                    if (panelMeshTransform != null)
                    {
                        panelYOffset = panelMeshTransform.localPosition.y;  // 获取 Y 偏移 (1.34)
                    }

                    // 预制体向下偏移，使面板网格中心在容器原点（旋转中心）
                    panelInstance.transform.localPosition = new Vector3(0, -panelYOffset, 0);

                    panelInstance.SetActive(true);

                    // 关键：只移动 Pole1 (杆子网格)，保留 Assembly (扭力管) 在旋转容器内
                    // 这样面板围绕扭力管旋转，杆子保持垂直不旋转

                    // 查找 Pole1 的路径（新prefab结构）
                    Transform poleMesh = panelInstance.transform.Find("Structure/Pole/Pole1");
                    if (poleMesh == null)
                    {
                        // 兼容旧prefab结构：Pole/Cube
                        poleMesh = panelInstance.transform.Find("Pole/Cube");
                    }
                    if (poleMesh == null)
                    {
                        // 尝试在根级别找 Pole1
                        poleMesh = panelInstance.transform.Find("Pole1");
                    }
                    if (poleMesh == null)
                    {
                        // 尝试找 Structure/Pole 然后找其子对象 Pole1
                        Transform poleContainerTransform = panelInstance.transform.Find("Structure/Pole");
                        if (poleContainerTransform != null)
                        {
                            poleMesh = poleContainerTransform.Find("Pole1");
                            if (poleMesh == null)
                            {
                                // 查找第一个包含 Renderer 且名称含 Pole 的子对象
                                foreach (Transform child in poleContainerTransform)
                                {
                                    if (child.name.Contains("Pole") && child.GetComponent<Renderer>() != null)
                                    {
                                        poleMesh = child;
                                        break;
                                    }
                                }
                            }
                        }
                    }

                    if (poleMesh != null)
                    {
                        // 计算扭力管的实际世界位置
                        // 由于预制体向下偏移了 panelYOffset，扭力管位置也相应下移
                        Vector3 torqueTubeWorldPos = panelContainer.transform.position + Vector3.down * panelYOffset;

                        // 创建杆子容器（在 Row 下，不随面板旋转）
                        GameObject poleContainerObj = new GameObject($"Pole_{table.table_id}_{totalCount}");
                        poleContainerObj.transform.parent = rowContainer.transform;
                        poleContainerObj.transform.position = torqueTubeWorldPos;
                        poleContainerObj.transform.rotation = Quaternion.Euler(0, table.axis_azimuth, 0);

                        // 移动 Pole1 到杆子容器
                        poleMesh.SetParent(poleContainerObj.transform, false);

                        // 设置杆子网格的本地位置和缩放
                        // 杆子顶部在容器原点（扭力管位置），杆子向下延伸
                        poleMesh.localPosition = new Vector3(0, -actualPoleHeight / 2f, 0);
                        poleMesh.localRotation = Quaternion.identity;

                        // 调整杆子高度
                        Vector3 meshScale = poleMesh.localScale;
                        poleMesh.localScale = new Vector3(meshScale.x, actualPoleHeight, meshScale.z);

                        // 调试日志：验证杆子容器设置
                        if (totalCount < 3)
                        {
                            Debug.Log($"[SolarPanelGenerator] PoleContainer '{poleContainerObj.name}' parent: {poleContainerObj.transform.parent.name}, rotation: {poleContainerObj.transform.rotation.eulerAngles}");
                            Debug.Log($"[SolarPanelGenerator] PoleMesh '{poleMesh.name}' localRotation: {poleMesh.localRotation.eulerAngles}, worldRotation: {poleMesh.rotation.eulerAngles}");
                        }
                    }
                    else
                    {
                        Debug.LogWarning($"[SolarPanelGenerator] 未找到 Pole1 网格！面板将跟随旋转。");
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
