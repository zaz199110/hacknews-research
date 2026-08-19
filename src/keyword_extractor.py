"""关键词提取模块"""
import json
from typing import List, Dict
from .llm_client import llm_client
from .storage import storage


class KeywordExtractor:
    """关键词提取器"""
    
    def extract_from_news(self, news_id: int, title: str, description: str = None) -> List[str]:
        """从新闻内容提取关键词并更新数据库"""
        # 调用 LLM 提取关键词
        keywords = llm_client.extract_keywords(title, description)
        
        if keywords:
            # 更新数据库中的关键词
            storage.update_news_keywords(news_id, keywords)
        
        return keywords
    
    def extract_from_feedback(self, feedback_text: str) -> Dict:
        """从文字反馈中提取关键词和情感"""
        # 调用 LLM 分析反馈
        analysis = llm_client.analyze_feedback(feedback_text)
        
        sentiment = analysis.get("sentiment", "neutral")
        keywords = analysis.get("keywords", [])
        
        # 更新关键词池
        delta = config.feedback.get("text_feedback_weight", 2)
        for keyword in keywords:
            if sentiment == "positive":
                storage.update_keyword_score(keyword, delta)
            elif sentiment == "negative":
                storage.update_keyword_score(keyword, -delta)
        
        return {
            "sentiment": sentiment,
            "keywords": keywords
        }


# 导入 config
from .config import config

# 全局关键词提取器实例
keyword_extractor = KeywordExtractor()
