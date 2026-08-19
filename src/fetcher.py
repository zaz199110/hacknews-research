"""HN API 采集模块"""
import httpx
from datetime import datetime
from typing import List, Dict, Optional
from .config import config


class Fetcher:
    """HackerNews API 采集器"""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client
    
    @property
    def api_url(self) -> str:
        return config.hackernews.get("api_url", "https://hn.algolia.com/api/v1/search")
    
    @property
    def hits_per_page(self) -> int:
        return config.hackernews.get("hits_per_page", 100)
    
    @property
    def tags(self) -> str:
        return config.hackernews.get("tags", "story")
    
    def _build_query(self, keywords: List[str], logic: str) -> str:
        """构造搜索查询字符串"""
        if not keywords:
            return "LLM"
        
        if len(keywords) == 1:
            return keywords[0]
        
        # 使用 OR 或 AND 连接关键词
        separator = " OR " if logic.upper() == "OR" else " AND "
        return separator.join(keywords)
    
    def _date_to_timestamp(self, date_str: str) -> int:
        """将日期字符串转换为时间戳"""
        # 支持多种日期格式
        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return int(dt.timestamp())
            except ValueError:
                continue
        # 默认返回当前时间戳
        return int(datetime.now().timestamp())
    
    def fetch_news(self, keywords: List[str], logic: str, 
                   start_date: str, end_date: str) -> List[Dict]:
        """从 HN API 获取新闻"""
        query = self._build_query(keywords, logic)
        start_timestamp = self._date_to_timestamp(start_date)
        # 结束日期设为当天 23:59:59
        end_timestamp = self._date_to_timestamp(end_date) + 86399
        
        params = {
            "query": query,
            "tags": self.tags,
            "hitsPerPage": self.hits_per_page,
            "numericFilters": f"created_at_i>{start_timestamp},created_at_i<{end_timestamp}"
        }
        
        try:
            response = self.client.get(self.api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            hits = data.get("hits", [])
            news_list = []
            
            for hit in hits:
                news_item = {
                    "object_id": hit.get("objectID", ""),
                    "title_en": hit.get("title", ""),
                    "description_en": hit.get("story_text") or hit.get("comment_text") or "",
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "points": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "published_at": hit.get("created_at", "")
                }
                news_list.append(news_item)
            
            return news_list
            
        except httpx.HTTPError as e:
            print(f"HN API 请求失败: {e}")
            return []
        except Exception as e:
            print(f"解析 HN API 响应失败: {e}")
            return []


# 全局采集器实例
fetcher = Fetcher()
