"""LLM 客户端模块 - 兼容 OpenAI API 协议"""
import httpx
import json
from typing import Optional, List
from .config import config


class LLMClient:
    """LLM API 客户端"""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=120.0)  # 增加到120秒
        return self._client
    
    @property
    def api_url(self) -> str:
        return config.llm.get("api_url", "https://api.deepseek.com/v1")
    
    @property
    def api_key(self) -> str:
        return config.llm.get("api_key", "")
    
    @property
    def model_name(self) -> str:
        return config.llm.get("model_name", "deepseek-chat")
    
    def _call_llm(self, system_prompt: str, user_prompt: str, timeout: float = None) -> Optional[str]:
        """调用 LLM API"""
        url = f"{self.api_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        try:
            if timeout:
                response = self.client.post(url, headers=headers, json=payload, timeout=timeout)
            else:
                response = self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return None
    
    def translate(self, title_en: str, description_en: str = None) -> dict:
        """翻译新闻标题"""
        system_prompt = """你是一个专业的技术新闻翻译助手。请将以下英文技术新闻标题翻译成中文。
要求：
1. 翻译准确、流畅
2. 保留专业术语
3. 只返回翻译后的标题，不要添加任何解释"""
        
        user_prompt = f"标题：{title_en}"
        
        result = self._call_llm(system_prompt, user_prompt)
        if result is None:
            return {"title_cn": title_en}
        
        return {"title_cn": result.strip()}
    
    def summarize_by_title_and_url(self, title_en: str, url: str) -> dict:
        """兜底策略：根据标题和URL生成英文摘要+中文摘要"""
        system_prompt = """你是一个技术新闻摘要助手。请根据新闻标题和来源网址，生成该新闻的摘要。

要求：
1. 根据标题和网址推断新闻内容，生成简洁的英文摘要（100-200词）
2. 将英文摘要翻译成中文，中文摘要要求500字左右
3. 保留关键技术信息和核心观点
4. 语义完整，不要截断

返回格式（严格按此格式）：
EN: 英文摘要内容
CN: 中文摘要内容"""
        
        user_prompt = f"新闻标题：{title_en}\n来源网址：{url}"
        
        result = self._call_llm(system_prompt, user_prompt)
        if result is None:
            return {"description_en": "", "description_cn": "暂无摘要"}
        
        # 解析返回结果
        import re
        en_match = re.search(r'EN:\s*(.+?)(?:\nCN:|$)', result, re.DOTALL)
        cn_match = re.search(r'CN:\s*(.+?)$', result, re.DOTALL)
        
        description_en = en_match.group(1).strip()[:500] if en_match else ""
        description_cn = cn_match.group(1).strip()[:500] if cn_match else "暂无摘要"
        
        return {
            "description_en": description_en,
            "description_cn": description_cn
        }
    
    def summarize_article_en(self, title_en: str, article_content: str) -> str:
        """生成文章英文摘要"""
        if not article_content or len(article_content.strip()) < 50:
            return "No summary available"
        
        content_preview = article_content[:3000]
        
        system_prompt = """You are a tech news summarizer. Read the following article and generate a concise English summary.

Requirements:
1. Summary should be 100-200 words
2. Capture the core content in English
3. Preserve key technical information
4. Be semantically complete, don't truncate
5. Return only the summary, no titles or formatting"""
        
        user_prompt = f"Article title: {title_en}\n\nArticle content: {content_preview}"
        
        result = self._call_llm(system_prompt, user_prompt)
        if result is None:
            return "No summary available"
        
        return result.strip()[:500]
    
    def summarize_article(self, title_en: str, article_content: str) -> str:
        """生成文章中文摘要"""
        if not article_content or len(article_content.strip()) < 50:
            return "暂无摘要"
        
        # 截取前 3000 字用于摘要
        content_preview = article_content[:3000]
        
        system_prompt = """你是一个技术新闻摘要助手。请阅读以下文章内容，生成一个简洁的中文摘要。

要求：
1. 摘要不超过 500 字
2. 用中文总结核心内容
3. 保留关键技术信息
4. 语义完整，不要截断
5. 只返回摘要，不要添加标题或其他格式"""
        
        user_prompt = f"文章标题：{title_en}\n\n文章内容：{content_preview}"
        
        result = self._call_llm(system_prompt, user_prompt)
        if result is None:
            return "暂无摘要"
        
        return result.strip()[:500]
    
    def translate_batch(self, news_list: List[dict]) -> List[dict]:
        """批量翻译新闻（一次调用翻译多条）"""
        if not news_list:
            return []
        
        # 构建批量翻译请求
        items_to_translate = []
        for i, news in enumerate(news_list):
            title = news.get("title_en", "")
            desc = news.get("description_en", "")
            # 截取摘要前300字用于翻译和总结
            desc_summary = desc[:300] if desc else "无摘要"
            items_to_translate.append(f"---{i+1}---\n标题: {title}\n原文: {desc_summary}")
        
        system_prompt = """你是一个技术新闻翻译助手。请将以下英文新闻翻译成中文。

对每条新闻，请：
1. 翻译标题为中文
2. 将原文总结为不超过300字的中文摘要

严格按以下格式返回（每条新闻之间空一行）：
---序号---
标题: 中文标题
摘要: 中文摘要（不超过300字）

注意：必须保留 ---序号--- 格式，标题和摘要必须是中文。"""
        
        user_prompt = "请翻译以下新闻：\n\n" + "\n\n".join(items_to_translate)
        
        result = self._call_llm(system_prompt, user_prompt)
        if result is None:
            # 翻译失败，返回原文
            return [{"title_cn": n.get("title_en"), "description_cn": n.get("description_en", "")[:300]} for n in news_list]
        
        # 解析批量翻译结果
        translations = []
        import re
        
        # 按 ---序号--- 分割
        parts = re.split(r'---(\d+)---', result)
        
        # parts[0] 是空或前言，parts[1] 是序号1，parts[2] 是内容1，以此类推
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                content = parts[i + 1]
                title_cn = ""
                desc_cn = ""
                
                # 提取标题
                title_match = re.search(r'标题[：:]\s*(.+?)(?:\n|$)', content)
                if title_match:
                    title_cn = title_match.group(1).strip()
                
                # 提取摘要
                desc_match = re.search(r'摘要[：:]\s*(.+?)(?:$)', content, re.DOTALL)
                if desc_match:
                    desc_cn = desc_match.group(1).strip()[:300]  # 限制300字
                
                if title_cn:
                    translations.append({"title_cn": title_cn, "description_cn": desc_cn})
        
        # 补齐缺失的翻译
        while len(translations) < len(news_list):
            idx = len(translations)
            translations.append({
                "title_cn": news_list[idx].get("title_en"),
                "description_cn": news_list[idx].get("description_en", "")[:300]
            })
        
        return translations[:len(news_list)]
    
    def extract_keywords_batch(self, news_list: List[dict]) -> List[List[str]]:
        """批量提取关键词（一次调用提取多条）"""
        if not news_list:
            return []
        
        # 构建批量提取请求
        items_to_analyze = []
        for i, news in enumerate(news_list):
            title = news.get("title_en", "")
            desc = news.get("description_en", "")
            items_to_analyze.append(f"{i+1}. {title} - {desc[:100] if desc else ''}")
        
        system_prompt = """你是一个技术新闻分析助手。请从以下新闻中提取技术关键词。
要求：
1. 每条新闻提取3-5个关键词
2. 返回格式：序号: [关键词1, 关键词2, ...]
3. 关键词应该是技术领域、模型名称、公司等
4. 只返回结果，不要添加解释"""
        
        user_prompt = "请提取关键词：\n\n" + "\n".join(items_to_analyze)
        
        result = self._call_llm(system_prompt, user_prompt)
        if result is None:
            return [[] for _ in news_list]
        
        # 解析结果
        all_keywords = []
        lines = result.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 提取序号和关键词
            import re
            match = re.match(r'(\d+)[.:：]\s*\[(.+?)\]', line)
            if match:
                keywords_str = match.group(2)
                keywords = [k.strip().strip("'\"") for k in keywords_str.split(",")]
                all_keywords.append(keywords[:5])
        
        # 补齐
        while len(all_keywords) < len(news_list):
            all_keywords.append([])
        
        return all_keywords[:len(news_list)]
    
    def analyze_feedback(self, feedback_text: str) -> dict:
        """分析文字反馈的情感和关键词"""
        system_prompt = """你是一个用户反馈分析助手。请分析用户的文字反馈，判断情感倾向并提取关键词。
要求：
1. 判断情感：正面(positive)或负面(negative)
2. 提取用户提到的关键词（技术领域、模型、概念等）
3. 返回JSON格式：{"sentiment": "positive/negative", "keywords": ["关键词1", "关键词2"]}
4. 只返回JSON，不要添加任何解释"""
        
        user_prompt = f"用户反馈：{feedback_text}"
        
        result = self._call_llm(system_prompt, user_prompt)
        if result is None:
            return {"sentiment": "neutral", "keywords": []}
        
        # 解析JSON
        try:
            analysis = json.loads(result)
            return {
                "sentiment": analysis.get("sentiment", "neutral"),
                "keywords": analysis.get("keywords", [])[:5]
            }
        except json.JSONDecodeError:
            return {"sentiment": "neutral", "keywords": []}


# 全局 LLM 客户端实例
llm_client = LLMClient()
