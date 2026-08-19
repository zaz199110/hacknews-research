"""测试翻译 API"""
import requests
import json

# 测试翻译 API
url = 'http://127.0.0.1:8080/api/translate/1630'
try:
    response = requests.post(url, timeout=60)
    data = response.json()
    print("翻译成功!")
    print("标题:", data.get("title_cn", "无"))
    print("摘要:", data.get("description_cn", "无")[:100] + "...")
except Exception as e:
    print("翻译失败:", e)
