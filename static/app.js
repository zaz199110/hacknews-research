/**
 * LLM 新闻日报 - 前端交互逻辑
 */

// ==================== 全局变量 ====================

let currentKeywords = [];
let currentNewsList = [];
let selectedNewsIds = new Set();
let selectedSessionIds = new Set();
let isBatchMode = false;

// ==================== 工具函数 ====================

async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '请求失败');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API 调用失败:', error);
        throw error;
    }
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN');
}

function getToday() {
    return new Date().toISOString().split('T')[0];
}

// ==================== 首页功能 ====================

// 加载上次搜索条件
async function loadLastSearch() {
    try {
        const data = await apiCall('/api/last-search');
        
        // 设置关键词
        currentKeywords = data.keywords || [];
        renderKeywords();
        
        // 设置逻辑关系
        const logicRadio = document.querySelector(`input[name="logic"][value="${data.logic}"]`);
        if (logicRadio) logicRadio.checked = true;
        
        // 设置日期
        document.getElementById('start-date').value = data.start_date || getToday();
        document.getElementById('end-date').value = data.end_date || getToday();
    } catch (error) {
        console.error('加载上次搜索失败:', error);
        // 使用默认值
        currentKeywords = ['LLM'];
        renderKeywords();
        document.getElementById('start-date').value = getToday();
        document.getElementById('end-date').value = getToday();
    }
}

// 加载搜索历史
async function loadSessions() {
    try {
        const data = await apiCall('/api/sessions');
        renderSessions(data.sessions);
    } catch (error) {
        console.error('加载搜索历史失败:', error);
    }
}

// 渲染关键词标签
function renderKeywords() {
    const container = document.getElementById('keywords-container');
    container.innerHTML = currentKeywords.map((kw, index) => `
        <span class="tag">
            ${kw}
            <button onclick="removeKeyword(${index})">×</button>
        </span>
    `).join('');
}

// 添加关键词
function addKeyword() {
    const input = document.getElementById('keyword-input');
    const keyword = input.value.trim();
    
    if (keyword && !currentKeywords.includes(keyword)) {
        currentKeywords.push(keyword);
        renderKeywords();
        input.value = '';
    }
}

// 删除关键词
function removeKeyword(index) {
    currentKeywords.splice(index, 1);
    renderKeywords();
}

// 执行搜索
async function doSearch() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const logic = document.querySelector('input[name="logic"]:checked').value;
    
    if (!startDate || !endDate) {
        alert('请选择时间范围');
        return;
    }
    
    if (currentKeywords.length === 0) {
        alert('请至少添加一个关键词');
        return;
    }
    
    const btn = document.getElementById('search-btn');
    btn.disabled = true;
    btn.textContent = '搜索中...';
    
    try {
        const result = await apiCall('/api/search', {
            method: 'POST',
            body: JSON.stringify({
                keywords: currentKeywords,
                logic: logic,
                start_date: startDate,
                end_date: endDate
            })
        });
        
        // 跳转到详情页
        window.location.href = `/detail/${result.session_id}`;
    } catch (error) {
        alert('搜索失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '立即搜索';
    }
}

// 渲染搜索历史
function renderSessions(sessions) {
    const container = document.getElementById('sessions-list');
    
    if (!sessions || sessions.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无搜索记录</div>';
        return;
    }
    
    container.innerHTML = sessions.map(session => {
        const keywords = JSON.parse(session.keywords || '[]');
        const keywordsStr = keywords.join(session.logic === 'OR' ? ' OR ' : ' AND ');
        
        return `
            <div class="session-card" onclick="${isBatchMode ? `toggleSessionSelection(${session.id})` : `window.location.href='/detail/${session.id}'`}">
                <div class="session-info">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        ${isBatchMode ? `<input type="checkbox" ${selectedSessionIds.has(session.id) ? 'checked' : ''} onclick="event.stopPropagation(); toggleSessionSelection(${session.id})">` : ''}
                        <span class="session-id">#${session.id}</span>
                        <span class="session-date">${formatDate(session.created_at)}</span>
                    </div>
                    <div class="session-meta">
                        ${keywordsStr} | ${formatDate(session.start_date)} ~ ${formatDate(session.end_date)} | ${session.result_count}条
                    </div>
                </div>
                ${!isBatchMode ? `<button onclick="event.stopPropagation(); deleteSession(${session.id})" class="btn btn-danger">删除</button>` : ''}
            </div>
        `;
    }).join('');
}

// 切换批量模式
function toggleBatchMode() {
    isBatchMode = !isBatchMode;
    selectedSessionIds.clear();
    
    const batchModeBtn = document.getElementById('batch-mode-btn');
    const batchDeleteBtn = document.getElementById('batch-delete-btn');
    
    if (isBatchMode) {
        batchModeBtn.textContent = '取消';
        batchDeleteBtn.style.display = 'inline-block';
    } else {
        batchModeBtn.textContent = '批量删除';
        batchDeleteBtn.style.display = 'none';
    }
    
    loadSessions();
}

// 切换会话选择
function toggleSessionSelection(sessionId) {
    if (selectedSessionIds.has(sessionId)) {
        selectedSessionIds.delete(sessionId);
    } else {
        selectedSessionIds.add(sessionId);
    }
    
    // 重新渲染列表
    loadSessions();
}

// 批量删除
async function batchDelete() {
    if (selectedSessionIds.size === 0) {
        alert('请选择要删除的搜索会话');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${selectedSessionIds.size} 个搜索会话吗？`)) {
        return;
    }
    
    try {
        for (const sessionId of selectedSessionIds) {
            await apiCall(`/api/sessions/${sessionId}`, { method: 'DELETE' });
        }
        
        alert(`成功删除 ${selectedSessionIds.size} 个搜索会话`);
        selectedSessionIds.clear();
        isBatchMode = false;
        
        // 更新按钮状态
        document.getElementById('batch-mode-btn').textContent = '批量删除';
        document.getElementById('batch-delete-btn').style.display = 'none';
        
        loadSessions();
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// 删除搜索会话
async function deleteSession(sessionId) {
    if (!confirm('确定要删除这个搜索会话吗？')) return;
    
    try {
        await apiCall(`/api/sessions/${sessionId}`, { method: 'DELETE' });
        loadSessions();
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// ==================== 详情页功能 ====================

// 加载搜索信息
async function loadSessionInfo() {
    try {
        const session = await apiCall(`/api/sessions/${sessionId}`);
        const keywords = JSON.parse(session.keywords || '[]');
        const keywordsStr = keywords.join(session.logic === 'OR' ? ' OR ' : ' AND ');
        
        document.getElementById('session-info').textContent = 
            `搜索 #${session.id} | ${keywordsStr} | ${formatDate(session.start_date)} ~ ${formatDate(session.end_date)}`;
    } catch (error) {
        console.error('加载搜索信息失败:', error);
    }
}

// 加载新闻列表
async function loadNewsList() {
    try {
        const data = await apiCall(`/api/sessions/${sessionId}/news`);
        currentNewsList = data.news_list || [];
        renderNewsList();
    } catch (error) {
        console.error('加载新闻列表失败:', error);
        document.getElementById('news-list').innerHTML = 
            '<div class="empty-state">加载失败</div>';
    }
}

// 翻译轮询定时器
let translatePollTimer = null;

// 全局翻译所有新闻（异步）
async function translateAll() {
    const btn = document.getElementById('translate-btn');
    btn.disabled = true;
    btn.textContent = '启动翻译...';
    
    try {
        const result = await apiCall(`/api/translate/session/${sessionId}`, {
            method: 'POST'
        });
        
        if (result.progress && result.progress.pending === 0) {
            btn.disabled = false;
            btn.textContent = '翻译';
            alert('所有新闻已翻译');
            loadNewsList();
            return;
        }
        
        // 开始轮询翻译进度
        startTranslatePoll();
        
    } catch (error) {
        alert('启动翻译失败: ' + error.message);
        btn.disabled = false;
        btn.textContent = '翻译';
    }
}

// 翻译单条新闻
async function translateSingleNews(newsId) {
    try {
        // 标记为翻译中
        const news = currentNewsList.find(n => n.id === newsId);
        if (news) {
            news.translation_status = 'translating';
            renderNewsList();
        }
        
        await apiCall(`/api/translate/${newsId}`, {
            method: 'POST'
        });
        
        // 翻译完成，刷新列表
        loadNewsList();
    } catch (error) {
        alert('翻译失败: ' + error.message);
        // 恢复状态
        if (news) {
            news.translation_status = 'pending';
            renderNewsList();
        }
    }
}

// 开始轮询翻译进度
function startTranslatePoll() {
    const btn = document.getElementById('translate-btn');
    btn.disabled = true;
    btn.textContent = '翻译中...';
    
    // 清除之前的定时器
    if (translatePollTimer) {
        clearInterval(translatePollTimer);
    }
    
    translatePollTimer = setInterval(async () => {
        try {
            const status = await apiCall(`/api/translate/session/${sessionId}/status`);
            
            // 更新按钮文本
            const { total, done } = status.progress;
            btn.textContent = `翻译中... (${done}/${total})`;
            
            // 如果有新闻状态变化，刷新列表
            if (status.is_translating || done < total) {
                // 一次性获取最新数据
                const updatedData = await apiCall(`/api/sessions/${sessionId}/news`);
                currentNewsList = updatedData.news_list || [];
            }
            
            // 重新渲染列表
            renderNewsList();
            
            // 翻译完成
            if (!status.is_translating) {
                clearInterval(translatePollTimer);
                translatePollTimer = null;
                btn.disabled = false;
                btn.textContent = '翻译';
            }
        } catch (error) {
            console.error('查询翻译状态失败:', error);
        }
    }, 2000); // 每2秒轮询一次
}

// 更新单条新闻卡片显示
function updateNewsCard(news) {
    const card = document.querySelector(`[data-news-id="${news.id}"]`)?.closest('.news-card');
    if (!card) return;
    
    const titleEl = card.querySelector('.news-title');
    const descEl = card.querySelector('.news-description');
    
    // 优先显示中文标题，没有则显示英文标题
    if (titleEl) {
        const title = news.title_cn || news.title_en || '无标题';
        titleEl.innerHTML = `<a href="${news.url}" target="_blank">${title}</a>`;
    }
    
    // 优先显示中文摘要，没有则显示英文摘要
    if (descEl) {
        const description = news.description_cn || news.description_en || '';
        if (description) {
            descEl.textContent = description;
            descEl.style.display = 'block';
        } else {
            descEl.style.display = 'none';
        }
    }
}

// 渲染新闻列表
function renderNewsList() {
    const container = document.getElementById('news-list');
    
    if (!currentNewsList || currentNewsList.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无新闻</div>';
        return;
    }
    
    container.innerHTML = currentNewsList.map((news, index) => {
        // 优先显示中文，没有则显示英文
        const title = news.title_cn || news.title_en || '无标题';
        const description = news.description_cn || news.description_en || '';
        const feedbackStatus = news.feedback_status;
        
        return `
            <div class="news-card">
                <div style="display: flex; gap: 12px;">
                    <input type="checkbox" 
                           style="margin-top: 4px;"
                           data-news-id="${news.id}"
                           onchange="toggleNewsSelection(${news.id})">
                    <div style="flex: 1;">
                        <div class="news-title">
                            <a href="${news.url}" target="_blank">${title}</a>
                        </div>
                        ${description ? `<div class="news-description">${description}</div>` : ''}
                        <div class="news-meta">
                            <a href="${news.url}" target="_blank">原文链接</a>
                            <span>HN👍 ${news.points || 0}</span>
                            <span>HN💬 ${news.comments || 0}</span>
                            <span>⏰ ${formatDate(news.published_at)}</span>
                            <span class="translation-status ${news.translation_status === 'done' ? 'status-done' : news.translation_status === 'translating' ? 'status-translating' : 'status-pending'}">
                                ${news.translation_status === 'done' ? '✓ 已翻译' : news.translation_status === 'translating' ? '⏳ 翻译中' : '未翻译'}
                            </span>
                        </div>
                        
                        <div class="feedback-btns">
                            <button onclick="quickFeedback(${news.id}, 'positive')" 
                                    class="feedback-btn ${feedbackStatus === 'positive' ? 'active-positive' : ''}">
                                👍
                            </button>
                            <button onclick="quickFeedback(${news.id}, 'negative')" 
                                    class="feedback-btn ${feedbackStatus === 'negative' ? 'active-negative' : ''}">
                                👎
                            </button>
                            ${news.translation_status !== 'translating' ? 
                                `<button onclick="translateSingleNews(${news.id})" 
                                        class="feedback-btn" title="重新翻译">
                                    🔄
                                </button>` : ''}
                        </div>
                        
                        <div class="feedback-input">
                            <input type="text" id="feedback-${news.id}" 
                                   placeholder="文字反馈（可选）">
                            <button onclick="submitTextFeedback(${news.id})" class="btn btn-primary">
                                提交
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// 切换全选
function toggleSelectAll() {
    const selectAll = document.getElementById('select-all').checked;
    selectedNewsIds.clear();
    
    if (selectAll) {
        currentNewsList.forEach(news => selectedNewsIds.add(news.id));
    }
    
    document.querySelectorAll('[data-news-id]').forEach(checkbox => {
        checkbox.checked = selectAll;
    });
    
    updateSelectedCount();
}

// 切换单条选择
function toggleNewsSelection(newsId) {
    if (selectedNewsIds.has(newsId)) {
        selectedNewsIds.delete(newsId);
    } else {
        selectedNewsIds.add(newsId);
    }
    updateSelectedCount();
}

// 更新已选数量
function updateSelectedCount() {
    document.getElementById('selected-count').textContent = `已选 ${selectedNewsIds.size} 条`;
}

// 快捷反馈（异步版本）
async function quickFeedback(newsId, status) {
    // 找到对应的按钮并显示加载状态
    const news = currentNewsList.find(n => n.id === newsId);
    const card = document.querySelector(`[data-news-id="${newsId}"]`)?.closest('.news-card');
    
    if (card) {
        const feedbackBtns = card.querySelectorAll('.feedback-btn');
        feedbackBtns.forEach(btn => btn.disabled = true);
        
        // 显示加载提示
        const feedbackArea = card.querySelector('.feedback-btns');
        if (feedbackArea) {
            feedbackArea.innerHTML = '<span style="color: #9B9A97; font-size: 13px;">⏳ 正在提取关键词...</span>';
        }
    }
    
    try {
        // 调用异步 API
        const result = await apiCall('/api/feedback/quick/async', {
            method: 'POST',
            body: JSON.stringify({ news_id: newsId, status: status })
        });
        
        if (!result.success) {
            throw new Error(result.message || '提交失败');
        }
        
        // 开始轮询任务状态
        const taskId = result.task_id;
        await pollFeedbackStatus(taskId, newsId, status);
        
    } catch (error) {
        alert('反馈失败: ' + error.message);
        // 恢复按钮状态
        if (card) {
            renderNewsList();
        }
    }
}

// 轮询反馈任务状态
async function pollFeedbackStatus(taskId, newsId, status) {
    const maxAttempts = 150; // 最多轮询 150 次（约 150 秒，覆盖后端 LLM 120s 超时）
    let attempts = 0;
    
    while (attempts < maxAttempts) {
        try {
            const taskStatus = await apiCall(`/api/feedback/quick/status/${taskId}`);
            
            // 更新卡片上的状态提示
            updateFeedbackStatusInCard(newsId, taskStatus.message);
            
            if (taskStatus.status === 'completed') {
                // 任务完成
                const result = taskStatus.result;
                
                // 更新本地数据
                const news = currentNewsList.find(n => n.id === newsId);
                if (news) {
                    news.feedback_status = result.feedback_status;
                }
                
                // 显示结果
                if (result.keywords && result.keywords.length > 0) {
                    const keywordsStr = result.keywords.join(', ');
                    const deltaStr = result.delta > 0 ? `+${result.delta}` : result.delta;
                    const message = result.feedback_status 
                        ? `反馈成功！\n\n提取的关键词：${keywordsStr}\n得分变化：${deltaStr}`
                        : `反馈已取消\n\n得分变化：${deltaStr}`;
                    alert(message);
                }
                
                // 重新渲染列表
                renderNewsList();
                return;
                
            } else if (taskStatus.status === 'failed') {
                // 任务失败
                alert('反馈处理失败: ' + taskStatus.message);
                renderNewsList();
                return;
            }
            
            // 等待 1 秒后继续轮询
            await new Promise(resolve => setTimeout(resolve, 1000));
            attempts++;
            
        } catch (error) {
            console.error('查询反馈状态失败:', error);
            break;
        }
    }
    
    // 超时处理
    alert('反馈处理超时，请稍后刷新页面查看结果');
    renderNewsList();
}

// 更新卡片上的反馈状态提示
function updateFeedbackStatusInCard(newsId, message) {
    const card = document.querySelector(`[data-news-id="${newsId}"]`)?.closest('.news-card');
    if (!card) return;
    
    const feedbackArea = card.querySelector('.feedback-btns');
    if (feedbackArea) {
        feedbackArea.innerHTML = `<span style="color: #9B9A97; font-size: 13px;">⏳ ${message}</span>`;
    }
}

// 提交文字反馈
async function submitTextFeedback(newsId) {
    const input = document.getElementById(`feedback-${newsId}`);
    const content = input.value.trim();
    
    if (!content) {
        alert('请输入反馈内容');
        return;
    }
    
    // 禁用按钮，显示加载状态
    const btn = input.nextElementSibling;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '处理中...';
    
    try {
        await apiCall('/api/feedback/text', {
            method: 'POST',
            body: JSON.stringify({ news_id: newsId, content: content })
        });
        
        input.value = '';
        alert('反馈已提交');
    } catch (error) {
        alert('提交失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// 显示导出弹窗
function showExportModal() {
    if (selectedNewsIds.size === 0) {
        alert('请选择要导出的新闻');
        return;
    }
    
    // 默认文档名称
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('export-name').value = `${today} LLM 新闻日报`;
    
    // 显示弹窗
    document.getElementById('export-modal').style.display = 'block';
}

// 关闭导出弹窗
function closeExportModal() {
    document.getElementById('export-modal').style.display = 'none';
}

// 确认导出
async function confirmExport() {
    const title = document.getElementById('export-name').value.trim();
    
    if (!title) {
        alert('请输入文档名称');
        return;
    }
    
    try {
        const result = await apiCall('/api/export', {
            method: 'POST',
            body: JSON.stringify({
                news_ids: Array.from(selectedNewsIds),
                title: title
            })
        });
        
        // 关闭弹窗
        closeExportModal();
        
        // 下载文件
        const blob = new Blob([result.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = result.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        alert('导出成功！');
    } catch (error) {
        alert('导出失败: ' + error.message);
    }
}

// ==================== 关键词管理页功能 ====================

// 加载关键词
async function loadKeywords() {
    try {
        const data = await apiCall('/api/keywords');
        
        // 更新统计
        const stats = data.stats || {};
        document.getElementById('total-feedback').textContent = stats.total || 0;
        document.getElementById('positive-count').textContent = stats.positive || 0;
        document.getElementById('negative-count').textContent = stats.negative || 0;
        
        // 渲染关键词列表
        renderKeywordsList(data.keywords || []);
    } catch (error) {
        console.error('加载关键词失败:', error);
    }
}

// 渲染关键词列表
function renderKeywordsList(keywords) {
    const container = document.getElementById('keywords-list');
    
    if (!keywords || keywords.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无关键词</div>';
        return;
    }
    
    container.innerHTML = keywords.map(kw => `
        <div class="keyword-row">
            <div style="display: flex; align-items: center;">
                <span class="keyword-name">${kw.keyword}</span>
                <span class="keyword-score ${kw.score > 0 ? 'positive' : kw.score < 0 ? 'negative' : ''}">${kw.score > 0 ? '+' : ''}${kw.score}</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <button onclick="editKeyword(${kw.id}, ${kw.score})" class="btn btn-ghost">
                    编辑
                </button>
                <button onclick="deleteKeyword(${kw.id})" class="btn btn-danger">
                    删除
                </button>
            </div>
        </div>
    `).join('');
}

// 编辑关键词
async function editKeyword(keywordId, currentScore) {
    const newScore = prompt('输入新的得分:', currentScore);
    if (newScore === null) return;
    
    const score = parseFloat(newScore);
    if (isNaN(score)) {
        alert('请输入有效的数字');
        return;
    }
    
    try {
        await apiCall(`/api/keywords/${keywordId}`, {
            method: 'PUT',
            body: JSON.stringify({ score: score })
        });
        loadKeywords();
    } catch (error) {
        alert('更新失败: ' + error.message);
    }
}

// 删除关键词
async function deleteKeyword(keywordId) {
    if (!confirm('确定要删除这个关键词吗？')) return;
    
    try {
        await apiCall(`/api/keywords/${keywordId}`, { method: 'DELETE' });
        loadKeywords();
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// ==================== 模型配置功能 ====================

// 打开配置弹窗
function openConfigModal() {
    document.getElementById('config-modal').style.display = 'flex';
    loadConfig();
}

// 关闭配置弹窗
function closeConfigModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('config-modal').style.display = 'none';
}

// 加载配置
async function loadConfig() {
    try {
        const data = await apiCall('/api/config');
        document.getElementById('config-provider').value = data.provider || '';
        document.getElementById('config-api-key').value = data.api_key || '';
        document.getElementById('config-api-url').value = data.api_url || '';
        document.getElementById('config-model-name').value = data.model_name || '';
    } catch (error) {
        console.error('加载配置失败:', error);
    }
}

// 保存配置
async function saveConfig() {
    const config = {
        provider: document.getElementById('config-provider').value.trim(),
        api_key: document.getElementById('config-api-key').value.trim(),
        api_url: document.getElementById('config-api-url').value.trim(),
        model_name: document.getElementById('config-model-name').value.trim()
    };

    try {
        await apiCall('/api/config', {
            method: 'PUT',
            body: JSON.stringify(config)
        });
        alert('配置保存成功');
        closeConfigModal();
    } catch (error) {
        alert('保存配置失败: ' + error.message);
    }
}
