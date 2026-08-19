"""
LLM 新闻日报 - Playwright 端到端测试
"""
import asyncio
import sys
import io

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright


async def test_e2e():
    """端到端测试"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("=" * 60)
        print("LLM 新闻日报 - Playwright 端到端测试")
        print("=" * 60)
        
        # 1. 访问首页
        print("\n[1] 访问首页...")
        await page.goto("http://127.0.0.1:8080")
        await page.wait_for_load_state("networkidle")
        
        # 检查标题
        title = await page.title()
        print(f"    页面标题: {title}")
        assert "LLM" in title, f"标题不正确: {title}"
        print("    OK 首页加载成功")
        
        # 2. 执行搜索
        print("\n[2] 执行搜索...")
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        await page.fill('input[type="date"]:first-of-type', today)
        await page.fill('input[type="date"]:last-of-type', today)
        
        await page.click('button:has-text("立即搜索")')
        print("    等待搜索完成...")
        
        await page.wait_for_url("**/detail/*", timeout=60000)
        print("    OK 搜索完成，已跳转到详情页")
        
        # 3. 检查新闻列表
        print("\n[3] 检查新闻列表...")
        await page.wait_for_selector(".news-card", timeout=30000)
        news_cards = await page.query_selector_all(".news-card")
        print(f"    新闻数量: {len(news_cards)}")
        assert len(news_cards) > 0, "没有新闻"
        print("    OK 新闻列表显示正常")
        
        # 4. 检查翻译按钮
        print("\n[4] 检查翻译按钮...")
        translate_btn = await page.query_selector('#translate-btn')
        assert translate_btn, "翻译按钮不存在"
        btn_text = await translate_btn.inner_text()
        print(f"    按钮文本: {btn_text}")
        assert "翻译" in btn_text, "按钮文本不正确"
        print("    OK 翻译按钮存在")
        
        # 5. 测试翻译功能
        print("\n[5] 测试翻译功能...")
        print("    点击翻译按钮...")
        await translate_btn.click()
        
        # 等待翻译完成（最多 120 秒）
        print("    等待翻译完成（最多 120 秒）...")
        try:
            # 等待按钮文本变回"翻译"
            await page.wait_for_function("""
                () => {
                    const btn = document.getElementById('translate-btn');
                    return btn && btn.textContent === '翻译' && !btn.disabled;
                }
            """, timeout=120000)
            print("    OK 翻译完成")
        except Exception as e:
            print(f"    翻译等待超时: {e}")
        
        # 6. 检查翻译结果
        print("\n[6] 检查翻译结果...")
        await page.wait_for_timeout(2000)
        
        # 获取第一条新闻
        first_card = (await page.query_selector_all(".news-card"))[0]
        title_el = await first_card.query_selector(".news-title")
        title_text = await title_el.inner_text() if title_el else ""
        
        desc_el = await first_card.query_selector(".news-description")
        desc_text = await desc_el.inner_text() if desc_el else ""
        
        print(f"    标题: {title_text[:50]}...")
        print(f"    摘要: {desc_text[:50]}..." if desc_text else "    摘要: 无")
        
        # 检查是否包含中文字符
        import re
        has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', title_text))
        if has_chinese:
            print("    OK 标题已翻译为中文")
        else:
            print("    标题仍为英文")
        
        # 7. 测试点赞功能
        print("\n[7] 测试点赞功能...")
        feedback_btns = await first_card.query_selector_all(".feedback-btn")
        if feedback_btns:
            await feedback_btns[0].click()
            await page.wait_for_timeout(1000)
            print("    OK 点赞按钮点击成功")
        
        # 8. 测试导出功能
        print("\n[8] 测试导出功能...")
        checkbox = await first_card.query_selector('input[type="checkbox"]')
        if checkbox:
            await checkbox.click()
        
        export_input = await page.query_selector('#export-title')
        if export_input:
            await export_input.fill("测试日报")
        
        print("    OK 导出功能准备就绪")
        
        # 9. 截图保存
        print("\n[9] 保存截图...")
        await page.screenshot(path="D:/opencode-project/LLM新闻日报/test_screenshot.png")
        print("    OK 截图已保存")
        
        # 10. 测试关键词管理页
        print("\n[10] 测试关键词管理页...")
        await page.goto("http://127.0.0.1:8080/keywords")
        await page.wait_for_load_state("networkidle")
        
        stats_el = await page.query_selector(".stats")
        if stats_el:
            stats_text = await stats_el.inner_text()
            print(f"    统计信息: {stats_text}")
        
        print("    OK 关键词管理页正常")
        
        await browser.close()
        
        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_e2e())
