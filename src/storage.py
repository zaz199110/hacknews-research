"""数据库存储模块"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class Storage:
    """SQLite 数据库存储"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "news.db"
        self.db_path = Path(db_path)
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """确保数据库和表存在"""
        # 创建 data 目录
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建表
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 搜索会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keywords TEXT NOT NULL,
                    logic TEXT NOT NULL DEFAULT 'OR',
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    result_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 新闻表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_id INTEGER NOT NULL,
                    object_id TEXT NOT NULL,
                    title_cn TEXT,
                    title_en TEXT,
                    description_cn TEXT,
                    description_en TEXT,
                    url TEXT,
                    source TEXT DEFAULT 'hackernews',
                    points INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    published_at DATETIME,
                    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    content_keywords TEXT,
                    score FLOAT DEFAULT 0,
                    feedback_status TEXT,
                    FOREIGN KEY (search_id) REFERENCES search_sessions(id)
                )
            """)
            
            # 关键词池表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    score FLOAT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 迁移：为 news 表添加 translation_status 列（如果不存在）
            cursor.execute("PRAGMA table_info(news)")
            columns = [col[1] for col in cursor.fetchall()]
            if "translation_status" not in columns:
                cursor.execute(
                    "ALTER TABLE news ADD COLUMN translation_status TEXT DEFAULT 'pending'"
                )
            
            # 文字反馈表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    news_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    extracted_keywords TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (news_id) REFERENCES news(id)
                )
            """)
            
            # 关键词归一化缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keyword_normalize_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_keyword TEXT NOT NULL,
                    normalized_keyword TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_search_id ON news(search_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_object_id ON news(object_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_score ON news(score DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_news_id ON feedback(news_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_normalize_cache_original ON keyword_normalize_cache(original_keyword)")
            
            conn.commit()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== 搜索会话 ====================
    
    def create_session(self, keywords: List[str], logic: str, start_date: str, end_date: str) -> int:
        """创建搜索会话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO search_sessions (keywords, logic, start_date, end_date) VALUES (?, ?, ?, ?)",
                (json.dumps(keywords), logic, start_date, end_date)
            )
            conn.commit()
            return cursor.lastrowid
    
    def update_session_result_count(self, session_id: int, count: int):
        """更新搜索会话结果数量"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE search_sessions SET result_count = ? WHERE id = ?",
                (count, session_id)
            )
            conn.commit()
    
    def get_session(self, session_id: int) -> Optional[Dict]:
        """获取搜索会话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM search_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_all_sessions(self) -> List[Dict]:
        """获取所有搜索会话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM search_sessions ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_session(self, session_id: int):
        """删除搜索会话及其关联的新闻"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 先删除关联的文字反馈
            cursor.execute("""
                DELETE FROM feedback WHERE news_id IN (
                    SELECT id FROM news WHERE search_id = ?
                )
            """, (session_id,))
            # 删除关联的新闻
            cursor.execute("DELETE FROM news WHERE search_id = ?", (session_id,))
            # 删除会话
            cursor.execute("DELETE FROM search_sessions WHERE id = ?", (session_id,))
            conn.commit()
    
    def get_last_search(self) -> Optional[Dict]:
        """获取上一次搜索条件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM search_sessions ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    # ==================== 新闻 ====================
    
    def create_news(self, search_id: int, object_id: str, title_en: str, 
                    description_en: str = None, url: str = None,
                    points: int = 0, comments: int = 0, 
                    published_at: str = None, content_keywords: List[str] = None,
                    score: float = 0) -> int:
        """创建新闻"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO news (search_id, object_id, title_en, description_en, url, 
                                 points, comments, published_at, content_keywords, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (search_id, object_id, title_en, description_en, url,
                  points, comments, published_at, 
                  json.dumps(content_keywords) if content_keywords else None,
                  score))
            conn.commit()
            return cursor.lastrowid
    
    def update_news_translation(self, news_id: int, title_cn: str, description_cn: str, description_en: str = None):
        """更新新闻翻译"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if description_en is not None:
                cursor.execute(
                    "UPDATE news SET title_cn = ?, description_cn = ?, description_en = ? WHERE id = ?",
                    (title_cn, description_cn, description_en, news_id)
                )
            else:
                cursor.execute(
                    "UPDATE news SET title_cn = ?, description_cn = ? WHERE id = ?",
                    (title_cn, description_cn, news_id)
                )
            conn.commit()
    
    def update_news_keywords(self, news_id: int, keywords: List[str]):
        """更新新闻关键词"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE news SET content_keywords = ? WHERE id = ?",
                (json.dumps(keywords), news_id)
            )
            conn.commit()
    
    def update_news_score(self, news_id: int, score: float):
        """更新新闻得分"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE news SET score = ? WHERE id = ?",
                (score, news_id)
            )
            conn.commit()
    
    def update_news_feedback_status(self, news_id: int, status: Optional[str]):
        """更新反馈状态，传 None 表示取消反馈"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE news SET feedback_status = ? WHERE id = ?",
                (status, news_id)
            )
            conn.commit()
    
    def update_translation_status(self, news_id: int, status: str):
        """更新翻译状态：pending / done"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE news SET translation_status = ? WHERE id = ?",
                (status, news_id)
            )
            conn.commit()
    
    def get_translation_progress(self, session_id: int) -> Dict:
        """获取翻译进度：{ total, done, pending }（仅统计展示的 Top 10）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 只取 Top 10 的进度
            cursor.execute(
                "SELECT COUNT(*) FROM (SELECT * FROM news WHERE search_id = ? ORDER BY score DESC LIMIT 10)",
                (session_id,)
            )
            total = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM (SELECT * FROM news WHERE search_id = ? ORDER BY score DESC LIMIT 10) WHERE translation_status = 'done'",
                (session_id,)
            )
            done = cursor.fetchone()[0]
            return {"total": total, "done": done, "pending": total - done}
    
    def get_news(self, news_id: int) -> Optional[Dict]:
        """获取单条新闻"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_news_by_session(self, session_id: int) -> List[Dict]:
        """获取搜索会话下的所有新闻（按得分排序）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM news WHERE search_id = ? ORDER BY score DESC",
                (session_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_news_by_object_id(self, object_id: str) -> Optional[Dict]:
        """根据 object_id 获取新闻"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM news WHERE object_id = ?", (object_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def news_exists_in_session(self, session_id: int, object_id: str) -> bool:
        """检查新闻是否已存在于该搜索会话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM news WHERE search_id = ? AND object_id = ?",
                (session_id, object_id)
            )
            return cursor.fetchone()[0] > 0
    
    # ==================== 关键词池 ====================
    
    def get_or_create_keyword(self, keyword: str) -> int:
        """获取或创建关键词"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 先查询是否存在
            cursor.execute("SELECT id FROM keywords WHERE keyword = ?", (keyword,))
            row = cursor.fetchone()
            if row:
                return row[0]
            # 不存在则创建
            cursor.execute("INSERT INTO keywords (keyword) VALUES (?)", (keyword,))
            conn.commit()
            return cursor.lastrowid
    
    def update_keyword_score(self, keyword: str, delta: float):
        """更新关键词得分"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 确保关键词存在
            self.get_or_create_keyword(keyword)
            # 更新得分
            cursor.execute(
                "UPDATE keywords SET score = score + ?, updated_at = CURRENT_TIMESTAMP WHERE keyword = ?",
                (delta, keyword)
            )
            conn.commit()
    
    def set_keyword_score(self, keyword_id: int, score: float):
        """设置关键词得分"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE keywords SET score = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (score, keyword_id)
            )
            conn.commit()
    
    def delete_keyword(self, keyword_id: int):
        """删除关键词"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
            conn.commit()
    
    def get_all_keywords(self) -> List[Dict]:
        """获取所有关键词（按得分排序）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM keywords ORDER BY score DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_keyword_score(self, keyword: str) -> float:
        """获取关键词得分"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT score FROM keywords WHERE keyword = ?", (keyword,))
            row = cursor.fetchone()
            return row[0] if row else 0.0
    
    def get_keyword_id(self, keyword: str) -> Optional[int]:
        """获取关键词 ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM keywords WHERE keyword = ?", (keyword,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def decay_keyword_scores(self, rate: float = 0.95, interval_days: int = 7):
        """衰减关键词得分"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 使用 SQLite 的日期函数计算衰减
            cursor.execute("""
                UPDATE keywords 
                SET score = score * POWER(?, CAST((julianday('now') - julianday(updated_at)) / ? AS INTEGER)),
                    updated_at = CURRENT_TIMESTAMP
                WHERE ABS(score) > 0.01
            """, (rate, interval_days))
            conn.commit()
    
    # ==================== 反馈 ====================
    
    def create_feedback(self, news_id: int, content: str, extracted_keywords: List[str] = None) -> int:
        """创建文字反馈"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO feedback (news_id, content, extracted_keywords) VALUES (?, ?, ?)",
                (news_id, content, json.dumps(extracted_keywords) if extracted_keywords else None)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_feedback_by_news(self, news_id: int) -> List[Dict]:
        """获取新闻的所有反馈"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM feedback WHERE news_id = ? ORDER BY created_at DESC",
                (news_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_feedback_stats(self) -> Dict:
        """获取反馈统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 已反馈的新闻数量（去重）
            cursor.execute("SELECT COUNT(*) FROM news WHERE feedback_status IS NOT NULL")
            total_feedback = cursor.fetchone()[0]
            
            # 👍 的数量
            cursor.execute("SELECT COUNT(*) FROM news WHERE feedback_status = 'positive'")
            positive_count = cursor.fetchone()[0]
            
            # 👎 的数量
            cursor.execute("SELECT COUNT(*) FROM news WHERE feedback_status = 'negative'")
            negative_count = cursor.fetchone()[0]
            
            return {
                "total": total_feedback,
                "positive": positive_count,
                "negative": negative_count
            }
    
    # ==================== 关键词归一化缓存 ====================
    
    def get_normalized_keyword(self, original_keyword: str) -> Optional[str]:
        """获取归一化后的关键词（从缓存）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT normalized_keyword FROM keyword_normalize_cache WHERE original_keyword = ?",
                (original_keyword,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_normalized_keyword(self, original_keyword: str, normalized_keyword: str):
        """保存归一化结果到缓存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO keyword_normalize_cache (original_keyword, normalized_keyword) VALUES (?, ?)",
                (original_keyword, normalized_keyword)
            )
            conn.commit()
    
    def get_all_keyword_pairs(self) -> List[Dict]:
        """获取所有归一化映射（用于调试）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM keyword_normalize_cache")
            return [dict(row) for row in cursor.fetchall()]


# 全局存储实例
storage = Storage()
