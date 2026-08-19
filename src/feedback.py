"""反馈处理模块"""
import json
from typing import Dict, Optional
from .storage import storage
from .llm_client import llm_client
from .keyword_manager import keyword_manager


class FeedbackHandler:
    """反馈处理器"""
    
    def quick_feedback(self, news_id: int, status: str) -> Dict:
        """处理快捷反馈（👍/👎）
        
        从英文摘要中用 LLM 提取 3 个最重要的关键词
        支持切换：如果当前状态与点击状态相同，则取消反馈
        """
        # 获取新闻
        news = storage.get_news(news_id)
        if not news:
            return {"success": False, "message": "新闻不存在"}
        
        # 获取英文内容
        title_en = news.get("title_en", "")
        desc_en = news.get("description_en", "")
        content = f"{title_en}\n{desc_en}" if desc_en else title_en
        
        # 用 LLM 提取 3 个最重要的关键词
        raw_keywords = self._extract_keywords_with_llm(content)
        
        # 归一化关键词（语义去重）
        keywords = keyword_manager.normalize_keywords_batch(raw_keywords)
        
        # 检查是否需要切换状态（点击相同状态则取消）
        current_status = news.get("feedback_status")
        if current_status == status:
            # 取消反馈：将得分反转
            delta = -1 if status == "positive" else 1
            new_status = None
        else:
            # 新增或切换反馈
            delta = 1 if status == "positive" else -1
            new_status = status
        
        # 更新关键词池得分
        for keyword in keywords:
            storage.update_keyword_score(keyword, delta)
        
        # 更新新闻反馈状态
        storage.update_news_feedback_status(news_id, new_status)
        
        return {
            "success": True,
            "message": f"反馈已记录: {new_status}" if new_status else "反馈已取消",
            "keywords": keywords,
            "raw_keywords": raw_keywords,
            "delta": delta,
            "feedback_status": new_status
        }
    
    def _extract_keywords_with_llm(self, content: str) -> list:
        """用 LLM 提取 3 个最重要的英文关键词"""
        if not content or len(content.strip()) < 10:
            return []
        
        system_prompt = """你是一个技术新闻分析助手。请从以下英文内容中提取 3 个最重要的英文关键词。

要求：
1. 关键词必须是英文
2. 关键词应该是技术领域、模型名称、公司、概念等
3. 只返回 JSON 数组格式，例如: ["keyword1", "keyword2", "keyword3"]
4. 不要添加任何解释"""
        
        user_prompt = f"请提取 3 个最重要的关键词：\n\n{content[:1000]}"
        
        result = llm_client._call_llm(system_prompt, user_prompt, timeout=30.0)
        if result is None:
            return []
        
        # 解析 JSON 数组
        try:
            # 尝试提取 JSON 部分
            import re
            json_match = re.search(r'\[.*?\]', result)
            if json_match:
                keywords = json.loads(json_match.group())
                if isinstance(keywords, list):
                    return keywords[:3]
        except Exception as e:
            print(f"解析关键词失败: {e}")
        
        return []
    
    def text_feedback(self, news_id: int, content: str) -> Dict:
        """处理文字反馈
        """
        # 获取新闻
        news = storage.get_news(news_id)
        if not news:
            return {"success": False, "message": "新闻不存在"}
        
        # 从用户输入中提取关键词
        keywords = self._extract_keywords_with_llm(content)
        
        # 保存文字反馈记录
        feedback_id = storage.create_feedback(
            news_id=news_id,
            content=content,
            extracted_keywords=keywords
        )
        
        return {
            "success": True,
            "message": "文字反馈已记录",
            "feedback_id": feedback_id,
            "keywords": keywords
        }


# 全局反馈处理器实例
feedback_handler = FeedbackHandler()
