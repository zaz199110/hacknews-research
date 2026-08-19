"""Test save config functionality"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto('http://localhost:8080')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    # Open config modal
    page.get_by_role("button", name="模型配置").click()
    time.sleep(0.5)
    
    # Read original model name
    original_model = page.locator('#config-model-name').input_value()
    print(f"Original model name: {original_model}")
    
    # Modify model name
    page.locator('#config-model-name').fill('mimo-v2.5-test')
    time.sleep(0.3)
    
    # Click save
    page.get_by_role("button", name="保存").click()
    time.sleep(1)
    
    # Handle alert dialog
    page.on('dialog', lambda dialog: dialog.accept())
    
    # Take screenshot after save
    page.screenshot(path='D:/opencode-project/LLM新闻日报/test_03_after_save.png', full_page=True)
    print("Clicked save button")
    
    # Check if modal closed
    modal = page.locator('#config-modal')
    is_visible = modal.is_visible()
    print(f"Modal visible after save: {is_visible}")
    
    # Re-open modal to verify change persisted
    page.get_by_role("button", name="模型配置").click()
    time.sleep(0.5)
    
    new_model = page.locator('#config-model-name').input_value()
    print(f"Model name after save: {new_model}")
    
    # Restore original value
    page.locator('#config-model-name').fill(original_model)
    page.get_by_role("button", name="保存").click()
    time.sleep(0.5)
    
    page.screenshot(path='D:/opencode-project/LLM新闻日报/test_04_reverted.png', full_page=True)
    
    browser.close()
    
    print("\n=== Test Result ===")
    if new_model == 'mimo-v2.5-test':
        print("PASS: Save functionality works!")
    else:
        print(f"FAIL: Expected 'mimo-v2.5-test', got '{new_model}'")
