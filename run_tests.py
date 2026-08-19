"""
LLM 新闻日报 - 自动化验收测试

运行方式：
    python run_tests.py

或者使用 pytest：
    pytest tests/ -v
"""
import subprocess
import sys
import time
import requests
from pathlib import Path


def check_server_running(base_url="http://localhost:8080"):
    """检查服务器是否运行"""
    try:
        response = requests.get(base_url, timeout=5)
        return response.status_code == 200
    except:
        return False


def start_server():
    """启动服务器"""
    print("启动服务器...")
    project_root = Path(__file__).parent
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.web_app:app", 
         "--host", "0.0.0.0", "--port", "8080"],
        cwd=str(project_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # 等待服务器启动
    print("等待服务器启动...")
    for i in range(30):
        time.sleep(1)
        if check_server_running():
            print("服务器启动成功!")
            return True
    
    print("服务器启动超时!")
    return False


def run_tests():
    """运行测试"""
    print("\n" + "="*60)
    print("LLM 新闻日报 - 自动化验收测试")
    print("="*60 + "\n")
    
    # 检查服务器
    if not check_server_running():
        if not start_server():
            print("无法启动服务器，测试终止")
            return False
    
    print("服务器运行中，开始测试...\n")
    
    # 运行 pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=str(Path(__file__).parent),
        capture_output=False
    )
    
    print("\n" + "="*60)
    if result.returncode == 0:
        print("所有测试通过!")
    else:
        print("部分测试失败，请检查输出")
    print("="*60 + "\n")
    
    return result.returncode == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
