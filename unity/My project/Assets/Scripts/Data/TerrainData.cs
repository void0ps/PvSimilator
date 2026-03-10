using System;
using System.Collections.Generic;
using UnityEngine;

namespace PVSimulator.Data
{
    /// <summary>
    /// 地形布局响应 - 对应 API /api/v1/terrain/layout
    /// </summary>
    [Serializable]
    public class TerrainLayoutResponse
    {
        public List<TableData> tables;
        public Metadata metadata;
    }

    /// <summary>
    /// 跟踪器数据（单行）
    /// </summary>
    [Serializable]
    public class TableData
    {
        public int table_id;              // int 类型匹配后端
        public string zone_id;
        public string preset_type;
        public string table_direction;    // 后端字段名
        public float table_slope_deg;     // 行坡度（度）- 用于地形感知回溯
        public float slope_delta_deg;     // 与相邻行的坡度差
        public string notes;
        public List<PileData> piles;

        // 计算属性：将 table_direction 转换为角度
        public float axis_azimuth
        {
            get
            {
                if (string.IsNullOrEmpty(table_direction)) return 180f;
                // "North facing" = 180° (南北轴)
                if (table_direction.ToLower().Contains("north")) return 180f;
                if (table_direction.ToLower().Contains("south")) return 0f;
                if (table_direction.ToLower().Contains("east")) return 90f;
                if (table_direction.ToLower().Contains("west")) return 270f;
                return 180f; // 默认南北向
            }
        }
    }

    /// <summary>
    /// 桩位数据 - 严格匹配后端 JSON 字段
    /// </summary>
    [Serializable]
    public class PileData
    {
        public int index;           // 桩位索引
        public float x;             // 坐标 X (原 coord_x)
        public float y;             // 坐标 Y (原 coord_y)
        public float lat;           // 纬度
        public float lon;           // 经度
        public float z_top;         // 桩顶高度
        public float z_ground;      // 地面高度
        public float pile_reveal_m; // 桩露出高度
        public float table_slope_deg;
        public float? slope_delta_deg;
        public string notes;

        // 兼容性属性（供旧代码使用）
        public float z => z_top;    // 兼容旧代码
    }

    /// <summary>
    /// 元数据
    /// </summary>
    [Serializable]
    public class Metadata
    {
        public string source_file;
        public int total_tables;
        public int total_piles;
        public string generated_at;
        public BoundsData bounds;
    }

    /// <summary>
    /// 边界数据 - 匹配后端字段名
    /// </summary>
    [Serializable]
    public class BoundsData
    {
        public float min_x;
        public float max_x;
        public float min_y;
        public float max_y;
        public float? min_z;
        public float? max_z;

        // 兼容性属性
        public float minX => min_x;
        public float maxX => max_x;
        public float minY => min_y;
        public float maxY => max_y;
    }
}
