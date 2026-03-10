using UnityEngine;
using PVSimulator.SolarPanel;
using PVSimulator.Time;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace PVSimulator.Export
{
    /// <summary>
    /// 数据导出器 - 支持导出追踪角度、遮挡系数和截图
    /// </summary>
    public class DataExporter : MonoBehaviour
    {
        [Header("组件引用")]
        [SerializeField] private SolarPanelController panelController;
        [SerializeField] private TimeController timeController;

        [Header("导出设置")]
        [Tooltip("默认导出路径（相对于项目根目录）")]
        public string exportPath = "Exports";

        [Tooltip("截图分辨率宽度")]
        public int screenshotWidth = 1920;

        [Tooltip("截图分辨率高度")]
        public int screenshotHeight = 1080;

        private string fullExportPath;

        private void Awake()
        {
            // 确保导出目录存在
            fullExportPath = Path.Combine(Application.dataPath, "..", exportPath);
            if (!Directory.Exists(fullExportPath))
            {
                Directory.CreateDirectory(fullExportPath);
            }
        }

        /// <summary>
        /// 导出追踪角度到 CSV
        /// </summary>
        /// <param name="filename">文件名（不含扩展名）</param>
        public void ExportTrackingAngles(string filename = null)
        {
            if (panelController == null)
            {
                Debug.LogError("[DataExporter] panelController 未设置");
                return;
            }

            var trackingInfo = panelController.GetTrackingInfo();
            if (trackingInfo == null || trackingInfo.Count == 0)
            {
                Debug.LogWarning("[DataExporter] 没有追踪数据可导出");
                return;
            }

            string timeStamp = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string fileName = filename ?? $"tracking_angles_{timeStamp}.csv";
            string filePath = Path.Combine(fullExportPath, fileName);

            StringBuilder sb = new StringBuilder();

            // CSV 头部
            sb.AppendLine("TableID,CurrentTilt,TargetTilt,ShadingFactor,ShadingMargin");

            // 数据行
            foreach (var info in trackingInfo)
            {
                sb.AppendLine(string.Format("{0},{1:F2},{2:F2},{3:F4},{4:F2}",
                    info.tableId,
                    info.currentTilt,
                    info.targetTilt,
                    info.shadingFactor,
                    info.shadingMargin
                ));
            }

            // 添加统计信息
            var stats = panelController.GetStatistics();
            sb.AppendLine();
            sb.AppendLine($"# 统计信息");
            sb.AppendLine($"# 总行数,{stats.totalRows}");
            sb.AppendLine($"# 平均角度,{stats.averageAngle:F2}");
            sb.AppendLine($"# 平均遮挡系数,{stats.averageShadingFactor:F4}");
            sb.AppendLine($"# 能量损失,{stats.energyLossPercent:F2}%");
            sb.AppendLine($"# 遮挡行数,{stats.shadedRowCount}");

            // 添加时间信息
            if (timeController != null)
            {
                sb.AppendLine($"# 时间,{timeController.CurrentDateTime:yyyy-MM-dd HH:mm}");
                var sunPos = timeController.CurrentSunPosition;
                sb.AppendLine($"# 太阳高度,{sunPos.altitude:F2}");
                sb.AppendLine($"# 太阳方位,{sunPos.azimuth:F2}");
            }

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
            Debug.Log($"[DataExporter] 追踪角度已导出到: {filePath}");
        }

        /// <summary>
        /// 导出遮挡系数到 CSV
        /// </summary>
        /// <param name="filename">文件名（不含扩展名）</param>
        public void ExportShadingFactors(string filename = null)
        {
            if (panelController == null)
            {
                Debug.LogError("[DataExporter] panelController 未设置");
                return;
            }

            var trackingInfo = panelController.GetTrackingInfo();
            if (trackingInfo == null || trackingInfo.Count == 0)
            {
                Debug.LogWarning("[DataExporter] 没有遮挡数据可导出");
                return;
            }

            string timeStamp = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string fileName = filename ?? $"shading_factors_{timeStamp}.csv";
            string filePath = Path.Combine(fullExportPath, fileName);

            StringBuilder sb = new StringBuilder();

            // CSV 头部
            sb.AppendLine("TableID,ShadingFactor,ShadingMargin,Status");

            // 数据行
            int noShading = 0, lightShading = 0, mediumShading = 0, heavyShading = 0;

            foreach (var info in trackingInfo)
            {
                string status;
                if (info.shadingFactor >= 0.99f)
                {
                    status = "无遮挡";
                    noShading++;
                }
                else if (info.shadingFactor >= 0.8f)
                {
                    status = "轻微遮挡";
                    lightShading++;
                }
                else if (info.shadingFactor >= 0.5f)
                {
                    status = "中度遮挡";
                    mediumShading++;
                }
                else
                {
                    status = "严重遮挡";
                    heavyShading++;
                }

                sb.AppendLine(string.Format("{0},{1:F4},{2:F2},{3}",
                    info.tableId,
                    info.shadingFactor,
                    info.shadingMargin,
                    status
                ));
            }

            // 添加统计信息
            var stats = panelController.GetStatistics();
            sb.AppendLine();
            sb.AppendLine($"# 遮挡统计");
            sb.AppendLine($"# 总行数,{stats.totalRows}");
            sb.AppendLine($"# 无遮挡,{noShading}");
            sb.AppendLine($"# 轻微遮挡,{lightShading}");
            sb.AppendLine($"# 中度遮挡,{mediumShading}");
            sb.AppendLine($"# 严重遮挡,{heavyShading}");
            sb.AppendLine($"# 平均遮挡系数,{stats.averageShadingFactor:F4}");
            sb.AppendLine($"# 能量损失,{stats.energyLossPercent:F2}%");

            // 添加时间信息
            if (timeController != null)
            {
                sb.AppendLine($"# 时间,{timeController.CurrentDateTime:yyyy-MM-dd HH:mm}");
                var sunPos = timeController.CurrentSunPosition;
                sb.AppendLine($"# 太阳高度,{sunPos.altitude:F2}");
                sb.AppendLine($"# 太阳方位,{sunPos.azimuth:F2}");
            }

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
            Debug.Log($"[DataExporter] 遮挡系数已导出到: {filePath}");
        }

        /// <summary>
        /// 导出完整报告（包含追踪角度和遮挡系数）
        /// </summary>
        /// <param name="filename">文件名（不含扩展名）</param>
        public void ExportFullReport(string filename = null)
        {
            if (panelController == null)
            {
                Debug.LogError("[DataExporter] panelController 未设置");
                return;
            }

            var trackingInfo = panelController.GetTrackingInfo();
            if (trackingInfo == null || trackingInfo.Count == 0)
            {
                Debug.LogWarning("[DataExporter] 没有数据可导出");
                return;
            }

            string timeStamp = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string fileName = filename ?? $"full_report_{timeStamp}.csv";
            string filePath = Path.Combine(fullExportPath, fileName);

            StringBuilder sb = new StringBuilder();

            // 报告头部
            sb.AppendLine("=== 光伏仿真系统完整报告 ===");
            sb.AppendLine();

            // 时间信息
            if (timeController != null)
            {
                sb.AppendLine($"仿真时间: {timeController.CurrentDateTime:yyyy-MM-dd HH:mm}");
                var sunPos = timeController.CurrentSunPosition;
                sb.AppendLine($"太阳高度角: {sunPos.altitude:F2}");
                sb.AppendLine($"太阳方位角: {sunPos.azimuth:F2}");
                sb.AppendLine();
            }

            // 统计信息
            var stats = panelController.GetStatistics();
            sb.AppendLine("=== 统计摘要 ===");
            sb.AppendLine($"总跟踪器数量: {stats.totalRows}");
            sb.AppendLine($"平均追踪角度: {stats.averageAngle:F2}");
            sb.AppendLine($"平均遮挡系数: {stats.averageShadingFactor:F4}");
            sb.AppendLine($"能量损失: {stats.energyLossPercent:F2}%");
            sb.AppendLine($"有遮挡的行数: {stats.shadedRowCount}");
            sb.AppendLine();

            // 详细数据
            sb.AppendLine("=== 详细数据 ===");
            sb.AppendLine("TableID,CurrentTilt,TargetTilt,ShadingFactor,ShadingMargin,Status");

            foreach (var info in trackingInfo)
            {
                string status = info.shadingFactor >= 0.99f ? "OK" :
                               info.shadingFactor >= 0.8f ? "轻" :
                               info.shadingFactor >= 0.5f ? "中" : "重";

                sb.AppendLine(string.Format("{0},{1:F2},{2:F2},{3:F4},{4:F2},{5}",
                    info.tableId,
                    info.currentTilt,
                    info.targetTilt,
                    info.shadingFactor,
                    info.shadingMargin,
                    status
                ));
            }

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
            Debug.Log($"[DataExporter] 完整报告已导出到: {filePath}");
        }

        /// <summary>
        /// 截图
        /// </summary>
        /// <param name="filename">文件名（不含扩展名）</param>
        public void TakeScreenshot(string filename = null)
        {
            string timeStamp = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string fileName = filename ?? $"screenshot_{timeStamp}.png";
            string filePath = Path.Combine(fullExportPath, fileName);

            // 使用高分辨率截图
            RenderTexture rt = new RenderTexture(screenshotWidth, screenshotHeight, 24);
            Camera.main.targetTexture = rt;
            Texture2D screenshot = new Texture2D(screenshotWidth, screenshotHeight, TextureFormat.RGB24, false);

            Camera.main.Render();
            RenderTexture.active = rt;
            screenshot.ReadPixels(new Rect(0, 0, screenshotWidth, screenshotHeight), 0, 0);

            Camera.main.targetTexture = null;
            RenderTexture.active = null;
            Destroy(rt);

            byte[] bytes = screenshot.EncodeToPNG();
            File.WriteAllBytes(filePath, bytes);
            Destroy(screenshot);

            Debug.Log($"[DataExporter] 截图已保存到: {filePath}");
        }

        /// <summary>
        /// 快速截图（使用当前屏幕分辨率）
        /// </summary>
        /// <param name="filename">文件名（不含扩展名）</param>
        public void TakeQuickScreenshot(string filename = null)
        {
            string timeStamp = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string fileName = filename ?? $"screenshot_{timeStamp}.png";
            string filePath = Path.Combine(fullExportPath, fileName);

            ScreenCapture.CaptureScreenshot(filePath);
            Debug.Log($"[DataExporter] 快速截图已保存到: {filePath}");
        }

        /// <summary>
        /// 导出当前时间快照（CSV + 截图）
        /// </summary>
        public void ExportSnapshot()
        {
            string timeStamp = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string prefix = $"snapshot_{timeStamp}";

            ExportFullReport($"{prefix}_report.csv");
            TakeScreenshot($"{prefix}.png");

            Debug.Log($"[DataExporter] 快照已导出，前缀: {prefix}");
        }

        /// <summary>
        /// 获取导出目录路径
        /// </summary>
        public string GetExportPath()
        {
            return fullExportPath;
        }

        /// <summary>
        /// 打开导出目录
        /// </summary>
        public void OpenExportFolder()
        {
            System.Diagnostics.Process.Start(fullExportPath);
        }
    }
}
