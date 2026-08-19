"""反馈功能测试"""
import pytest
import requests
from datetime import datetime, timedelta


class TestFeedback:
    """反馈功能测试"""
    
    def _get_news_id(self, api_base):
        """获取一个新闻 ID"""
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
        
        if news_list:
            return news_list[0]["id"]
        return None
    
    def test_quick_feedback_positive(self, api_base):
        """TC-03-01: 点赞"""
        news_id = self._get_news_id(api_base)
        if not news_id:
            pytest.skip("没有可用的新闻")
        
        payload = {
            "news_id": news_id,
            "status": "positive"
        }
        
        response = requests.post(f"{api_base}/feedback/quick", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
    
    def test_quick_feedback_negative(self, api_base):
        """TC-03-02: 批评"""
        news_id = self._get_news_id(api_base)
        if not news_id:
            pytest.skip("没有可用的新闻")
        
        payload = {
            "news_id": news_id,
            "status": "negative"
        }
        
        response = requests.post(f"{api_base}/feedback/quick", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
    
    def test_text_feedback(self, api_base):
        """TC-04-01: 提交文字反馈"""
        news_id = self._get_news_id(api_base)
        if not news_id:
            pytest.skip("没有可用的新闻")
        
        payload = {
            "news_id": news_id,
            "content": "这个新闻很有用，关于Agent框架的"
        }
        
        response = requests.post(f"{api_base}/feedback/text", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "feedback_id" in data
