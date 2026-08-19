"""导出模块"""
import json
from datetime import datetime
from typing import List, Dict
from .storage import storage


class Exporter:
    """Markdown 导出器"""
    
    def export_markdown(self, news_ids: List[int], title: str) -> str:
        """导出选中的新闻为 Markdown 格式
        
        Args:
            news_ids: 要导出的新闻ID列表
            title: 文档标题
            
        Returns:
            Markdown 格式的字符串
        """
        # 获取新闻列表
        news_list = []
        for news_id in news_ids:
            news = storage.get_news(news_id)
            if news:
                news_list.append(news)
        
        # 构建 Markdown
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        md_lines = []
        
        # 标题
        md_lines.append(f"# {title}")
        md_lines.append("")
        md_lines.append(f"> 生成时间：{now} | 共 {len(news_list)} 条")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        
        # 每条新闻
        for i, news in enumerate(news_list, 1):
            title_cn = news.get("title_cn") or news.get("title_en", "无标题")
            description_cn = news.get("description_cn") or news.get("description_en") or "无摘要"
            url = news.get("url", "#")
            published_at = news.get("published_at", "未知时间")
            
            md_lines.append(f"## {i}. {title_cn}")
            md_lines.append("")
            md_lines.append(f"**摘要**：{description_cn}")
            md_lines.append("")
            md_lines.append(f"**来源**：HackerNews")
            md_lines.append("")
            md_lines.append(f"**链接**：[原文链接]({url})")
            md_lines.append("")
            md_lines.append(f"**时间**：{published_at}")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
        
        return "\n".join(md_lines)
    
    def get_export_content(self, news_ids: List[int], title: str) -> Dict:
        """获取导出内容（用于返回给前端）"""
        markdown_content = self.export_markdown(news_ids, title)
        
        return {
            "content": markdown_content,
            "filename": f"{title}.md",
            "news_count": len(news_ids)
        }


# 全局导出器实例
exporter = Exporter()
