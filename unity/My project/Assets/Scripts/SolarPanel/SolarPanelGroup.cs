using UnityEngine;
using System.Collections.Generic;

namespace PVSimulator.SolarPanel
{
    /// <summary>
    /// 太阳能板组 - 代表一行追踪器
    /// </summary>
    public class SolarPanelGroup
    {
        public string tableId { get; private set; }
        public float axisAzimuth { get; private set; }
        public float slopeDeg { get; private set; }  // 行坡度（度）- 用于地形感知回溯
        public float slopeAzimuthDeg { get; private set; }  // 坡度方位角（度）- 用于横轴坡度计算
        public List<GameObject> panels { get; private set; }
        public Transform container { get; private set; }

        public float currentRotation { get; private set; }
        public float targetRotation { get; set; }

        public SolarPanelGroup(string tableId, float axisAzimuth, float slopeDeg = 0f, float slopeAzimuthDeg = 180f)
        {
            this.tableId = tableId;
            this.axisAzimuth = axisAzimuth;
            this.slopeDeg = slopeDeg;
            this.slopeAzimuthDeg = slopeAzimuthDeg;
            this.panels = new List<GameObject>();
            this.currentRotation = 0f;
            this.targetRotation = 0f;
        }

        /// <summary>
        /// 计算横轴坡度 (βc) - NREL论文 Equation 25-26
        /// βc = β_terrain × sin(γ_slope - γ_axis)
        /// </summary>
        /// <returns>横轴坡度（度）</returns>
        public float CalculateCrossAxisTilt()
        {
            if (slopeDeg == 0f)
                return 0f;

            // 相对方位角 = 坡度方位角 - 轴方位角
            float relativeAzimuthRad = (slopeAzimuthDeg - axisAzimuth) * Mathf.Deg2Rad;
            float slopeRad = slopeDeg * Mathf.Deg2Rad;

            // βc = β_terrain × sin(γ_slope - γ_axis)
            float crossAxisTilt = slopeRad * Mathf.Sin(relativeAzimuthRad);
            return crossAxisTilt * Mathf.Rad2Deg;
        }

        public void AddPanel(GameObject panel)
        {
            panels.Add(panel);
        }

        public void SetContainer(Transform containerTransform)
        {
            container = containerTransform;
        }

        /// <summary>
        /// 更新旋转
        /// </summary>
        public void UpdateRotation(float smoothingFactor)
        {
            // 平滑过渡
            float diff = Mathf.Abs(targetRotation - currentRotation);
            if (diff > 0.1f)
            {
                currentRotation = Mathf.Lerp(currentRotation, targetRotation, smoothingFactor);
            }
            else if (diff > 0.01f)
            {
                currentRotation = targetRotation;
            }

            // 应用旋转到所有面板
            foreach (var panel in panels)
            {
                if (panel != null)
                {
                    // 保留原有的 Y 轴旋转（朝向），只修改 X 轴（倾斜角）
                    float yRotation = panel.transform.localEulerAngles.y;
                    panel.transform.localRotation = Quaternion.Euler(currentRotation, yRotation, 0);

                    // 调试日志：验证旋转应用
                    if (UnityEngine.Time.frameCount % 300 == 0 && panels.IndexOf(panel) == 0)
                    {
                        UnityEngine.Debug.Log($"[SolarPanelGroup] {tableId}: Applying rotation X={currentRotation:F1}°, Y={yRotation:F1}° to {panel.name}");
                    }
                }
            }
        }

        /// <summary>
        /// 获取组中心位置（优先使用container的世界坐标）
        /// </summary>
        public Vector3 GetCenterPosition()
        {
            // 优先使用container的世界坐标（更准确）
            if (container != null)
            {
                return container.position;
            }

            if (panels == null || panels.Count == 0)
                return Vector3.zero;

            Vector3 sum = Vector3.zero;
            int count = 0;

            foreach (var panel in panels)
            {
                if (panel != null)
                {
                    sum += panel.transform.position;
                    count++;
                }
            }

            return count > 0 ? sum / count : Vector3.zero;
        }
    }
}
