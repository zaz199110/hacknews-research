"""搜索功能测试"""
import pytest
import requests
from datetime import datetime, timedelta


class TestSearch:
    """搜索功能测试"""
    
    def test_get_last_search(self, api_base):
        """TC-01-01: 获取上次搜索条件"""
        response = requests.get(f"{api_base}/last-search")
        assert response.status_code == 200
        
        data = response.json()
        assert "keywords" in data
        assert "logic" in data
        assert "start_date" in data
        assert "end_date" in data
        
        # 验证关键词列表不为空
        assert len(data["keywords"]) > 0
    
    def test_create_search(self, api_base):
        """TC-01-05: 执行搜索"""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        payload = {
            "keywords": ["LLM"],
            "logic": "OR",
            "start_date": yesterday,
            "end_date": today
        }
        
        response = requests.post(f"{api_base}/search", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "session_id" in data
        assert "news_count" in data
        assert "news_list" in data
        
        return data["session_id"]
    
    def test_get_sessions(self, api_base):
        """TC-07-01: 获取搜索历史"""
        response = requests.get(f"{api_base}/sessions")
        assert response.status_code == 200
        
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
    
    def test_get_session_detail(self, api_base):
        """TC-07-02: 获取搜索会话详情"""
        # 先创建一个搜索
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
        
        # 获取详情
        response = requests.get(f"{api_base}/sessions/{session_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == session_id
    
    def test_get_session_news(self, api_base):
        """TC-02-01: 获取搜索结果"""
        # 先创建一个搜索
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
        
        # 获取新闻列表
        response = requests.get(f"{api_base}/sessions/{session_id}/news")
        assert response.status_code == 200
        
        data = response.json()
        assert "news_list" in data
        
        # 如果有新闻，验证字段
        if data["news_list"]:
            news = data["news_list"][0]
            assert "id" in news
            assert "title_en" in news
            assert "score" in news
    
    def test_delete_session(self, api_base):
        """TC-07-03: 删除搜索会话"""
        # 先创建一个搜索
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
        
        # 删除
        response = requests.delete(f"{api_base}/sessions/{session_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # 验证已删除
        get_resp = requests.get(f"{api_base}/sessions/{session_id}")
        assert get_resp.status_code == 404
