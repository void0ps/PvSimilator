using UnityEngine;
using PVSimulator.API;
using PVSimulator.Data;
using PVSimulator.SolarPanel;
using PVSimulator.Time;
using PVSimulator.Sun;
using PVSimulator.Terrain;

namespace PVSimulator
{
    /// <summary>
    /// 场景管理器 - 协调所有组件的初始化和交互
    /// </summary>
    public class SceneManager : MonoBehaviour
    {
        [Header("核心组件")]
        [SerializeField] private CameraController cameraController;
        [SerializeField] private ApiClient apiClient;
        [SerializeField] private SolarPanelGenerator panelGenerator;
        [SerializeField] private SolarPanelController panelController;
        [SerializeField] private TimeController timeController;
        [SerializeField] private SunVisualizer sunVisualizer;
        [SerializeField] private TerrainMeshGenerator terrainGenerator;

        [Header("默认设置")]
        [SerializeField] private double defaultLatitude = 39.9042; // 北京
        [SerializeField] private double defaultLongitude = 116.4074;
        [SerializeField] private float defaultTimezone = 8f;
        [SerializeField] private float initialCameraDistance = 80f;

        private TerrainLayoutResponse terrainData;
        private bool isInitialized = false;

        void Start()
        {
            InitializeScene();
        }

        private void InitializeScene()
        {
            Debug.Log("=== 场景初始化开始 ===");

            // 1. 初始化组件引用
            InitializeComponents();

            // 2. 配置时间控制器
            ConfigureTimeController();

            // 3. 配置太阳可视化
            ConfigureSunVisualizer();

            // 4. 加载地形数据
            LoadTerrainData();
        }

        private void InitializeComponents()
        {
            // 初始化API客户端
            if (apiClient == null)
            {
                apiClient = GetComponent<ApiClient>();
                if (apiClient == null)
                {
                    apiClient = gameObject.AddComponent<ApiClient>();
                }
            }

            // 初始化相机控制器
            if (cameraController == null)
            {
                Camera mainCamera = Camera.main;
                if (mainCamera != null)
                {
                    cameraController = mainCamera.GetComponent<CameraController>();
                    if (cameraController == null)
                    {
                        cameraController = mainCamera.gameObject.AddComponent<CameraController>();
                    }
                }
            }

            // 初始化太阳能板生成器
            if (panelGenerator == null)
            {
                panelGenerator = GetComponent<SolarPanelGenerator>();
            }

            // 初始化太阳能板控制器
            if (panelController == null)
            {
                panelController = GetComponent<SolarPanelController>();
                if (panelController == null)
                {
                    panelController = gameObject.AddComponent<SolarPanelController>();
                }
            }

            // 初始化时间控制器
            if (timeController == null)
            {
                timeController = GetComponent<TimeController>();
                if (timeController == null)
                {
                    timeController = gameObject.AddComponent<TimeController>();
                }
            }

            // 初始化太阳可视化
            if (sunVisualizer == null)
            {
                sunVisualizer = FindObjectOfType<SunVisualizer>();
                if (sunVisualizer == null)
                {
                    GameObject sunObj = new GameObject("SunVisualizer");
                    sunVisualizer = sunObj.AddComponent<SunVisualizer>();
                }
            }

            // 初始化地形生成器
            if (terrainGenerator == null)
            {
                terrainGenerator = GetComponent<TerrainMeshGenerator>();
                if (terrainGenerator == null)
                {
                    terrainGenerator = gameObject.AddComponent<TerrainMeshGenerator>();
                }
            }
        }

        private void ConfigureTimeController()
        {
            if (timeController != null)
            {
                timeController.SetLocation(defaultLatitude, defaultLongitude, defaultTimezone);
            }
        }

        private void ConfigureSunVisualizer()
        {
            if (sunVisualizer != null && timeController != null)
            {
                // SunVisualizer 会自动查找 TimeController
            }
        }

        private void LoadTerrainData()
        {
            Debug.Log("[SceneManager] 正在加载地形数据...");

            // 先检查后端健康状态
            apiClient.HealthCheck(isHealthy =>
            {
                if (isHealthy)
                {
                    Debug.Log("[SceneManager] 后端服务可用，开始加载数据");
                    apiClient.GetTerrainLayout(OnTerrainDataLoaded, OnLoadError);
                }
                else
                {
                    Debug.LogWarning("[SceneManager] 后端服务不可用，使用测试数据");
                    LoadTestData();
                }
            });
        }

        private void OnTerrainDataLoaded(TerrainLayoutResponse data)
        {
            terrainData = data;
            Debug.Log($"[SceneManager] 地形数据加载成功:");
            Debug.Log($"   - 跟踪器数量: {(data.tables != null ? data.tables.Count : 0)}");
            Debug.Log($"   - 元数据: {(data.metadata != null ? "有" : "无")}");

            // 验证桩位数据
            if (data.tables != null && data.tables.Count > 0)
            {
                var firstTable = data.tables[0];
                Debug.Log($"   - 第一行 table_id: {firstTable.table_id}, 桩位数: {(firstTable.piles != null ? firstTable.piles.Count : 0)}");

                if (firstTable.piles != null && firstTable.piles.Count > 0)
                {
                    var firstPile = firstTable.piles[0];
                    Debug.Log($"   - 第一个桩位: x={firstPile.x}, y={firstPile.y}, z_ground={firstPile.z_ground}, z_top={firstPile.z_top}");
                }
            }

            // 计算统一的场景参数（确保太阳能板和地形使用相同参数）
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
            float scale = 250f / maxRange; // targetSceneSize = 250

            float centerX = (minX + maxX) / 2f;
            float centerY = (minY + maxY) / 2f;
            float groundCenter = minGround + (maxGround - minGround) / 2f;

            Debug.Log($"[SceneManager] 场景参数: scale={scale:F4}, center=({centerX:F1}, {centerY:F1}), groundCenter={groundCenter:F2}");

            // 确保 heightScale 同步
            float heightScale = panelGenerator != null ? panelGenerator.heightScale : 3.0f;
            if (terrainGenerator != null && panelGenerator != null)
            {
                terrainGenerator.heightScale = panelGenerator.heightScale;
            }

            // 生成太阳能板（使用统一参数）
            if (panelGenerator != null)
            {
                panelGenerator.GeneratePanels(data, scale, centerX, centerY, groundCenter);
            }

            // 生成地形网格（使用统一参数）
            if (terrainGenerator != null)
            {
                terrainGenerator.GenerateTerrain(data, scale, centerX, centerY, groundCenter);
            }

            // 初始化太阳能板控制器
            if (panelController != null)
            {
                // 等待一帧让太阳能板生成完成
                StartCoroutine(InitializePanelControllerAfterGeneration());
            }

            // 设置相机位置
            if (cameraController != null)
            {
                cameraController.SetTargetPosition(Vector3.zero);
                cameraController.SetDistance(initialCameraDistance);
            }

            isInitialized = true;
            Debug.Log("[SceneManager] 场景初始化完成");
        }

        private System.Collections.IEnumerator InitializePanelControllerAfterGeneration()
        {
            yield return null; // 等待一帧

            if (panelController != null)
            {
                panelController.Reinitialize();
            }
        }

        private void OnLoadError(string error)
        {
            Debug.LogError($"[SceneManager] 加载失败: {error}");
            LoadTestData();
        }

        /// <summary>
        /// 加载测试数据（后端不可用时使用）
        /// </summary>
        private void LoadTestData()
        {
            Debug.Log("[SceneManager] 生成测试地形数据...");

            terrainData = GenerateTestData();

            // 计算统一的场景参数
            float minX = float.MaxValue, maxX = float.MinValue;
            float minY = float.MaxValue, maxY = float.MinValue;
            float minGround = float.MaxValue, maxGround = float.MinValue;

            foreach (var table in terrainData.tables)
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
            float scale = 250f / maxRange;

            float centerX = (minX + maxX) / 2f;
            float centerY = (minY + maxY) / 2f;
            float groundCenter = minGround + (maxGround - minGround) / 2f;

            // 确保 heightScale 同步
            if (terrainGenerator != null && panelGenerator != null)
            {
                terrainGenerator.heightScale = panelGenerator.heightScale;
            }

            // 生成太阳能板（使用统一参数）
            if (panelGenerator != null)
            {
                panelGenerator.GeneratePanels(terrainData, scale, centerX, centerY, groundCenter);
            }

            // 生成地形网格（使用统一参数）
            if (terrainGenerator != null)
            {
                terrainGenerator.GenerateTerrain(terrainData, scale, centerX, centerY, groundCenter);
            }

            if (panelController != null)
            {
                StartCoroutine(InitializePanelControllerAfterGeneration());
            }

            if (cameraController != null)
            {
                cameraController.SetTargetPosition(Vector3.zero);
                cameraController.SetDistance(initialCameraDistance);
            }

            isInitialized = true;
        }

        /// <summary>
        /// 生成测试用例数据
        /// </summary>
        private TerrainLayoutResponse GenerateTestData()
        {
            var data = new TerrainLayoutResponse
            {
                tables = new System.Collections.Generic.List<TableData>(),
                metadata = new Metadata
                {
                    source_file = "test_data",
                    total_tables = 5,
                    total_piles = 50,
                    bounds = new BoundsData
                    {
                        min_x = 0, max_x = 100,
                        min_y = 0, max_y = 50
                    }
                }
            };

            // 生成5行跟踪器，每行10个桩位
            int rowCount = 5;
            int pilesPerRow = 10;
            float rowSpacing = 10f;
            float pileSpacing = 5f;

            for (int row = 0; row < rowCount; row++)
            {
                var table = new TableData
                {
                    table_id = row + 1,  // int 类型
                    table_direction = "North facing", // 南北向
                    table_slope_deg = 0f,
                    piles = new System.Collections.Generic.List<PileData>()
                };

                for (int i = 0; i < pilesPerRow; i++)
                {
                    table.piles.Add(new PileData
                    {
                        index = i + 1,
                        x = i * pileSpacing,
                        y = row * rowSpacing,
                        z_ground = 0f,
                        z_top = 2.5f
                    });
                }

                data.tables.Add(table);
            }

            data.metadata.total_piles = rowCount * pilesPerRow;

            return data;
        }

        /// <summary>
        /// 公开方法：重新加载地形数据
        /// </summary>
        public void ReloadTerrainData()
        {
            if (apiClient != null)
            {
                apiClient.GetTerrainLayout(OnTerrainDataLoaded, OnLoadError);
            }
        }

        /// <summary>
        /// 公开方法：设置地理位置
        /// </summary>
        public void SetLocation(double latitude, double longitude, float timezone = 8f)
        {
            defaultLatitude = latitude;
            defaultLongitude = longitude;
            defaultTimezone = timezone;

            if (timeController != null)
            {
                timeController.SetLocation(latitude, longitude, timezone);
            }
        }

        /// <summary>
        /// 公开方法：获取当前场景状态
        /// </summary>
        public bool IsInitialized => isInitialized;
    }
}
