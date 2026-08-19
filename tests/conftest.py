"""测试配置"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def base_url():
    """基础 URL"""
    return "http://localhost:8080"


@pytest.fixture(scope="session")
def api_base(base_url):
    """API 基础 URL"""
    return f"{base_url}/api"
