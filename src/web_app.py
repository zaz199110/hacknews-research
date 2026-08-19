"""FastAPI 主应用"""
import json
import threading
import uuid
from datetime import datetime
from typing import List, Optional, Set, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .storage import storage
from .search import search_manager
from .feedback import feedback_handler
from .keyword_manager import keyword_manager
from .export import exporter
from .config import config


# 创建 FastAPI 应用
app = FastAPI(title="LLM 新闻日报", version="1.0.0")

# 异步翻译任务跟踪：session_id -> 正在翻译的 news_id 集合
_translating_tasks: dict[int, Set[int]] = {}
_translating_lock = threading.Lock()

# 异步反馈任务跟踪：task_id -> 任务状态
_feedback_tasks: dict[str, Dict[str, Any]] = {}
_feedback_lock = threading.Lock()

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


# ==================== 请求模型 ====================

class SearchRequest(BaseModel):
    keywords: List[str]
    logic: str = "OR"
    start_date: str
    end_date: str


class QuickFeedbackRequest(BaseModel):
    news_id: int
    status: str  # "positive" 或 "negative"


class TextFeedbackRequest(BaseModel):
    news_id: int
    content: str


class ExportRequest(BaseModel):
    news_ids: List[int]
    title: str


class KeywordUpdateRequest(BaseModel):
    score: float


class LLMConfigRequest(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    model_name: Optional[str] = None


# ==================== 页面路由 ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    """首页"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/detail/{session_id}", response_class=HTMLResponse)
async def detail_page(session_id: int):
    """详情页"""
    with open("static/detail.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/keywords", response_class=HTMLResponse)
async def keywords_page():
    """关键词管理页"""
    with open("static/keywords.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ==================== API 路由 ====================

@app.get("/api/sessions")
async def get_sessions():
    """获取所有搜索会话"""
    sessions = storage.get_all_sessions()
    return {"sessions": sessions}


@app.post("/api/search")
async def create_search(request: SearchRequest):
    """创建新搜索"""
    result = search_manager.create_search(
        keywords=request.keywords,
        logic=request.logic,
        start_date=request.start_date,
        end_date=request.end_date
    )
    return result


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int):
    """获取搜索会话详情"""
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="搜索会话不存在")
    return session


@app.get("/api/sessions/{session_id}/news")
async def get_session_news(session_id: int):
    """获取搜索结果"""
    news_list = search_manager.get_search_results(session_id)
    return {"news_list": news_list}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: int):
    """删除搜索会话"""
    success = search_manager.delete_search(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    return {"success": True}


@app.post("/api/feedback/quick")
async def quick_feedback(request: QuickFeedbackRequest):
    """提交快捷反馈"""
    result = feedback_handler.quick_feedback(request.news_id, request.status)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.post("/api/feedback/text")
async def text_feedback(request: TextFeedbackRequest):
    """提交文字反馈"""
    result = feedback_handler.text_feedback(request.news_id, request.content)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# ==================== 异步反馈 ====================

def _process_feedback_async(task_id: str, news_id: int, status: str):
    """后台处理反馈任务"""
    try:
        # 更新任务状态为处理中 - 提取关键词阶段
        with _feedback_lock:
            _feedback_tasks[task_id]["status"] = "processing"
            _feedback_tasks[task_id]["message"] = "正在用 LLM 提取关键词..."
        
        # 调用反馈处理
        result = feedback_handler.quick_feedback(news_id, status)
        
        if result.get("success"):
            # 更新任务状态为完成
            with _feedback_lock:
                _feedback_tasks[task_id]["status"] = "completed"
                _feedback_tasks[task_id]["result"] = result
                _feedback_tasks[task_id]["message"] = "反馈处理完成"
        else:
            # 业务逻辑失败（如新闻不存在）
            with _feedback_lock:
                _feedback_tasks[task_id]["status"] = "failed"
                _feedback_tasks[task_id]["message"] = result.get("message", "处理失败")
            
    except Exception as e:
        # 更新任务状态为失败
        with _feedback_lock:
            _feedback_tasks[task_id]["status"] = "failed"
            _feedback_tasks[task_id]["message"] = f"处理失败: {str(e)}"


@app.post("/api/feedback/quick/async")
async def quick_feedback_async(request: QuickFeedbackRequest):
    """异步提交快捷反馈（返回任务 ID，后台处理）"""
    # 生成任务 ID
    task_id = str(uuid.uuid4())
    
    # 初始化任务状态
    with _feedback_lock:
        _feedback_tasks[task_id] = {
            "task_id": task_id,
            "news_id": request.news_id,
            "status": "pending",
            "message": "任务已创建，等待处理...",
            "result": None
        }
    
    # 启动后台线程处理
    thread = threading.Thread(
        target=_process_feedback_async,
        args=(task_id, request.news_id, request.status),
        daemon=True
    )
    thread.start()
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "反馈任务已提交，正在后台处理"
    }


@app.get("/api/feedback/quick/status/{task_id}")
async def get_feedback_status(task_id: str):
    """查询异步反馈任务状态"""
    with _feedback_lock:
        task = _feedback_tasks.get(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task


@app.post("/api/export")
async def export_markdown(request: ExportRequest):
    """导出 Markdown"""
    if not request.news_ids:
        raise HTTPException(status_code=400, detail="请选择要导出的新闻")
    if not request.title:
        raise HTTPException(status_code=400, detail="请输入文档标题")
    
    result = exporter.get_export_content(request.news_ids, request.title)
    return result


@app.post("/api/translate/{news_id}")
async def translate_news(news_id: int):
    """翻译单条新闻（标题翻译 + 全文摘要）"""
    from .llm_client import llm_client
    import httpx
    
    news = storage.get_news(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="新闻不存在")
    
    title_en = news.get("title_en", "")
    url = news.get("url", "")
    
    # 1. 翻译标题
    title_result = llm_client.translate(title_en)
    title_cn = title_result.get("title_cn", title_en)
    
    # 2. 抓取文章全文
    article_content = ""
    if url:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, follow_redirects=True, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                if resp.status_code == 200:
                    # 简单提取文本内容（去掉 HTML 标签）
                    import re
                    html = resp.text
                    # 移除 script 和 style
                    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
                    # 移除 HTML 标签
                    text = re.sub(r'<[^>]+>', ' ', html)
                    # 清理空白
                    text = re.sub(r'\s+', ' ', text).strip()
                    article_content = text[:3000]  # 取前3000字
        except Exception as e:
            print(f"抓取文章失败: {e}")
    
    # 3. 生成摘要（多级降级策略）
    description_en = ""
    description_cn = ""
    
    if article_content:
        # 优先：有全文内容，生成英文摘要+中文摘要
        description_en = llm_client.summarize_article_en(title_en, article_content)
        description_cn = llm_client.summarize_article(title_en, article_content)
    else:
        # 降级1：有HN描述 → 描述变成英文摘要，翻译后为中文摘要
        desc_en = news.get("description_en", "")
        if desc_en:
            description_en = desc_en
            desc_result = llm_client.translate(desc_en)
            description_cn = desc_result.get("title_cn", desc_en)[:300]
        else:
            # 降级2（兜底）：用标题+URL让LLM直接生成英文+中文摘要
            if url:
                fallback_result = llm_client.summarize_by_title_and_url(title_en, url)
                description_en = fallback_result.get("description_en", "")
                description_cn = fallback_result.get("description_cn", "暂无摘要")
            else:
                description_en = "No summary available"
                description_cn = "暂无摘要"
    
    # 4. 更新数据库
    storage.update_news_translation(news_id, title_cn, description_cn, description_en)
    
    return {
        "success": True,
        "title_cn": title_cn,
        "description_cn": description_cn,
        "description_en": description_en
    }


# ==================== 异步翻译 ====================

def _translate_single_news(news_id: int):
    """翻译单条新闻（后台线程调用）"""
    from .llm_client import llm_client
    import httpx
    
    try:
        news = storage.get_news(news_id)
        if not news:
            return
        
        title_en = news.get("title_en", "")
        url = news.get("url", "")
        
        # 1. 翻译标题
        title_result = llm_client.translate(title_en)
        title_cn = title_result.get("title_cn", title_en)
        
        # 2. 抓取文章全文
        article_content = ""
        if url:
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(url, follow_redirects=True, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    if resp.status_code == 200:
                        import re
                        html = resp.text
                        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
                        text = re.sub(r'<[^>]+>', ' ', html)
                        text = re.sub(r'\s+', ' ', text).strip()
                        article_content = text[:3000]
            except Exception as e:
                print(f"抓取文章失败: {e}")
        
        # 3. 生成摘要
        description_en = ""
        description_cn = ""
        
        if article_content:
            description_en = llm_client.summarize_article_en(title_en, article_content)
            description_cn = llm_client.summarize_article(title_en, article_content)
        else:
            desc_en = news.get("description_en", "")
            if desc_en:
                description_en = desc_en
                desc_result = llm_client.translate(desc_en)
                description_cn = desc_result.get("title_cn", desc_en)[:300]
            else:
                if url:
                    fallback_result = llm_client.summarize_by_title_and_url(title_en, url)
                    description_en = fallback_result.get("description_en", "")
                    description_cn = fallback_result.get("description_cn", "暂无摘要")
                else:
                    description_en = "No summary available"
                    description_cn = "暂无摘要"
        
        # 4. 更新数据库
        storage.update_news_translation(news_id, title_cn, description_cn, description_en)
        storage.update_translation_status(news_id, "done")
        
    except Exception as e:
        print(f"翻译新闻 {news_id} 失败: {e}")
        # 翻译失败也标记为 done，避免卡住
        storage.update_translation_status(news_id, "done")


def _translate_session_worker(session_id: int):
    """后台翻译整个会话的展示新闻（Top 10）"""
    news_list = storage.get_news_by_session(session_id)[:10]
    
    for news in news_list:
        news_id = news["id"]
        # 跳过已翻译的
        if news.get("translation_status") == "done":
            with _translating_lock:
                if session_id in _translating_tasks:
                    _translating_tasks[session_id].discard(news_id)
            continue
        
        # 标记为翻译中
        storage.update_translation_status(news_id, "pending")
        with _translating_lock:
            if session_id not in _translating_tasks:
                _translating_tasks[session_id] = set()
            _translating_tasks[session_id].add(news_id)
        
        # 执行翻译
        _translate_single_news(news_id)
        
        # 翻译完成，移除
        with _translating_lock:
            if session_id in _translating_tasks:
                _translating_tasks[session_id].discard(news_id)
    
    # 全部完成，清理任务
    with _translating_lock:
        _translating_tasks.pop(session_id, None)


@app.post("/api/translate/session/{session_id}")
async def translate_session(session_id: int):
    """异步翻译整个会话的所有新闻"""
    # 检查会话是否存在
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="搜索会话不存在")
    
    # 检查是否已在翻译中
    with _translating_lock:
        if session_id in _translating_tasks and _translating_tasks[session_id]:
            return {"success": True, "message": "翻译任务已在进行中"}
    
    # 获取未翻译的新闻数量
    progress = storage.get_translation_progress(session_id)
    
    if progress["pending"] == 0:
        return {"success": True, "message": "所有新闻已翻译", "progress": progress}
    
    # 启动后台翻译线程
    thread = threading.Thread(
        target=_translate_session_worker,
        args=(session_id,),
        daemon=True
    )
    thread.start()
    
    return {
        "success": True,
        "message": f"开始翻译 {progress['pending']} 条新闻",
        "progress": progress
    }


@app.get("/api/translate/session/{session_id}/status")
async def translate_session_status(session_id: int):
    """查询翻译进度"""
    # 检查会话是否存在
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="搜索会话不存在")
    
    # 获取数据库中的翻译进度
    progress = storage.get_translation_progress(session_id)
    
    # 获取正在翻译的新闻 ID
    translating_ids = []
    with _translating_lock:
        if session_id in _translating_tasks:
            translating_ids = list(_translating_tasks[session_id])
    
    return {
        "progress": progress,
        "translating_ids": translating_ids,
        "is_translating": len(translating_ids) > 0
    }


@app.get("/api/keywords")
async def get_keywords():
    """获取关键词池"""
    keywords = keyword_manager.get_all_keywords()
    stats = keyword_manager.get_feedback_stats()
    return {"keywords": keywords, "stats": stats}


@app.put("/api/keywords/{keyword_id}")
async def update_keyword(keyword_id: int, request: KeywordUpdateRequest):
    """更新关键词得分"""
    success = keyword_manager.update_keyword(keyword_id, request.score)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")
    return {"success": True}


@app.delete("/api/keywords/{keyword_id}")
async def delete_keyword(keyword_id: int):
    """删除关键词"""
    success = keyword_manager.delete_keyword(keyword_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    return {"success": True}


@app.post("/api/keywords/normalize")
async def normalize_keyword(keyword: str):
    """归一化单个关键词"""
    normalized = keyword_manager.normalize_keyword(keyword)
    return {
        "original": keyword,
        "normalized": normalized
    }


@app.get("/api/keywords/normalize-cache")
async def get_normalize_cache():
    """获取归一化缓存（调试用）"""
    cache = storage.get_all_keyword_pairs()
    return {"cache": cache}


@app.get("/api/last-search")
async def get_last_search():
    """获取上一次搜索条件"""
    last_search = storage.get_last_search()
    if last_search:
        # 解析 keywords JSON
        keywords = json.loads(last_search.get("keywords", "[]"))
        return {
            "keywords": keywords,
            "logic": last_search.get("logic", "OR"),
            "start_date": last_search.get("start_date"),
            "end_date": last_search.get("end_date")
        }
    # 返回默认配置
    default = config.default_search
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "keywords": default.get("keywords", ["LLM", "Fintech"]),
        "logic": default.get("logic", "OR"),
        "start_date": today,
        "end_date": today
    }


@app.get("/api/config")
async def get_llm_config():
    """获取 LLM 配置"""
    llm = config.llm
    return {
        "provider": llm.get("provider"),
        "api_key": llm.get("api_key"),
        "api_url": llm.get("api_url"),
        "model_name": llm.get("model_name")
    }


@app.put("/api/config")
async def update_llm_config(request: LLMConfigRequest):
    """更新 LLM 配置"""
    try:
        # 读取现有配置文件
        config_path = config.config_path
        with open(config_path, "r", encoding="utf-8") as f:
            full_config = json.load(f)
        
        # 更新 llm 部分
        if "llm" not in full_config:
            full_config["llm"] = {}
        
        if request.provider is not None:
            full_config["llm"]["provider"] = request.provider
        if request.api_key is not None:
            full_config["llm"]["api_key"] = request.api_key
        if request.api_url is not None:
            full_config["llm"]["api_url"] = request.api_url
        if request.model_name is not None:
            full_config["llm"]["model_name"] = request.model_name
        
        # 写回配置文件
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(full_config, f, indent=2, ensure_ascii=False)
        
        # 重新加载配置
        config.reload()
        
        return {"success": True, "message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


# ==================== 启动 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
