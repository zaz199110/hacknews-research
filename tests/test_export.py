"""导出功能测试"""
import pytest
import requests
from datetime import datetime, timedelta


class TestExport:
    """导出功能测试"""
    
    def _get_news_ids(self, api_base, count=2):
        """获取新闻 ID 列表"""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        payload = {
            "keywords": ["LLM"],
            "logic": "OR",
            "start_date": yesterday,
            "end_date": today
        }
        
        search_resp = requests.post(f"{api_base}/search", json=payload)
        session_id = search_resp.json()["session_id"]
        
        news_resp = requests.get(f"{api_base}/sessions/{session_id}/news")
        news_list = news_resp.json().get("news_list", [])
        
        return [news["id"] for news in news_list[:count]]
    
    def test_export_markdown(self, api_base):
        """TC-05-03: 导出文件"""
        news_ids = self._get_news_ids(api_base)
        if not news_ids:
            pytest.skip("没有可用的新闻")
        
        payload = {
            "news_ids": news_ids,
            "title": "测试日报"
        }
        
        response = requests.post(f"{api_base}/export", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "content" in data
        assert "filename" in data
        assert "news_count" in data
        
        # 验证 Markdown 格式
        content = data["content"]
        assert "# 测试日报" in content
        assert "生成时间" in content
        assert "共" in content
        assert "条" in content
    
    def test_export_empty_selection(self, api_base):
        """TC-05-04: 未选择导出"""
        payload = {
            "news_ids": [],
            "title": "测试日报"
        }
        
        response = requests.post(f"{api_base}/export", json=payload)
        assert response.status_code == 400
    
    def test_export_no_title(self, api_base):
        """TC-05-05: 未输入名称"""
        news_ids = self._get_news_ids(api_base)
        if not news_ids:
            pytest.skip("没有可用的新闻")
        
        payload = {
            "news_ids": news_ids,
            "title": ""
        }
        
        response = requests.post(f"{api_base}/export", json=payload)
        assert response.status_code == 400
