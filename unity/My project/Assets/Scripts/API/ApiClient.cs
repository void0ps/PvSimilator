using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using PVSimulator.Data;

namespace PVSimulator.API
{
    /// <summary>
    /// 后端API客户端 - 获取精确计算数据
    /// 后端做精确计算，前端做3D可视化
    /// </summary>
    public class ApiClient : MonoBehaviour
    {
        [Header("API配置")]
        [SerializeField] private string baseUrl = "http://localhost:8000";
        [SerializeField] private float timeout = 30f;

        #region 数据模型

        [Serializable]
        public class SunPosition
        {
            public float zenith;
            public float azimuth;
            public float elevation;
        }

        [Serializable]
        public class TrackingRowData
        {
            public float angle;
            public float shading_factor;
            public float shading_margin;
        }

        [Serializable]
        public class TrackingStatistics
        {
            public float average_shading_factor;
            public float min_shading_factor;
            public int shaded_row_count;
            public int total_row_count;
            public float energy_loss_percent;
        }

        [Serializable]
        public class RealtimeTrackingResponse
        {
            public string timestamp;
            public SunPosition sun_position;
            public TrackingStatistics statistics;
        }

        // 用于解析tracking_data的辅助类
        [Serializable]
        public class TrackingDataWrapper
        {
            public string timestamp;
            public SunPosition sun_position;
            public TrackingStatistics statistics;
            public string tracking_data_json;  // 原始JSON字符串
        }

        #endregion

        #region 地形数据API

        public void GetTerrainLayout(Action<TerrainLayoutResponse> onSuccess, Action<string> onError = null)
        {
            StartCoroutine(GetRequest($"{baseUrl}/api/v1/terrain/layout", onSuccess, onError));
        }

        public void GetTerrainTable(int tableId, Action<TableData> onSuccess, Action<string> onError = null)
        {
            StartCoroutine(GetRequest($"{baseUrl}/api/v1/terrain/layout/{tableId}", onSuccess, onError));
        }

        #endregion

        #region 实时追踪API

        /// <summary>
        /// 获取当前时刻的追踪数据（后端精确计算）
        /// </summary>
        public void GetCurrentTracking(
            float latitude,
            float longitude,
            bool enableBacktracking,
            bool useNrelShadingFraction,
            Action<RealtimeTrackingResponse> onSuccess,
            Action<string> onError = null)
        {
            string url = $"{baseUrl}/api/v1/shading/realtime/tracking/current" +
                $"?latitude={latitude}" +
                $"&longitude={longitude}" +
                $"&enable_backtracking={enableBacktracking.ToString().ToLower()}" +
                $"&use_nrel_shading_fraction={useNrelShadingFraction.ToString().ToLower()}";

            StartCoroutine(GetRealtimeTrackingRequest(url, onSuccess, onError));
        }

        /// <summary>
        /// 获取指定时间的追踪数据（后端精确计算）
        /// </summary>
        public void GetRealtimeTracking(
            float latitude,
            float longitude,
            string datetimeUtc,
            bool enableBacktracking,
            bool useNrelShadingFraction,
            Action<RealtimeTrackingResponse> onSuccess,
            Action<string> onError = null)
        {
            // 使用POST请求
            var requestData = new
            {
                latitude = latitude,
                longitude = longitude,
                timezone = -8.0,
                datetime_utc = datetimeUtc,
                enable_backtracking = enableBacktracking,
                use_nrel_shading_fraction = useNrelShadingFraction
            };

            string json = JsonUtility.ToJson(requestData);
            StartCoroutine(PostRequest($"{baseUrl}/api/v1/shading/realtime/tracking", json, onSuccess, onError));
        }

        private IEnumerator GetRealtimeTrackingRequest(
            string url,
            Action<RealtimeTrackingResponse> onSuccess,
            Action<string> onError)
        {
            Debug.Log($"[ApiClient] 请求实时追踪数据: {url}");

            using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                request.timeout = (int)timeout;
                request.SetRequestHeader("Content-Type", "application/json");

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    string json = request.downloadHandler.text;
                    try
                    {
                        // 解析主要数据
                        var wrapper = JsonUtility.FromJson<RealtimeTrackingResponse>(json);

                        // 手动解析tracking_data字典
                        var trackingData = ParseTrackingData(json);
                        onSuccess?.Invoke(wrapper);
                    }
                    catch (Exception e)
                    {
                        string error = $"解析实时追踪数据失败: {e.Message}";
                        Debug.LogError($"[ApiClient] {error}");
                        onError?.Invoke(error);
                    }
                }
                else
                {
                    string error = $"请求失败: {request.error}";
                    Debug.LogError($"[ApiClient] {error}");
                    onError?.Invoke(error);
                }
            }
        }

        private IEnumerator PostRequest<T>(
            string url,
            string jsonBody,
            Action<T> onSuccess,
            Action<string> onError)
        {
            Debug.Log($"[ApiClient] POST请求: {url}");

            using (UnityWebRequest request = new UnityWebRequest(url, "POST"))
            {
                byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(jsonBody);
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.timeout = (int)timeout;
                request.SetRequestHeader("Content-Type", "application/json");

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    string json = request.downloadHandler.text;
                    try
                    {
                        T data = JsonUtility.FromJson<T>(json);
                        onSuccess?.Invoke(data);
                    }
                    catch (Exception e)
                    {
                        string error = $"JSON解析失败: {e.Message}";
                        Debug.LogError($"[ApiClient] {error}");
                        onError?.Invoke(error);
                    }
                }
                else
                {
                    string error = $"请求失败: {request.error}";
                    Debug.LogError($"[ApiClient] {error}");
                    onError?.Invoke(error);
                }
            }
        }

        /// <summary>
        /// 解析tracking_data字典（Unity的JsonUtility不支持字典）
        /// </summary>
        private Dictionary<string, TrackingRowData> ParseTrackingData(string json)
        {
            var result = new Dictionary<string, TrackingRowData>();

            // 简单的JSON解析（查找tracking_data部分）
            int startIdx = json.IndexOf("\"tracking_data\":");
            if (startIdx < 0) return result;

            startIdx = json.IndexOf("{", startIdx);
            if (startIdx < 0) return result;

            int depth = 1;
            int endIdx = startIdx + 1;
            while (endIdx < json.Length && depth > 0)
            {
                if (json[endIdx] == '{') depth++;
                else if (json[endIdx] == '}') depth--;
                endIdx++;
            }

            string trackingJson = json.Substring(startIdx, endIdx - startIdx);

            // 这里简化处理，实际项目中建议使用Newtonsoft.JSON或其他JSON库
            // Unity2020+可以使用Unity的JsonUtility配合自定义包装类

            return result;
        }

        #endregion

        #region 通用请求方法

        private IEnumerator GetRequest<T>(string url, Action<T> onSuccess, Action<string> onError)
        {
            Debug.Log($"[ApiClient] GET请求: {url}");

            using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                request.timeout = (int)timeout;
                request.SetRequestHeader("Content-Type", "application/json");

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    string json = request.downloadHandler.text;
                    Debug.Log($"[ApiClient] 响应成功，数据长度: {json.Length}");

                    try
                    {
                        T data = JsonUtility.FromJson<T>(json);
                        onSuccess?.Invoke(data);
                    }
                    catch (Exception e)
                    {
                        string error = $"JSON解析失败: {e.Message}";
                        Debug.LogError($"[ApiClient] {error}");
                        onError?.Invoke(error);
                    }
                }
                else
                {
                    string error = $"请求失败: {request.error}";
                    Debug.LogError($"[ApiClient] {error}");
                    onError?.Invoke(error);
                }
            }
        }

        public void HealthCheck(Action<bool> callback)
        {
            StartCoroutine(HealthCheckCoroutine(callback));
        }

        private IEnumerator HealthCheckCoroutine(Action<bool> callback)
        {
            using (UnityWebRequest request = UnityWebRequest.Get($"{baseUrl}/health"))
            {
                request.timeout = 5;
                yield return request.SendWebRequest();
                callback?.Invoke(request.result == UnityWebRequest.Result.Success);
            }
        }

        #endregion
    }
}
