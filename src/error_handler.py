"""错误处理模块"""
from typing import Dict, Any
from fastapi import HTTPException


class ErrorHandler:
    """统一错误处理器"""
    
    def handle_hn_api_error(self, error: Exception) -> Dict[str, Any]:
        """处理 HN API 错误"""
        return {
            "success": False,
            "error_type": "hn_api_error",
            "message": f"获取新闻失败: {str(error)}",
            "suggestion": "请检查网络连接后重试"
        }
    
    def handle_llm_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """处理 LLM 调用错误"""
        return {
            "success": False,
            "error_type": "llm_error",
            "message": f"LLM 调用失败: {str(error)}",
            "context": context,
            "suggestion": "翻译或分析可能不完整，但不影响基本功能"
        }
    
    def handle_database_error(self, error: Exception) -> Dict[str, Any]:
        """处理数据库错误"""
        return {
            "success": False,
            "error_type": "database_error",
            "message": f"数据库操作失败: {str(error)}",
            "suggestion": "请检查数据库文件权限"
        }
    
    def raise_http_error(self, status_code: int, detail: str):
        """抛出 HTTP 异常"""
        raise HTTPException(status_code=status_code, detail=detail)


# 全局错误处理器实例
error_handler = ErrorHandler()
