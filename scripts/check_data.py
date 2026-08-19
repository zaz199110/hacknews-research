"""调查摘要缺失原因"""
import sqlite3

# 连接数据库
conn = sqlite3.connect('D:/opencode-project/LLM新闻日报/data/news.db')
conn.row_factory = sqlite3.Row

# 查询最近的新闻
cursor = conn.cursor()
cursor.execute('SELECT id, title_en, title_cn, description_en, description_cn, url FROM news ORDER BY id DESC LIMIT 10')

print("=" * 80)
print("新闻数据调查")
print("=" * 80)

for row in cursor.fetchall():
    news_id = row['id']
    title_en = row['title_en'] or '无'
    title_cn = row['title_cn'] or '无'
    desc_en = row['description_en'] or '无'
    desc_cn = row['description_cn'] or '无'
    url = row['url'] or '无'
    
    print(f"\n[新闻 {news_id}]")
    print(f"  英文标题: {title_en[:60]}...")
    print(f"  中文标题: {title_cn[:60] if title_cn != '无' else '未翻译'}")
    print(f"  英文描述: {desc_en[:60] if desc_en != '无' else '无描述'}...")
    print(f"  中文描述: {desc_cn[:60] if desc_cn != '无' else '未翻译'}...")
    print(f"  URL: {url[:60]}...")
    
    # 分析问题
    issues = []
    if title_cn == '无':
        issues.append("未翻译标题")
    if desc_cn == '无':
        issues.append("未翻译摘要")
    if desc_en == '无':
        issues.append("原文无描述")
    
    if issues:
        print(f"  问题: {', '.join(issues)}")

conn.close()
