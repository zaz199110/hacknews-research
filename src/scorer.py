"""评分计算模块"""
import json
from typing import List, Dict
from .storage import storage


class Scorer:
    """新闻评分计算器"""
    
    def __init__(self):
        # 评分权重配置
        self.hn_weight = 0.6  # HN 点赞数权重
        self.preference_weight = 0.4  # 偏好池权重
    
    def calculate_preference_score(self, keywords: List[str]) -> float:
        """计算偏好池打分"""
        if not keywords:
            return 0.0
        
        total_score = 0.0
        for keyword in keywords:
            score = storage.get_keyword_score(keyword)
            total_score += score
        
        return total_score
    
    def calculate_news_score(self, points: int, keywords: List[str]) -> float:
        """计算新闻最终得分
        
        公式：最终得分 = HN 点赞数 × 0.6 + 偏好池打分 × 0.4
        """
        preference_score = self.calculate_preference_score(keywords)
        
        # HN 点赞数直接使用，偏好池打分求和
        final_score = points * self.hn_weight + preference_score * self.preference_weight
        
        return round(final_score, 2)
    
    def calculate_news_score_with_details(self, points: int, keywords: List[str]) -> Dict:
        """计算新闻得分并返回详细信息"""
        preference_score = self.calculate_preference_score(keywords)
        final_score = points * self.hn_weight + preference_score * self.preference_weight
        
        # 构建推荐原因
        reason_parts = []
        for keyword in keywords:
            score = storage.get_keyword_score(keyword)
            if score != 0:
                sign = "+" if score > 0 else ""
                reason_parts.append(f"{keyword}({sign}{int(score)})")
        
        return {
            "score": round(final_score, 2),
            "hn_score": points,
            "preference_score": round(preference_score, 2),
            "reason": " + ".join(reason_parts) if reason_parts else "无偏好数据"
        }
    
    def rank_news_list(self, news_list: List[Dict]) -> List[Dict]:
        """对新闻列表进行评分和排序"""
        for news in news_list:
            keywords = json.loads(news.get("content_keywords", "[]")) if isinstance(news.get("content_keywords"), str) else news.get("content_keywords", [])
            news["score"] = self.calculate_news_score(news.get("points", 0), keywords)
        
        # 按得分降序排序
        news_list.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return news_list


# 全局评分器实例
scorer = Scorer()
