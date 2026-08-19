"""快速测试翻译 API"""
import asyncio
from playwright.async_api import async_playwright


async def test_translate():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 访问详情页
        await page.goto("http://127.0.0.1:8080/detail/23")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_selector(".news-card", timeout=10000)
        
        # 测试翻译 API
        result = await page.evaluate("""
            async () => {
                try {
                    const response = await fetch("/api/translate/1426", { method: "POST" });
                    const data = await response.json();
                    return data;
                } catch (error) {
                    return { error: error.message };
                }
            }
        """)
        
        print(f"翻译结果: {result}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_translate())
