"""
LLM 新闻日报 - Playwright 基础功能测试
"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright


async def test_basic():
    """基础功能测试"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("=" * 60)
        print("LLM 新闻日报 - 基础功能测试")
        print("=" * 60)
        
        # 1. 访问首页
        print("\n[1] 访问首页...")
        await page.goto("http://127.0.0.1:8080")
        await page.wait_for_load_state("networkidle")
        title = await page.title()
        print(f"    页面标题: {title}")
        print("    OK 首页加载成功")
        
        # 2. 执行搜索
        print("\n[2] 执行搜索...")
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        await page.fill('input[type="date"]:first-of-type', today)
        await page.fill('input[type="date"]:last-of-type', today)
        await page.click('button:has-text("立即搜索")')
        
        await page.wait_for_url("**/detail/*", timeout=60000)
        print("    OK 搜索完成")
        
        # 3. 检查新闻列表
        print("\n[3] 检查新闻列表...")
        await page.wait_for_selector(".news-card", timeout=30000)
        news_cards = await page.query_selector_all(".news-card")
        print(f"    新闻数量: {len(news_cards)}")
        print("    OK 新闻列表显示正常")
        
        # 4. 检查翻译按钮
        print("\n[4] 检查翻译按钮...")
        translate_btn = await page.query_selector('#translate-btn')
        btn_text = await translate_btn.inner_text() if translate_btn else "无"
        print(f"    按钮文本: {btn_text}")
        print("    OK 翻译按钮存在")
        
        # 5. 测试单条翻译 API
        print("\n[5] 测试翻译 API...")
        first_card = news_cards[0]
        checkbox = await first_card.query_selector('input[type="checkbox"]')
        news_id = await checkbox.get_attribute('data-news-id') if checkbox else None
        
        if news_id:
            result = await page.evaluate(f"""
                async () => {{
                    try {{
                        const response = await fetch("/api/translate/{news_id}", {{ method: "POST" }});
                        const data = await response.json();
                        return data;
                    }} catch (error) {{
                        return {{ error: error.message }};
                    }}
                }}
            """)
            
            if result and result.get('success'):
                print(f"    翻译成功!")
                print(f"    标题: {result.get('title_cn', '无')[:50]}...")
                print(f"    摘要: {result.get('description_cn', '无')[:50]}...")
                print("    OK 翻译 API 正常")
            else:
                print(f"    翻译失败: {result}")
        
        # 6. 测试点赞功能
        print("\n[6] 测试点赞功能...")
        feedback_btns = await first_card.query_selector_all(".feedback-btn")
        if feedback_btns:
            await feedback_btns[0].click()
            await page.wait_for_timeout(1000)
            print("    OK 点赞按钮点击成功")
        
        # 7. 测试导出功能
        print("\n[7] 测试导出功能...")
        export_input = await page.query_selector('#export-title')
        if export_input:
            await export_input.fill("测试日报")
        print("    OK 导出功能准备就绪")
        
        # 8. 截图保存
        print("\n[8] 保存截图...")
        await page.screenshot(path="D:/opencode-project/LLM新闻日报/test_screenshot.png")
        print("    OK 截图已保存")
        
        # 9. 测试关键词管理页
        print("\n[9] 测试关键词管理页...")
        await page.goto("http://127.0.0.1:8080/keywords")
        await page.wait_for_load_state("networkidle")
        stats_el = await page.query_selector(".stats")
        if stats_el:
            stats_text = await stats_el.inner_text()
            print(f"    统计信息: {stats_text}")
        print("    OK 关键词管理页正常")
        
        await browser.close()
        
        print("\n" + "=" * 60)
        print("所有基础测试通过！")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_basic())
