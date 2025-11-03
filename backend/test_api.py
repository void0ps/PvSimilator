#!/usr/bin/env python3
"""
测试气象数据API
"""

import requests
import json

# 测试气象数据API
response = requests.get('http://localhost:8000/api/v1/weather/data/?limit=5')
print(f'状态码: {response.status_code}')

if response.status_code == 200:
    data = response.json()
    print(f'数据总数: {data["data_count"]}')
    print('前5条气象数据:')
    for i, item in enumerate(data['weather_data'][:5]):
        print(f'{i+1}. 时间: {item["timestamp"]}, 温度: {item["temperature"]}°C, 总辐射: {item["ghi"]} W/m²')
else:
    print(f'错误: {response.text}')