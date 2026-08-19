"""关键词管理测试"""
import pytest
import requests


class TestKeywords:
    """关键词管理测试"""
    
    def test_get_keywords(self, api_base):
        """TC-06-01: 获取关键词列表"""
        response = requests.get(f"{api_base}/keywords")
        assert response.status_code == 200
        
        data = response.json()
        assert "keywords" in data
        assert "stats" in data
        assert isinstance(data["keywords"], list)
    
    def test_get_feedback_stats(self, api_base):
        """TC-06-02: 获取反馈统计"""
        response = requests.get(f"{api_base}/keywords")
        assert response.status_code == 200
        
        data = response.json()
        stats = data["stats"]
        assert "total" in stats
        assert "positive" in stats
        assert "negative" in stats
    
    def test_update_keyword(self, api_base):
        """TC-06-03: 编辑关键词"""
        # 先获取关键词列表
        response = requests.get(f"{api_base}/keywords")
        keywords = response.json().get("keywords", [])
        
        if not keywords:
            pytest.skip("没有可编辑的关键词")
        
        keyword_id = keywords[0]["id"]
        new_score = 10.0
        
        payload = {"score": new_score}
        
        response = requests.put(f"{api_base}/keywords/{keyword_id}", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
    
    def test_delete_keyword(self, api_base):
        """TC-06-04: 删除关键词"""
        # 先获取关键词列表
        response = requests.get(f"{api_base}/keywords")
        keywords = response.json().get("keywords", [])
        
        if not keywords:
            pytest.skip("没有可删除的关键词")
        
        keyword_id = keywords[0]["id"]
        
        response = requests.delete(f"{api_base}/keywords/{keyword_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # 验证已删除
        response = requests.get(f"{api_base}/keywords")
        keywords = response.json().get("keywords", [])
        assert not any(kw["id"] == keyword_id for kw in keywords)
