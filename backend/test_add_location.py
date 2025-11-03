#!/usr/bin/env python3
import requests
import json

# 测试添加位置
test_data = {
    'name': '测试位置3',
    'latitude': 31.2304,
    'longitude': 121.4737,
    'altitude': 10.0,
    'timezone': 'Asia/Shanghai',
    'country': '中国',
    'province': '上海',
    'city': '上海'
}

print("测试添加位置功能...")
print("请求数据:", json.dumps(test_data, ensure_ascii=False, indent=2))

try:
    response = requests.post('http://localhost:8000/api/v1/weather/locations/', json=test_data)
    print('状态码:', response.status_code)
    print('响应内容:', response.text)
    
    if response.status_code == 200:
        print('添加位置成功!')
        # 获取位置列表验证
        list_response = requests.get('http://localhost:8000/api/v1/weather/locations/')
        print('位置列表:', list_response.text)
    else:
        print('添加位置失败!')
        
except Exception as e:
    print('请求异常:', str(e))