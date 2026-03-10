using UnityEngine;
using PVSimulator.Data;
using System.Collections.Generic;

namespace PVSimulator.Terrain
{
    /// <summary>
    /// 地形网格生成器 - 基于桩位高度数据生成地形 Mesh
    /// </summary>
    public class TerrainMeshGenerator : MonoBehaviour
    {
        [Header("网格设置")]
        [Tooltip("网格分辨率（每格多少米）")]
        public float cellSize = 2f;

        [Tooltip("高度缩放系数（夸张地形起伏）")]
        public float heightScale = 3.0f;

        [Tooltip("网格边缘扩展（米）")]
        public float edgePadding = 10f;

        [Header("材质设置")]
        [Tooltip("是否启用高度热力图")]
        public bool enableHeightHeatmap = true;

        [Tooltip("低海拔颜色")]
        public Color lowColor = new Color(0.2f, 0.4f, 0.8f);  // 蓝色

        [Tooltip("中低海拔颜色")]
        public Color midLowColor = new Color(0.2f, 0.7f, 0.3f);  // 绿色

        [Tooltip("中高海拔颜色")]
        public Color midHighColor = new Color(0.9f, 0.8f, 0.2f);  // 黄色

        [Tooltip("高海拔颜色")]
        public Color highColor = new Color(0.9f, 0.3f, 0.2f);  // 红色

        [Header("渲染设置")]
        [Tooltip("地形材质（可选，默认使用高度热力图）")]
        public Material terrainMaterial;

        [Tooltip("地形图层")]
        public int terrainLayer = 3;

        private GameObject terrainObject;
        private MeshFilter meshFilter;
        private MeshRenderer meshRenderer;
        private MeshCollider meshCollider;

        // 存储网格数据
        private float[,] heightGrid;
        private int gridWidth, gridHeight;
        private float sceneMinX, sceneMinZ, sceneMaxX, sceneMaxZ;

        /// <summary>
        /// 生成地形网格
        /// </summary>
        /// <param name="data">地形布局数据</param>
        /// <param name="scale">场景缩放系数</param>
        /// <param name="centerX">数据中心 X（原始坐标）</param>
        /// <param name="centerY">数据中心 Y（原始坐标）</param>
        /// <param name="groundCenter">地面高度中心</param>
        public void GenerateTerrain(TerrainLayoutResponse data, float scale, float centerX, float centerY, float groundCenter)
        {
            if (terrainObject != null)
            {
                Destroy(terrainObject);
            }

            // 第一步：收集所有桩位的原始坐标和高度
            List<PilePoint> pilePoints = CollectPilePoints(data);

            if (pilePoints.Count < 3)
            {
                Debug.LogWarning("[TerrainMeshGenerator] 桩位数据不足，无法生成地形");
                return;
            }

            // 第二步：计算原始数据边界
            float rawMinX = float.MaxValue, rawMaxX = float.MinValue;
            float rawMinY = float.MaxValue, rawMaxY = float.MinValue;
            float minGround = float.MaxValue, maxGround = float.MinValue;

            foreach (var pp in pilePoints)
            {
                rawMinX = Mathf.Min(rawMinX, pp.rawX);
                rawMaxX = Mathf.Max(rawMaxX, pp.rawX);
                rawMinY = Mathf.Min(rawMinY, pp.rawY);
                rawMaxY = Mathf.Max(rawMaxY, pp.rawY);
                minGround = Mathf.Min(minGround, pp.groundHeight);
                maxGround = Mathf.Max(maxGround, pp.groundHeight);
            }

            // 第三步：将桩位转换为场景坐标
            foreach (var pp in pilePoints)
            {
                pp.sceneX = (pp.rawX - centerX) * scale;
                pp.sceneZ = (pp.rawY - centerY) * scale;
                pp.sceneY = (pp.groundHeight - groundCenter) * heightScale;
            }

            // 第四步：计算场景边界
            sceneMinX = float.MaxValue;
            sceneMaxX = float.MinValue;
            sceneMinZ = float.MaxValue;
            sceneMaxZ = float.MinValue;

            foreach (var pp in pilePoints)
            {
                sceneMinX = Mathf.Min(sceneMinX, pp.sceneX);
                sceneMaxX = Mathf.Max(sceneMaxX, pp.sceneX);
                sceneMinZ = Mathf.Min(sceneMinZ, pp.sceneZ);
                sceneMaxZ = Mathf.Max(sceneMaxZ, pp.sceneZ);
            }

            // 添加边缘扩展
            sceneMinX -= edgePadding;
            sceneMaxX += edgePadding;
            sceneMinZ -= edgePadding;
            sceneMaxZ += edgePadding;

            // 第五步：生成高度网格
            GenerateHeightGrid(pilePoints);

            // 第六步：创建地形 Mesh
            CreateTerrainMesh(minGround, maxGround, groundCenter);

            Debug.Log($"[TerrainMeshGenerator] 地形生成完成: {gridWidth}x{gridHeight} 网格, 场景范围: X[{sceneMinX:F1}, {sceneMaxX:F1}] Z[{sceneMinZ:F1}, {sceneMaxZ:F1}]");
        }

        /// <summary>
        /// 桩位点数据（同时存储原始和场景坐标）
        /// </summary>
        private class PilePoint
        {
            public float rawX, rawY;        // 原始坐标
            public float groundHeight;       // 地面高度
            public float sceneX, sceneY, sceneZ;  // 场景坐标
        }

        /// <summary>
        /// 收集所有桩位点
        /// </summary>
        private List<PilePoint> CollectPilePoints(TerrainLayoutResponse data)
        {
            List<PilePoint> points = new List<PilePoint>();

            foreach (var table in data.tables)
            {
                if (table.piles == null) continue;

                foreach (var pile in table.piles)
                {
                    float ground = pile.z_ground > 0 ? pile.z_ground : (pile.z_top > 0 ? pile.z_top : 0);

                    points.Add(new PilePoint
                    {
                        rawX = pile.x,
                        rawY = pile.y,
                        groundHeight = ground
                    });
                }
            }

            return points;
        }

        /// <summary>
        /// 生成高度网格（使用反距离加权插值）
        /// </summary>
        private void GenerateHeightGrid(List<PilePoint> pilePoints)
        {
            // 计算网格尺寸
            float width = sceneMaxX - sceneMinX;
            float height = sceneMaxZ - sceneMinZ;

            gridWidth = Mathf.CeilToInt(width / cellSize) + 1;
            gridHeight = Mathf.CeilToInt(height / cellSize) + 1;

            // 限制网格大小，避免过大
            gridWidth = Mathf.Min(gridWidth, 200);
            gridHeight = Mathf.Min(gridHeight, 200);

            heightGrid = new float[gridWidth, gridHeight];

            // 初始化为0
            for (int x = 0; x < gridWidth; x++)
            {
                for (int z = 0; z < gridHeight; z++)
                {
                    heightGrid[x, z] = 0f;
                }
            }

            // 使用 IDW 插值填充每个网格点
            for (int x = 0; x < gridWidth; x++)
            {
                for (int z = 0; z < gridHeight; z++)
                {
                    // 计算当前网格点的场景坐标
                    float worldX = sceneMinX + x * cellSize;
                    float worldZ = sceneMinZ + z * cellSize;

                    // 使用 IDW 插值计算高度
                    heightGrid[x, z] = IDWInterpolate(worldX, worldZ, pilePoints);
                }
            }
        }

        /// <summary>
        /// 反距离加权插值算法
        /// </summary>
        private float IDWInterpolate(float x, float z, List<PilePoint> points, float power = 2f, int maxNeighbors = 12)
        {
            // 计算到所有点的距离
            List<(float distance, float height)> distances = new List<(float, float)>();

            foreach (var point in points)
            {
                float dist = Mathf.Sqrt((point.sceneX - x) * (point.sceneX - x) + (point.sceneZ - z) * (point.sceneZ - z));
                if (dist < 0.001f)
                {
                    return point.sceneY; // 正好在点上
                }
                distances.Add((dist, point.sceneY));
            }

            // 按距离排序，取最近的点
            distances.Sort((a, b) => a.distance.CompareTo(b.distance));
            int count = Mathf.Min(maxNeighbors, distances.Count);

            float weightSum = 0;
            float valueSum = 0;

            for (int i = 0; i < count; i++)
            {
                float w = 1f / Mathf.Pow(distances[i].distance, power);
                weightSum += w;
                valueSum += w * distances[i].height;
            }

            return weightSum > 0 ? valueSum / weightSum : 0;
        }

        /// <summary>
        /// 创建地形 Mesh
        /// </summary>
        private void CreateTerrainMesh(float minGround, float maxGround, float groundCenter)
        {
            // 创建地形对象
            terrainObject = new GameObject("Terrain");
            terrainObject.transform.parent = transform;
            terrainObject.layer = terrainLayer;

            // 添加组件
            meshFilter = terrainObject.AddComponent<MeshFilter>();
            meshRenderer = terrainObject.AddComponent<MeshRenderer>();
            meshCollider = terrainObject.AddComponent<MeshCollider>();

            // 生成 Mesh
            Mesh mesh = new Mesh();
            mesh.name = "TerrainMesh";

            // 生成顶点
            Vector3[] vertices = new Vector3[gridWidth * gridHeight];
            Vector2[] uv = new Vector2[gridWidth * gridHeight];

            float minHeight = float.MaxValue;
            float maxHeight = float.MinValue;

            for (int x = 0; x < gridWidth; x++)
            {
                for (int z = 0; z < gridHeight; z++)
                {
                    int index = x * gridHeight + z;
                    float height = heightGrid[x, z];

                    vertices[index] = new Vector3(
                        sceneMinX + x * cellSize,
                        height,
                        sceneMinZ + z * cellSize
                    );

                    uv[index] = new Vector2((float)x / gridWidth, (float)z / gridHeight);

                    minHeight = Mathf.Min(minHeight, height);
                    maxHeight = Mathf.Max(maxHeight, height);
                }
            }

            // 生成三角形
            int[] triangles = new int[(gridWidth - 1) * (gridHeight - 1) * 6];
            int triangleIndex = 0;

            for (int x = 0; x < gridWidth - 1; x++)
            {
                for (int z = 0; z < gridHeight - 1; z++)
                {
                    int topLeft = x * gridHeight + z;
                    int topRight = topLeft + 1;
                    int bottomLeft = (x + 1) * gridHeight + z;
                    int bottomRight = bottomLeft + 1;

                    // 第一个三角形
                    triangles[triangleIndex++] = topLeft;
                    triangles[triangleIndex++] = topRight;
                    triangles[triangleIndex++] = bottomLeft;

                    // 第二个三角形
                    triangles[triangleIndex++] = bottomLeft;
                    triangles[triangleIndex++] = topRight;
                    triangles[triangleIndex++] = bottomRight;
                }
            }

            mesh.vertices = vertices;
            mesh.uv = uv;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();

            meshFilter.mesh = mesh;
            meshCollider.sharedMesh = mesh;

            // 设置材质
            if (terrainMaterial == null)
            {
                terrainMaterial = CreateHeightHeatmapMaterial(minHeight, maxHeight);
            }
            meshRenderer.material = terrainMaterial;

            // 设置为地面层，用于射线检测
            terrainObject.tag = "Terrain";
        }

        /// <summary>
        /// 创建高度热力图材质
        /// </summary>
        private Material CreateHeightHeatmapMaterial(float minHeight, float maxHeight)
        {
            // 优先使用自定义热力图着色器
            Shader shader = Shader.Find("Custom/TerrainHeightHeatmap");

            if (shader == null)
            {
                // 回退到 URP SimpleLit
                shader = Shader.Find("Universal Render Pipeline/SimpleLit");
            }

            if (shader == null)
            {
                // 最后回退到 Diffuse
                shader = Shader.Find("Diffuse");
            }

            Material mat = new Material(shader);
            mat.name = "TerrainHeightHeatmap";

            // 如果使用自定义着色器，设置颜色参数
            if (mat.shader.name == "Custom/TerrainHeightHeatmap")
            {
                mat.SetColor("_LowColor", lowColor);
                mat.SetColor("_MidLowColor", midLowColor);
                mat.SetColor("_MidHighColor", midHighColor);
                mat.SetColor("_HighColor", highColor);
                mat.SetFloat("_MinHeight", minHeight);
                mat.SetFloat("_MaxHeight", maxHeight);
                mat.SetFloat("_UseVertexColors", 0f); // 使用高度计算颜色
            }
            else
            {
                // 使用默认着色器时，设置平均高度颜色
                float avgHeight = (minHeight + maxHeight) / 2f;
                Color baseColor = GetHeightColor(avgHeight, minHeight, maxHeight);
                mat.color = baseColor;
            }

            return mat;
        }

        /// <summary>
        /// 根据高度获取颜色
        /// </summary>
        private Color GetHeightColor(float height, float minHeight, float maxHeight)
        {
            if (maxHeight <= minHeight)
            {
                return midLowColor;
            }

            float t = (height - minHeight) / (maxHeight - minHeight);

            if (t < 0.25f)
            {
                return Color.Lerp(lowColor, midLowColor, t * 4f);
            }
            else if (t < 0.5f)
            {
                return Color.Lerp(midLowColor, midHighColor, (t - 0.25f) * 4f);
            }
            else if (t < 0.75f)
            {
                return Color.Lerp(midHighColor, highColor, (t - 0.5f) * 4f);
            }
            else
            {
                return Color.Lerp(highColor, highColor, (t - 0.75f) * 4f);
            }
        }

        /// <summary>
        /// 获取指定点的地形高度
        /// </summary>
        public float GetHeightAtPosition(Vector3 worldPosition)
        {
            if (heightGrid == null)
            {
                return 0;
            }

            // 转换为网格坐标
            int gridX = Mathf.RoundToInt((worldPosition.x - sceneMinX) / cellSize);
            int gridZ = Mathf.RoundToInt((worldPosition.z - sceneMinZ) / cellSize);

            gridX = Mathf.Clamp(gridX, 0, gridWidth - 1);
            gridZ = Mathf.Clamp(gridZ, 0, gridHeight - 1);

            return heightGrid[gridX, gridZ];
        }

        /// <summary>
        /// 获取地形边界
        /// </summary>
        public Bounds GetTerrainBounds()
        {
            if (terrainObject == null || meshFilter == null)
            {
                return new Bounds(Vector3.zero, Vector3.zero);
            }

            return meshFilter.mesh.bounds;
        }

        /// <summary>
        /// 切换地形显示
        /// </summary>
        public void SetTerrainVisible(bool visible)
        {
            if (terrainObject != null)
            {
                terrainObject.SetActive(visible);
            }
        }

        /// <summary>
        /// 更新热力图颜色（运行时调用）
        /// </summary>
        public void UpdateHeatmapColors()
        {
            if (meshFilter == null || meshRenderer == null)
            {
                return;
            }

            Mesh mesh = meshFilter.mesh;
            Vector3[] vertices = mesh.vertices;

            float minHeight = float.MaxValue;
            float maxHeight = float.MinValue;

            foreach (var v in vertices)
            {
                minHeight = Mathf.Min(minHeight, v.y);
                maxHeight = Mathf.Max(maxHeight, v.y);
            }

            Color[] colors = new Color[vertices.Length];
            for (int i = 0; i < vertices.Length; i++)
            {
                colors[i] = GetHeightColor(vertices[i].y, minHeight, maxHeight);
            }

            mesh.colors = colors;

            // 如果着色器支持顶点颜色，需要设置相应属性
            if (meshRenderer.material.HasProperty("_VertexColor"))
            {
                // 某些自定义着色器支持顶点颜色
            }
        }

        void OnDestroy()
        {
            if (terrainObject != null)
            {
                Destroy(terrainObject);
            }
        }
    }
}
