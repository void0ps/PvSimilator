using UnityEngine;
using PVSimulator.Time;

namespace PVSimulator.Sun
{
    /// <summary>
    /// 太阳可视化 - 在场景中显示太阳位置和光照
    /// </summary>
    public class SunVisualizer : MonoBehaviour
    {
        [Header("引用")]
        [SerializeField] private TimeController timeController;
        [SerializeField] private Light directionalLight;

        [Header("太阳视觉设置")]
        [SerializeField] private Transform sunVisual; // 太阳球体
        [SerializeField] private float sunDistance = 500f; // 太阳距离
        [SerializeField] private float sunSize = 20f; // 太阳大小
        [SerializeField] private Color sunColor = new Color(1f, 0.95f, 0.8f); // 太阳颜色
        [SerializeField] private Color horizonColor = new Color(1f, 0.6f, 0.3f); // 地平线颜色

        [Header("光照设置")]
        [SerializeField] private float maxIntensity = 1.2f;
        [SerializeField] private float minIntensity = 0.1f;
        [SerializeField] private AnimationCurve intensityCurve; // 基于高度角的光照强度曲线
        [SerializeField] private Gradient ambientColorGradient; // 基于高度角的环境光颜色

        [Header("天空设置")]
        [SerializeField] private Material skyboxMaterial;
        [SerializeField] private Color daySkyColor = new Color(0.4f, 0.6f, 0.9f);
        [SerializeField] private Color sunsetSkyColor = new Color(1f, 0.5f, 0.3f);
        [SerializeField] private Color nightSkyColor = new Color(0.05f, 0.05f, 0.15f);

        [Header("阴影设置")]
        [SerializeField] private bool enableShadows = true;
        // [SerializeField] private int shadowResolution = 2; // 0=Low, 1=Medium, 2=High, 3=Very High
        [SerializeField] private float shadowDistance = 200f;

        private SunPosition currentSunPosition;

        private void Awake()
        {
            InitializeComponents();
            InitializeCurves();
        }

        private void InitializeComponents()
        {
            if (timeController == null)
            {
                timeController = FindObjectOfType<TimeController>();
            }

            if (directionalLight == null)
            {
                Light[] lights = FindObjectsOfType<Light>();
                foreach (var light in lights)
                {
                    if (light.type == LightType.Directional)
                    {
                        directionalLight = light;
                        break;
                    }
                }

                if (directionalLight == null)
                {
                    GameObject sunLightObj = new GameObject("SunLight");
                    directionalLight = sunLightObj.AddComponent<Light>();
                    directionalLight.type = LightType.Directional;
                }
            }

            // 创建太阳可视化对象
            if (sunVisual == null)
            {
                CreateSunVisual();
            }
        }

        private void InitializeCurves()
        {
            // 初始化光照强度曲线
            if (intensityCurve == null || intensityCurve.length == 0)
            {
                intensityCurve = new AnimationCurve();
                intensityCurve.AddKey(0f, 0f);      // 地平线
                intensityCurve.AddKey(15f, 0.5f);   // 低角度
                intensityCurve.AddKey(45f, 0.9f);   // 中等角度
                intensityCurve.AddKey(90f, 1f);     // 天顶
            }

            // 初始化环境光颜色渐变
            if (ambientColorGradient == null || ambientColorGradient.colorKeys.Length == 0)
            {
                ambientColorGradient = new Gradient();
                ambientColorGradient.SetKeys(
                    new GradientColorKey[] {
                        new GradientColorKey(nightSkyColor, 0f),
                        new GradientColorKey(sunsetSkyColor, 0.1f),
                        new GradientColorKey(daySkyColor, 0.3f),
                        new GradientColorKey(daySkyColor, 0.7f),
                        new GradientColorKey(sunsetSkyColor, 0.9f),
                        new GradientColorKey(nightSkyColor, 1f)
                    },
                    new GradientAlphaKey[] {
                        new GradientAlphaKey(1f, 0f),
                        new GradientAlphaKey(1f, 1f)
                    }
                );
            }
        }

        private void CreateSunVisual()
        {
            GameObject sunObj = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sunObj.name = "SunVisual";
            sunObj.transform.SetParent(transform);
            sunObj.transform.localScale = Vector3.one * sunSize;

            // 设置材质为自发光
            Renderer renderer = sunObj.GetComponent<Renderer>();
            Material sunMat = new Material(Shader.Find("Unlit/Color"));
            sunMat.color = sunColor;
            renderer.material = sunMat;

            // 移除碰撞器（不需要）
            Collider col = sunObj.GetComponent<Collider>();
            if (col != null) Destroy(col);

            sunVisual = sunObj.transform;
        }

        private void OnEnable()
        {
            if (timeController != null)
            {
                timeController.OnSunPositionChanged.AddListener(OnSunPositionUpdated);
            }
        }

        private void OnDisable()
        {
            if (timeController != null)
            {
                timeController.OnSunPositionChanged.RemoveListener(OnSunPositionUpdated);
            }
        }

        private void Start()
        {
            // 初始更新
            if (timeController != null)
            {
                OnSunPositionUpdated(timeController.CurrentSunPosition);
            }
        }

        private void OnSunPositionUpdated(SunPosition sunPosition)
        {
            currentSunPosition = sunPosition;
            UpdateSunVisual();
            UpdateLighting();
            UpdateSkybox();
        }

        private void UpdateSunVisual()
        {
            if (sunVisual == null) return;

            // 计算太阳位置
            Vector3 sunDirection = currentSunPosition.GetDirection();
            sunVisual.position = sunDirection * sunDistance;

            // 根据高度角调整太阳外观
            float normalizedAltitude = Mathf.Clamp01(currentSunPosition.altitude / 90f);

            // 调整太阳颜色（低角度时偏红）
            Color currentColor = Color.Lerp(horizonColor, sunColor, normalizedAltitude);
            Renderer renderer = sunVisual.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.material.color = currentColor;
            }

            // 太阳大小随高度角略有变化（大气折射效果）
            float sizeMultiplier = 1f + (1f - normalizedAltitude) * 0.3f;
            sunVisual.localScale = Vector3.one * sunSize * sizeMultiplier;

            // 太阳在地平线以下时隐藏
            sunVisual.gameObject.SetActive(currentSunPosition.isValid);
        }

        private void UpdateLighting()
        {
            if (directionalLight == null) return;

            // 更新光源方向
            Vector3 lightDirection = -currentSunPosition.GetDirection();
            directionalLight.transform.forward = lightDirection;

            // 计算光照强度
            float intensity = 0f;
            if (currentSunPosition.isValid)
            {
                float curveValue = intensityCurve.Evaluate(currentSunPosition.altitude);
                intensity = Mathf.Lerp(minIntensity, maxIntensity, curveValue);
            }
            directionalLight.intensity = intensity;

            // 更新光源颜色
            float normalizedAltitude = Mathf.Clamp01(currentSunPosition.altitude / 90f);
            Color lightColor = Color.Lerp(horizonColor, Color.white, normalizedAltitude);
            directionalLight.color = lightColor;

            // 更新阴影设置
            if (enableShadows)
            {
                directionalLight.shadows = LightShadows.Soft;
                QualitySettings.shadowDistance = shadowDistance;
            }
            else
            {
                directionalLight.shadows = LightShadows.None;
            }

            // 更新环境光
            float dayProgress = GetDayProgress();
            Color ambientColor = ambientColorGradient.Evaluate(dayProgress);
            RenderSettings.ambientLight = ambientColor;
            RenderSettings.ambientIntensity = 0.5f + normalizedAltitude * 0.5f;
        }

        private void UpdateSkybox()
        {
            if (skyboxMaterial == null) return;

            float normalizedAltitude = Mathf.Clamp01(currentSunPosition.altitude / 90f);
            Color skyColor = Color.Lerp(nightSkyColor, daySkyColor, normalizedAltitude);

            // 低角度时添加日落/日出颜色
            if (currentSunPosition.altitude > 0 && currentSunPosition.altitude < 20)
            {
                float t = currentSunPosition.altitude / 20f;
                skyColor = Color.Lerp(sunsetSkyColor, skyColor, t);
            }

            skyboxMaterial.SetColor("_SkyColor", skyColor);
        }

        /// <summary>
        /// 获取一天中的进度（0-1）
        /// </summary>
        private float GetDayProgress()
        {
            if (timeController == null) return 0.5f;

            var dt = timeController.CurrentDateTime;
            float hour = dt.Hour + dt.Minute / 60f;
            return hour / 24f;
        }

        /// <summary>
        /// 手动设置太阳位置（用于测试）
        /// </summary>
        public void SetSunPosition(SunPosition position)
        {
            currentSunPosition = position;
            UpdateSunVisual();
            UpdateLighting();
            UpdateSkybox();
        }
    }
}
