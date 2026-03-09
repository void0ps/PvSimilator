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

                    // 桩子底部和顶部位置
                    float poleBottomY = terrainOffset;
                    float poleTopY = y - panelSize.y / 2;
                    float actualPoleHeight = poleTopY - poleBottomY;
                    if (actualPoleHeight < 0.1f) actualPoleHeight = 0.1f;

                    // 创建面板容器（会被旋转）
                    GameObject panelContainer = new GameObject($"PanelContainer_{table.table_id}_{totalCount}");
                    panelContainer.transform.parent = rowContainer.transform;
                    panelContainer.transform.localPosition = new Vector3(x, y, z);
                    panelContainer.transform.localRotation = Quaternion.Euler(0, table.axis_azimuth, 0);

                    // 实例化预制体（包含 Panel 和 Pole）
                    GameObject panelInstance = Instantiate(solarPanelPrefab, panelContainer.transform);
                    panelInstance.transform.localPosition = Vector3.zero;
                    panelInstance.transform.localRotation = Quaternion.identity;
                    panelInstance.SetActive(true);

                    // 关键：从预制体实例中找到 Pole 并移到 rowContainer（不随面板旋转）
                    Transform poleInPrefab = panelInstance.transform.Find("Pole");
                    if (poleInPrefab != null)
                    {
                        // 保存 Pole 的本地信息
                        Vector3 poleLocalPos = poleInPrefab.localPosition;
                        Quaternion poleLocalRot = poleInPrefab.localRotation;
                        Vector3 poleLocalScale = poleInPrefab.localScale;

                        // 移到 rowContainer（跳出旋转的容器）
                        poleInPrefab.SetParent(rowContainer.transform, false);

                        // 计算杆子在场景中的实际位置
                        // 杆子的本地位置是相对于面板的，需要转换到世界坐标
                        Vector3 poleWorldPos = panelContainer.transform.TransformPoint(poleLocalPos);
                        poleInPrefab.position = poleWorldPos;

                        // 设置杆子朝向（与面板朝向一致，但不跟随面板倾斜）
                        poleInPrefab.rotation = Quaternion.Euler(0, table.axis_azimuth, 0);

                        // 调整杆子内部的 Cube 高度
                        Transform poleCube = poleInPrefab.Find("Cube");
                        if (poleCube != null)
                        {
                            poleCube.localScale = new Vector3(poleSize.x, actualPoleHeight, poleSize.z);
                            poleCube.localPosition = new Vector3(0, actualPoleHeight / 2f, 0);
                        }

                        poleInPrefab.name = $"Pole_{table.table_id}_{totalCount}";
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
            GameObject prefabRoot = new GameObject("PanelPrefab");

            // 1. 创建面板 (在原点)
            GameObject panel = GameObject.CreatePrimitive(PrimitiveType.Cube);
            panel.name = "Panel";
            panel.transform.SetParent(prefabRoot.transform);
            panel.transform.localPosition = Vector3.zero;
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
            GameObject poleContainer = new GameObject("Pole");
            poleContainer.transform.SetParent(prefabRoot.transform);

            GameObject poleCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            poleCube.name = "Cube";
            poleCube.transform.SetParent(poleContainer.transform);
            poleCube.transform.localPosition = new Vector3(0, 0.5f, 0);

            // 杆子位置：在面板正下方
            float poleY = -panelSize.y / 2f;
            poleContainer.transform.localPosition = new Vector3(0, poleY, 0);
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
