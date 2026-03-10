using UnityEngine;

namespace PVSimulator.SolarPanel
{
    /// <summary>
    /// 太阳能板材质控制器 - 管理太阳能板的视觉效果
    /// </summary>
    [RequireComponent(typeof(Renderer))]
    public class PanelMaterialController : MonoBehaviour
    {
        [Header("材质设置")]
        [SerializeField] private Color baseColor = new Color(0.1f, 0.15f, 0.35f);
        [SerializeField] private Color highlightColor = new Color(0.2f, 0.3f, 0.6f);
        [SerializeField] private float metallic = 0.8f;
        [SerializeField] private float smoothness = 0.3f;

        [Header("动态效果")]
        // [SerializeField] private bool enableReflection = true;
        // [SerializeField] private float reflectionIntensity = 0.5f;

        private Renderer panelRenderer;
        private MaterialPropertyBlock propertyBlock;
        private static readonly int BaseColorID = Shader.PropertyToID("_BaseColor");
        private static readonly int MetallicID = Shader.PropertyToID("_Metallic");
        private static readonly int SmoothnessID = Shader.PropertyToID("_Smoothness");

        private void Awake()
        {
            panelRenderer = GetComponent<Renderer>();
            propertyBlock = new MaterialPropertyBlock();
            InitializeMaterial();
        }

        private void InitializeMaterial()
        {
            if (panelRenderer == null) return;

            // 设置材质属性
            propertyBlock.SetColor(BaseColorID, baseColor);
            propertyBlock.SetFloat(MetallicID, metallic);
            propertyBlock.SetFloat(SmoothnessID, smoothness);

            panelRenderer.SetPropertyBlock(propertyBlock);
        }

        /// <summary>
        /// 设置高亮状态
        /// </summary>
        public void SetHighlighted(bool highlighted)
        {
            if (panelRenderer == null || propertyBlock == null) return;

            Color color = highlighted ? highlightColor : baseColor;
            propertyBlock.SetColor(BaseColorID, color);
            panelRenderer.SetPropertyBlock(propertyBlock);
        }

        /// <summary>
        /// 设置自定义颜色
        /// </summary>
        public void SetColor(Color color)
        {
            if (panelRenderer == null || propertyBlock == null) return;

            propertyBlock.SetColor(BaseColorID, color);
            panelRenderer.SetPropertyBlock(propertyBlock);
        }

        /// <summary>
        /// 设置阳光强度影响（根据太阳高度角调整亮度）
        /// </summary>
        public void SetSunIntensity(float intensity)
        {
            if (panelRenderer == null || propertyBlock == null) return;

            Color adjustedColor = Color.Lerp(baseColor * 0.8f, baseColor * 1.2f, intensity);
            propertyBlock.SetColor(BaseColorID, adjustedColor);
            panelRenderer.SetPropertyBlock(propertyBlock);
        }
    }
}
