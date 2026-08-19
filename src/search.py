"""搜索管理模块"""
import json
from typing import List, Dict, Optional
from datetime import datetime
from .storage import storage
from .fetcher import fetcher
from .scorer import scorer


class SearchManager:
    """搜索会话管理器"""
    
    def create_search(self, keywords: List[str], logic: str, 
                      start_date: str, end_date: str) -> Dict:
        """创建新的搜索会话并执行搜索
        
        Returns:
            包含搜索结果的字典
        """
        # 1. 创建搜索会话
        session_id = storage.create_session(keywords, logic, start_date, end_date)
        
        # 2. 从 HN API 获取新闻
        news_list = fetcher.fetch_news(keywords, logic, start_date, end_date)
        
        if not news_list:
            storage.update_session_result_count(session_id, 0)
            return {
                "session_id": session_id,
                "news_count": 0,
                "news_list": []
            }
        
        # 3. 去重（本次搜索内）
        unique_news = []
        seen_object_ids = set()
        for news in news_list:
            object_id = news.get("object_id")
            if object_id and object_id not in seen_object_ids:
                seen_object_ids.add(object_id)
                unique_news.append(news)
        
        # 4. 存储新闻（先不翻译，快速返回）
        all_stored_news = []
        
        for news in unique_news[:40]:  # 最多40条
            # 检查是否已存在
            if storage.news_exists_in_session(session_id, news["object_id"]):
                continue
            
            # 计算得分（使用 HN 点赞数，因为还没有偏好数据）
            score = news.get("points", 0) * 0.6  # 只用 HN 热度
            
            # 存储到数据库
            news_id = storage.create_news(
                search_id=session_id,
                object_id=news["object_id"],
                title_en=news["title_en"],
                description_en=news.get("description_en", "")[:300],
                url=news.get("url"),
                points=news.get("points", 0),
                comments=news.get("comments", 0),
                published_at=news.get("published_at"),
                content_keywords=[],
                score=score
            )
            
            all_stored_news.append(storage.get_news(news_id))
        
        # 5. 按得分排序，取 Top 10
        all_stored_news.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_news = all_stored_news[:10]
        
        # 6. 更新搜索会话结果数量
        storage.update_session_result_count(session_id, len(top_news))
        
        return {
            "session_id": session_id,
            "news_count": len(top_news),
            "news_list": top_news
        }
    
    def get_search_results(self, session_id: int, top_n: int = 10) -> List[Dict]:
        """获取搜索结果（按得分排序）"""
        news_list = storage.get_news_by_session(session_id)
        return news_list[:top_n]
    
    def delete_search(self, session_id: int) -> bool:
        """删除搜索会话"""
        try:
            storage.delete_session(session_id)
            return True
        except Exception as e:
            print(f"删除搜索会话失败: {e}")
            return False


# 全局搜索管理器实例
search_manager = SearchManager()
