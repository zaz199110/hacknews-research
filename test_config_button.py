"""Test the 模型配置 button functionality"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Navigate to the app
    page.goto('http://localhost:8080')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    # Take screenshot of initial state
    page.screenshot(path='D:/opencode-project/LLM新闻日报/test_01_initial.png', full_page=True)
    print("1. Initial page loaded")
    
    # Check if the button exists (use role to avoid matching modal title)
    config_btn = page.get_by_role("button", name="模型配置")
    print(f"2. Button found: {config_btn.count() > 0}")
    
    # Click the config button
    config_btn.click()
    time.sleep(0.5)
    
    # Take screenshot after click
    page.screenshot(path='D:/opencode-project/LLM新闻日报/test_02_after_click.png', full_page=True)
    print("3. Clicked config button")
    
    # Check if modal is visible
    modal = page.locator('#config-modal')
    is_visible = modal.is_visible()
    print(f"4. Modal visible: {is_visible}")
    
    # Check modal display style
    display_style = modal.evaluate('el => window.getComputedStyle(el).display')
    print(f"5. Modal display style: {display_style}")
    
    # Check if config fields are populated
    provider = page.locator('#config-provider').input_value()
    api_key = page.locator('#config-api-key').input_value()
    api_url = page.locator('#config-api-url').input_value()
    model_name = page.locator('#config-model-name').input_value()
    
    print(f"6. Provider: {provider}")
    print(f"7. API Key: {'***' if api_key else '(empty)'}")
    print(f"8. API URL: {api_url}")
    print(f"9. Model Name: {model_name}")
    
    # Check console errors
    console_errors = []
    page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
    
    browser.close()
    
    print("\n=== Test Result ===")
    if is_visible and provider:
        print("PASS: Modal opens and loads config")
    else:
        print("FAIL: Modal or config loading issue")
