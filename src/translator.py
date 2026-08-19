"""翻译模块"""
from typing import Dict, Optional
from .llm_client import llm_client
from .storage import storage


class Translator:
    """新闻翻译器"""
    
    def translate_news(self, news_id: int, title_en: str, description_en: str = None) -> Dict:
        """翻译新闻并更新数据库"""
        # 调用 LLM 翻译
        result = llm_client.translate(title_en, description_en)
        
        title_cn = result.get("title_cn", title_en)
        description_cn = result.get("description_cn", description_en)
        
        # 更新数据库
        storage.update_news_translation(news_id, title_cn, description_cn)
        
        return {
            "title_cn": title_cn,
            "description_cn": description_cn
        }
    
    def translate_batch(self, news_list: list) -> list:
        """批量翻译新闻"""
        results = []
        for news in news_list:
            news_id = news.get("id")
            title_en = news.get("title_en", "")
            description_en = news.get("description_en", "")
            
            if news_id and title_en:
                result = self.translate_news(news_id, title_en, description_en)
                news.update(result)
            
            results.append(news)
        
        return results


# 全局翻译器实例
translator = Translator()
