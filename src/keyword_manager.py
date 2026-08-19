"""关键词管理模块"""
from typing import List, Dict, Optional
from .storage import storage
from .llm_client import llm_client


class KeywordManager:
    """关键词池管理器"""
    
    def get_all_keywords(self) -> List[Dict]:
        """获取所有关键词（按得分排序）"""
        return storage.get_all_keywords()
    
    def update_keyword(self, keyword_id: int, score: float) -> bool:
        """更新关键词得分"""
        try:
            storage.set_keyword_score(keyword_id, score)
            return True
        except Exception as e:
            print(f"更新关键词失败: {e}")
            return False
    
    def delete_keyword(self, keyword_id: int) -> bool:
        """删除关键词"""
        try:
            storage.delete_keyword(keyword_id)
            return True
        except Exception as e:
            print(f"删除关键词失败: {e}")
            return False
    
    def get_feedback_stats(self) -> Dict:
        """获取反馈统计"""
        return storage.get_feedback_stats()
    
    def normalize_keyword(self, keyword: str) -> str:
        """归一化关键词（使用 LLM 语义归一化）
        
        将语义相似的关键词合并为统一形式，例如：
        - "LLMs" -> "LLM"
        - "Language Models" -> "LLM"
        - "GPT-4o" -> "GPT-4o"
        
        优先使用缓存，避免重复调用 LLM
        """
        # 1. 检查缓存
        cached = storage.get_normalized_keyword(keyword)
        if cached:
            return cached
        
        # 2. 简单规则预处理（快速、无成本）
        normalized = self._simple_normalize(keyword)
        if normalized != keyword:
            storage.set_normalized_keyword(keyword, normalized)
            return normalized
        
        # 3. 使用 LLM 进行语义归一化
        normalized = self._llm_normalize(keyword)
        
        # 4. 缓存结果
        storage.set_normalized_keyword(keyword, normalized)
        
        return normalized
    
    def _simple_normalize(self, keyword: str) -> str:
        """简单规则归一化（无 LLM 调用）"""
        # 转小写
        kw = keyword.strip()
        
        # 常见缩写归一化
        normalize_map = {
            "llms": "LLM",
            "llm": "LLM",
            "gpts": "GPT",
            "gpt": "GPT",
            "ais": "AI",
            "ai": "AI",
            "apis": "API",
            "api": "API",
            "mcps": "MCP",
            "mcp": "MCP",
        }
        
        # 精确匹配
        if kw.lower() in normalize_map:
            return normalize_map[kw.lower()]
        
        # 大写保留原样（如 GPT-4, LLM）
        if kw.isupper() or (kw.isupper() and any(c.isdigit() for c in kw)):
            return kw
        
        return kw
    
    def _llm_normalize(self, keyword: str) -> str:
        """使用 LLM 进行语义归一化"""
        system_prompt = """你是一个技术术语归一化助手。请将给定的技术关键词归一化为最标准、最常用的形式。

要求：
1. 将语义相同的词合并（如 "LLMs" 和 "Language Models" 都归一化为 "LLM"）
2. 保留专有名词的标准写法（如 "GPT-4o" 保持不变）
3. 只返回归一化后的关键词，不要添加任何解释
4. 如果关键词已经是标准形式，直接返回原词"""
        
        user_prompt = f"请归一化以下关键词：{keyword}"
        
        result = llm_client._call_llm(system_prompt, user_prompt, timeout=30.0)
        if result is None:
            return keyword
        
        # 清理返回结果
        normalized = result.strip()
        # 去除可能的引号
        normalized = normalized.strip('"').strip("'")
        
        return normalized if normalized else keyword
    
    def normalize_keywords_batch(self, keywords: List[str]) -> List[str]:
        """批量归一化关键词"""
        return [self.normalize_keyword(kw) for kw in keywords]


# 全局关键词管理器实例
keyword_manager = KeywordManager()
