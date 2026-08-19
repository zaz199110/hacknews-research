"""配置管理模块"""
import json
import os
from pathlib import Path


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.json"
        self.config_path = Path(config_path)
        self._config = None
    
    @property
    def config(self) -> dict:
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def reload(self):
        """重新加载配置"""
        self._config = None
    
    @property
    def llm(self) -> dict:
        return self.config.get("llm", {})
    
    @property
    def hackernews(self) -> dict:
        return self.config.get("hackernews", {})
    
    @property
    def default_search(self) -> dict:
        return self.config.get("default_search", {})
    
    @property
    def web(self) -> dict:
        return self.config.get("web", {})
    
    @property
    def feedback(self) -> dict:
        return self.config.get("feedback", {})
    
    @property
    def decay(self) -> dict:
        return self.config.get("decay", {})


# 全局配置实例
config = Config()
