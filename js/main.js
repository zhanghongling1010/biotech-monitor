// ===== Configuration =====
const CONFIG = {
    dataUrl: 'data/daily/latest.json',
    updateInterval: 300000,
    // Use local proxy server: python3 proxy.py
    proxyUrl: 'http://localhost:3000'
};

// ===== Analysis Cache =====
const ANALYSIS_CACHE_PREFIX = 'biotech_analysis_';
let pendingRequests = new Set(); // 防止重复请求
let serverCache = null; // 服务器端预生成的缓存

// 加载服务器端预生成的缓存
async function loadServerCache() {
    if (serverCache) return serverCache;
    try {
        const response = await fetch('data/daily/analysis_cache.json');
        if (response.ok) {
            serverCache = await response.json();
            console.log(`Loaded ${Object.keys(serverCache).length} pre-computed analyses`);
        }
    } catch (e) {
        console.log('No server cache available');
        serverCache = {};
    }
    return serverCache || {};
}

function getCachedAnalysis(key) {
    // 1. 优先检查 localStorage
    const local = localStorage.getItem(ANALYSIS_CACHE_PREFIX + key);
    if (local) {
        try {
            const parsed = JSON.parse(local);
            if (parsed && parsed.analysis && parsed.analysis.trim().length > 0) {
                return parsed;
            }
        } catch(e) {}
    }

    // 2. 检查服务器端预生成缓存
    if (serverCache && serverCache[key]) {
        return serverCache[key];
    }

    return null;
}

function setCachedAnalysis(key, analysis) {
    localStorage.setItem(ANALYSIS_CACHE_PREFIX + key, JSON.stringify(analysis));
}

// ===== AI Analysis Functions =====
async function generateDetailedAnalysis(cacheKey, prompt) {
    console.log('generateDetailedAnalysis called for:', cacheKey);

    // Check cache first (only return if has valid content)
    const cached = getCachedAnalysis(cacheKey);
    console.log('Cache check:', cached);
    if (cached && cached.analysis && cached.analysis.trim().length > 0) {
        console.log('Returning cached analysis');
        return cached;
    }

    // Clear invalid cache if exists
    if (cached) {
        localStorage.removeItem(ANALYSIS_CACHE_PREFIX + cacheKey);
        console.log('Cleared invalid empty cache');
    }

    // Prevent duplicate requests
    if (pendingRequests.has(ANALYSIS_CACHE_PREFIX + cacheKey)) {
        return null;
    }
    pendingRequests.add(ANALYSIS_CACHE_PREFIX + cacheKey);

    try {
        console.log('Calling AI proxy:', CONFIG.proxyUrl + '/v1/chat/completions');
        const response = await fetch(CONFIG.proxyUrl + '/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'MiniMax-M3',
                messages: [
                    {
                        role: 'system',
                        content: '你是一位资深的生物医药行业分析师，专注于基因编辑、细胞治疗、抗体药物偶联物(ADC)、GLP-1和肿瘤免疫领域。你的分析风格专业、深入、量化，具备产业视角。'
                    },
                    {
                        role: 'user',
                        content: prompt
                    }
                ],
                max_tokens: 2000,
                temperature: 0.7
            })
        });

        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', JSON.stringify(data).substring(0, 500));

        if (!response.ok) {
            throw new Error(`API error: ${response.status} - ${JSON.stringify(data)}`);
        }

        const analysis = data.choices?.[0]?.message?.content || '';

        // Cache the result
        const result = {
            analysis: analysis,
            timestamp: Date.now()
        };
        setCachedAnalysis(cacheKey, result);

        return result;

    } catch (error) {
        console.error('AI Analysis error:', error);
        // 显示错误到页面
        const errEl = document.getElementById('aiAnalysisStatus');
        if (errEl) {
            errEl.textContent = '错误: ' + (error.message || 'unknown');
            errEl.style.color = '#dc2626';
            errEl.style.fontSize = '0.7rem';
        }
        return null;
    } finally {
        pendingRequests.delete(ANALYSIS_CACHE_PREFIX + cacheKey);
    }
}

let currentSection = 'today';
let currentFilter = 'all';
let currentCompanyType = 'international';
let allData = null;
let currentModalItem = null;

// ===== Initialize =====
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initFilters();
    initCompanyTabs();
    loadData();
    setInterval(loadData, CONFIG.updateInterval);
});

// ===== Navigation =====
function initNavigation() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            showSection(tab.dataset.section);
        });
    });
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(sectionId)?.classList.add('active');
    currentSection = sectionId;
}

// ===== Filters =====
function initFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
        });
    });
}

// ===== Company Tabs =====
function initCompanyTabs() {
    document.querySelectorAll('.company-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.company-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentCompanyType = tab.dataset.type;
            renderCompanies();
        });
    });
}

// ===== Data Loading =====
async function loadData() {
    try {
        const response = await fetch(CONFIG.dataUrl);
        if (!response.ok) throw new Error('Network response was not ok');
        allData = await response.json();

        // 加载预生成的 AI 分析缓存
        await loadServerCache();

        updateLastUpdate(allData.timestamp);
        renderCritical(allData);
        renderDailyBrief(allData);
        renderPapersBySection(allData);
        renderCompanies();
        renderEarnings();
    } catch (error) {
        console.error('Failed to load data:', error);
        loadSampleData();
    }
}

function updateLastUpdate(timestamp) {
    if (!timestamp) return;
    const date = new Date(timestamp);
    const formatted = date.toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    });
    document.getElementById('lastUpdate').textContent = `最后更新: ${formatted}`;
}

// ===== Render Critical Today =====
function renderCritical(data) {
    const container = document.getElementById('criticalCards');
    if (!container) return;

    const items = [
        ...(data.critical?.deals || []).map(d => ({...d, _type: 'deal', _tag: 'BD交易'})),
        ...(data.critical?.clinical || []).map(c => ({...c, _type: 'clinical', _tag: '临床进展'})),
        ...(data.critical?.approvals || []).map(a => ({...a, _type: 'approval', _tag: '监管批准'}))
    ];

    if (items.length === 0) {
        container.innerHTML = '<div class="empty-state">今日无重大事件</div>';
        return;
    }

    container.innerHTML = items.map((item, idx) => `
        <div class="alert-card ${item.priority === 'critical' ? 'critical' : 'warning'}" onclick="openModal('critical', ${idx})">
            <div class="card-header">
                <span class="tag ${item._type}">${item._tag}</span>
                <div class="header-right">
                    ${item.company ? `<span class="companies">${item.company}</span>` : ''}
                    <span class="date">${formatDate(item.date || item.pub_date)}</span>
                    <span class="expand-icon">▶</span>
                </div>
            </div>
            <h4>${item.title || item.title_cn || '无标题'}</h4>
            ${item.description_cn ? `<p class="preview">${item.description_cn}</p>` : ''}
        </div>
    `).join('');
}

// ===== Render Daily Brief =====
function renderDailyBrief(data) {
    // Deals
    const dealsList = document.getElementById('dealsList');
    const deals = data.daily?.deals || [];
    if (deals.length === 0) {
        dealsList.innerHTML = '<div class="empty-card">暂无新交易</div>';
    } else {
        dealsList.innerHTML = deals.map((d, i) => `
            <div class="brief-item" onclick="openModal('deal', ${i})">
                <div class="brief-item-header">
                    <span class="item-title">${d.title || d.title_cn || '无标题'}</span>
                    <span class="expand-icon">▶</span>
                </div>
                <div class="brief-item-meta">
                    ${d.company ? `<span>${d.company}</span>` : ''}
                    ${d.value ? `<span class="value">${d.value}</span>` : ''}
                    ${d.date ? `<span class="date">${formatDate(d.date)}</span>` : ''}
                </div>
                ${d.description_cn ? `<p class="preview">${d.description_cn}</p>` : ''}
            </div>
        `).join('');
    }

    // Clinical
    const clinicalList = document.getElementById('clinicalList');
    const clinical = data.daily?.clinical || [];
    if (clinical.length === 0) {
        clinicalList.innerHTML = '<div class="empty-card">暂无临床进展</div>';
    } else {
        clinicalList.innerHTML = clinical.map((c, i) => `
            <div class="brief-item" onclick="openModal('clinical', ${i})">
                <div class="brief-item-header">
                    <span class="item-title">${c.title || c.title_cn || '无标题'}</span>
                    <span class="expand-icon">▶</span>
                </div>
                <div class="brief-item-meta">
                    ${c.company ? `<span>${c.company}</span>` : ''}
                    ${c.indication ? `<span>${c.indication}</span>` : ''}
                    ${c.stage ? `<span class="stage">${c.stage}</span>` : ''}
                </div>
                ${c.description_cn ? `<p class="preview">${c.description_cn}</p>` : ''}
            </div>
        `).join('');
    }

    // Research - Papers from all categories
    const researchList = document.getElementById('researchList');
    const allPapers = [];
    for (const [cat, papers] of Object.entries(data.papers || {})) {
        allPapers.push(...(papers || []).slice(0, 3));
    }
    if (allPapers.length === 0) {
        researchList.innerHTML = '<div class="empty-card">暂无新文献</div>';
    } else {
        researchList.innerHTML = allPapers.slice(0, 10).map((p, i) => `
            <div class="brief-item paper-item" onclick="openModal('paper', ${i})">
                <div class="brief-item-header">
                    <span class="item-title">${p.title_cn || p.title || '无标题'}</span>
                    <span class="expand-icon">▶</span>
                </div>
                <div class="brief-item-meta">
                    <span class="journal">${p.journal || '未知期刊'}</span>
                    ${p.date ? `<span class="date">${p.date}</span>` : ''}
                </div>
                ${p.summary_cn ? `<p class="preview">${p.summary_cn}</p>` : ''}
            </div>
        `).join('');
    }
}

// ===== Render Papers by Section =====
function renderPapersBySection(data) {
    renderPaperSection('geneEditingPapers', data.papers?.gene_editing || []);
    renderPaperSection('cellTherapyPapers', data.papers?.cell_therapy || []);
    renderPaperSection('ADCPapers', data.papers?.adc || []);
    renderPaperSection('GLP1Papers', data.papers?.glp1 || []);
    renderPaperSection('IOPapers', data.papers?.io || []);
    // 递送系统专题（包含 LNP、AAV、纳米、外泌体等）
    renderDeliverySection('deliveryPapers', data.papers?.delivery_systems || []);
}

function renderDeliverySection(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<div class="empty-card">暂无递送系统相关文献</div>';
        return;
    }

    // 按递送类型分组
    const typeLabels = {
        'lnp': '🧪 LNP',
        'aav': '🦠 AAV',
        'exosome': '📦 外泌体',
        'vlp': '🔬 VLP',
        'nanoparticle': '⚛️ 纳米',
        'lentivirus': '🦠 慢病毒',
        'adenovirus': '🦠 腺病毒',
        'electroporation': '⚡ 电穿孔',
        'other': '💊 其他'
    };

    container.innerHTML = items.slice(0, 15).map(p => {
        const types = p.delivery_types || ['other'];
        const typeTag = types.map(t => typeLabels[t] || t).join(' ');
        const analysisBadge = p.analysis_available
            ? '<span style="background:#16a34a;color:white;padding:1px 6px;border-radius:3px;font-size:0.65rem;margin-left:0.5rem;">✓ AI</span>'
            : '';

        return `
            <div class="paper-card" onclick='openPaperDetail(${JSON.stringify(p).replace(/'/g, "\\'")})'>
                <div class="paper-header">
                    <h4>${p.title || '无标题'}</h4>
                    ${analysisBadge}
                </div>
                <div class="paper-meta">
                    <span class="delivery-tags">${typeTag}</span>
                    <span class="journal">${p.journal || ''}</span>
                    <span class="date">${formatDate(p.date)}</span>
                </div>
                <p class="preview">${(p.abstract || '').substring(0, 150)}...</p>
            </div>
        `;
    }).join('');
}

function renderPaperSection(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<div class="empty-card">暂无相关文献</div>';
        return;
    }

    container.innerHTML = items.map(paper => `
        <div class="paper-card" onclick="openPaperDetail(${JSON.stringify(paper).replace(/"/g, '&quot;')})">
            <div class="paper-journal">${paper.journal || '期刊'}</div>
            <h4>${paper.title || '无标题'}</h4>
            <div class="authors">${(paper.authors || []).slice(0, 3).join(', ')}${(paper.authors || []).length > 3 ? ' et al.' : ''}</div>
            ${paper.summary_cn ? `<p class="abstract">${paper.summary_cn}</p>` : paper.abstract_cn ? `<p class="abstract">${paper.abstract_cn}</p>` : paper.abstract ? `<p class="abstract">${paper.abstract}</p>` : ''}
            <div class="tags">
                ${(paper.keywords || []).slice(0, 4).map(k => `<span class="tag">${k}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

// ===== Render Companies =====
function renderCompanies() {
    const container = document.getElementById('companyGrid');
    if (!container || !allData) return;

    const companies = allData.companies?.[currentCompanyType] || [];
    if (companies.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无公司数据</div>';
        return;
    }

    container.innerHTML = companies.map((company, index) => `
        <div class="company-card" onclick="openCompanyDetail(${index})" style="cursor:pointer;">
            <div class="ticker">${company.ticker || company.code || ''}</div>
            <h4>${company.name || ''}</h4>
            <div class="company-type">${company.type || company.focus || ''}</div>
            <div class="status">
                ${company.pipeline ? '<span class="status-item pipeline">Pipeline</span>' : ''}
                ${company.news ? '<span class="status-item news">News</span>' : ''}
                ${company.paper ? '<span class="status-item paper">Paper</span>' : ''}
            </div>
        </div>
    `).join('');
}

// ===== Open Company Detail =====
function openCompanyDetail(companyIndex) {
    const companies = allData.companies?.[currentCompanyType] || [];
    const company = companies[companyIndex];
    if (!company) return;

    const companyName = company.name || '';
    const companyTicker = company.ticker || company.code || '';

    // Find related news, deals, clinical from daily data
    const relatedDeals = (allData.daily?.deals || []).filter(d =>
        (d.company && (d.company.toLowerCase().includes(companyName.toLowerCase()) ||
                       d.company.toLowerCase().includes(companyTicker.toLowerCase()))) ||
        (d.companies && d.companies.some(c =>
            c.toLowerCase().includes(companyName.toLowerCase()) ||
            c.toLowerCase().includes(companyTicker.toLowerCase())
        ))
    );

    const relatedClinical = (allData.daily?.clinical || []).filter(c =>
        (c.company && (c.company.toLowerCase().includes(companyName.toLowerCase()) ||
                       c.company.toLowerCase().includes(companyTicker.toLowerCase()))) ||
        (c.companies && c.companies.some(c =>
            c.toLowerCase().includes(companyName.toLowerCase()) ||
            c.toLowerCase().includes(companyTicker.toLowerCase())
        ))
    );

    // Find related papers
    const allPapers = [];
    for (const [cat, papers] of Object.entries(allData.papers || {})) {
        allPapers.push(...(papers || []).map(p => ({...p, _category: cat})));
    }
    const relatedPapers = allPapers.filter(p =>
        (p.companies && p.companies.some(c =>
            c.toLowerCase().includes(companyName.toLowerCase()) ||
            c.toLowerCase().includes(companyTicker.toLowerCase())
        ))
    );

    // Build content for AI analysis
    let relatedContent = '';
    if (relatedDeals.length > 0) {
        relatedContent += '\n【相关BD交易】\n';
        relatedDeals.forEach(d => {
            relatedContent += `- ${d.title || d.title_cn || 'N/A'}\n  公司: ${d.company || 'N/A'}\n  金额: ${d.value || '未披露'}\n  日期: ${d.date || 'N/A'}\n  详情: ${d.description_cn || d.description || 'N/A'}\n\n`;
        });
    }
    if (relatedClinical.length > 0) {
        relatedContent += '\n【相关临床进展】\n';
        relatedClinical.forEach(c => {
            relatedContent += `- ${c.title || c.title_cn || 'N/A'}\n  公司: ${c.company || 'N/A'}\n  阶段: ${c.stage || 'N/A'}\n  适应症: ${c.indication || 'N/A'}\n  详情: ${c.description_cn || c.description || 'N/A'}\n\n`;
        });
    }
    if (relatedPapers.length > 0) {
        relatedContent += '\n【相关科研论文】\n';
        relatedPapers.slice(0, 5).forEach(p => {
            relatedContent += `- ${p.title || 'N/A'}\n  期刊: ${p.journal || 'N/A'}\n  日期: ${p.date || 'N/A'}\n  摘要: ${p.abstract ? p.abstract.substring(0, 300) + '...' : 'N/A'}\n\n`;
        });
    }

    // Open modal with company info
    const modal = document.getElementById('detailModal');
    if (!modal) return;

    document.getElementById('modalTag').textContent = '公司监控';
    document.getElementById('modalTag').className = 'modal-tag clinical';
    document.getElementById('modalTitle').textContent = `${companyTicker} - ${companyName}`;
    document.getElementById('modalLink').style.display = 'none';

    let metaHtml = '';
    if (company.type) metaHtml += `<span class="modal-meta-item"><strong>业务类型:</strong> ${company.type}</span>`;
    if (company.pipeline) metaHtml += `<span class="modal-meta-item"><strong>管线更新:</strong> 有</span>`;
    if (company.news) metaHtml += `<span class="modal-meta-item"><strong>最新新闻:</strong> 有</span>`;
    if (company.paper) metaHtml += `<span class="modal-meta-item"><strong>相关论文:</strong> 有</span>`;
    metaHtml += `<span class="modal-meta-item"><strong>相关BD交易:</strong> ${relatedDeals.length}条</span>`;
    metaHtml += `<span class="modal-meta-item"><strong>相关临床:</strong> ${relatedClinical.length}条</span>`;
    metaHtml += `<span class="modal-meta-item"><strong>相关论文:</strong> ${relatedPapers.length}篇</span>`;
    document.getElementById('modalMeta').innerHTML = metaHtml;

    let cnContent = '<h3 style="margin-bottom:1rem;">公司动态概览</h3>';

    if (relatedContent) {
        cnContent += `<p style="color:#64748b;margin-bottom:1.5rem;">找到 ${relatedDeals.length} 条相关BD交易、${relatedClinical.length} 条临床进展、${relatedPapers.length} 篇论文</p>`;
    } else {
        cnContent += `<p style="color:#64748b;margin-bottom:1.5rem;">暂无相关动态记录</p>`;
    }

    // AI analysis prompt
    const cacheKey = 'company_' + companyTicker + '_' + (companyName || '');

    // Generate AI analysis
    const analysisPrompt = `请为以下${companyName}(${companyTicker})公司的最新动态提供专业的中文深度分析，使用生物医药行业分析师的风格。

【公司信息】
公司名称: ${companyName}
股票代码: ${companyTicker}
业务类型: ${company.type || 'N/A'}

${relatedContent ? '【公司动态汇总】\n' + relatedContent : '【暂无动态记录】'}

请按以下格式输出详细分析：

【公司概况】
基于现有信息分析公司的核心业务和市场地位

【近期动态解读】
对相关BD交易、临床进展、论文进行综合分析

【管线价值评估】
如果有管线更新，分析其对公司的价值影响

【投资关注点】
从投资者角度的关键关注点

【风险提示】
潜在的风险因素

只用中文输出以上内容，每部分用【】标注。`;

    const cached = getCachedAnalysis(cacheKey);
    if (cached && cached.analysis && cached.analysis.trim().length > 0) {
        cnContent += `<div style="margin-top:1.5rem; padding:1rem; background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 100%); border-radius:12px; border-left:4px solid #16a34a;">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem;">
                <span style="background:#16a34a;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;">AI 深度解读</span>
                <span style="color:#64748b;font-size:0.75rem;">已缓存 · 即时显示</span>
            </div>
            <div style="white-space:pre-wrap; line-height:1.7; font-size:0.9rem;">${cached.analysis.replace(/\n/g, '<br>').replace(/【([^】]+)】/g, '<strong style="color:#16a34a;">[$1]</strong> ')}</div>
        </div>`;
    } else {
        cnContent += `<div id="aiAnalysisLoading" style="margin-top:1.5rem; padding:1rem; background:#f8fafc; border-radius:12px; border-left:4px solid #3b82f6;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                <span style="background:#3b82f6;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;">AI 深度解读</span>
                <span id="aiAnalysisStatus" style="color:#64748b;font-size:0.75rem;">检查缓存...</span>
            </div>
            <div style="margin-top:1rem;">
                <div style="display:flex;align-items:center;gap:0.5rem;color:#64748b;font-size:0.85rem;">
                    <div style="width:16px;height:16px;border:2px solid #3b82f6;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite;"></div>
                    加载中...
                </div>
            </div>
        </div>`;

        // 先尝试刷新服务器缓存
        setTimeout(async () => {
            await loadServerCache();
            const retryCached = getCachedAnalysis(cacheKey);
            if (retryCached && retryCached.analysis && retryCached.analysis.trim().length > 0) {
                const analysisHtml = `<div style="margin-top:1.5rem; padding:1rem; background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 100%); border-radius:12px; border-left:4px solid #16a34a;">
                    <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem;">
                        <span style="background:#16a34a;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;">AI 深度解读</span>
                        <span style="color:#64748b;font-size:0.75rem;">已缓存</span>
                    </div>
                    <div style="white-space:pre-wrap; line-height:1.7; font-size:0.9rem;">${retryCached.analysis.replace(/\n/g, '<br>').replace(/【([^】]+)】/g, '<strong style="color:#16a34a;">[$1]</strong> ')}</div>
                </div>`;
                const loadingEl = document.getElementById('aiAnalysisLoading');
                if (loadingEl) loadingEl.outerHTML = analysisHtml;
            } else {
                // 服务器也没有 - 显示友好提示（不在 GitHub Pages 上调用本地 API）
                const loadingEl2 = document.getElementById('aiAnalysisLoading');
                if (loadingEl2) {
                    loadingEl2.outerHTML = `<div style="margin-top:1.5rem; padding:1rem; background:#fef9c3; border-radius:12px; border-left:4px solid #eab308;">
                        <div style="display:flex; align-items:center; gap:0.5rem;">
                            <span style="background:#eab308;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;">AI 解读</span>
                            <span style="color:#64748b;font-size:0.85rem;">暂未预生成，每日 7:00 自动更新</span>
                        </div>
                    </div>`;
                }
            }
        }, 300);
        return;
    }

    document.getElementById('modalCnContent').innerHTML = cnContent;
    document.getElementById('modalEnContent').innerHTML = '<p style="color:#64748b;">无英文原文</p>';

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// ===== Render Earnings =====
function renderEarnings() {
    const container = document.getElementById('earningsList');
    if (!container || !allData) return;

    const earnings = allData.earnings || [];
    if (earnings.length === 0) {
        container.innerHTML = '<li>暂无财报发布计划</li>';
        return;
    }

    const today = new Date();
    const weekFromNow = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);

    container.innerHTML = earnings.map(e => {
        const date = new Date(e.date);
        const isSoon = date <= weekFromNow;
        return `
            <li>
                <span class="${isSoon ? 'soon' : ''}">${e.company} (${e.ticker})</span>
                <span class="date ${isSoon ? 'soon' : ''}">${e.date} ${e.exchange || ''}</span>
            </li>
        `;
    }).join('');
}

// ===== Modal Functions =====
let modalData = {
    critical: [],
    deals: [],
    clinical: [],
    papers: []
};

function openModal(type, index) {
    if (!allData) return;

    const modal = document.getElementById('detailModal');
    if (!modal) return;

    let item = null;
    let tag = '';
    let typeClass = '';

    switch(type) {
        case 'critical':
            const criticalItems = [
                ...(allData.critical?.deals || []).map(d => ({...d, _type: 'deal', _tag: 'BD交易'})),
                ...(allData.critical?.clinical || []).map(c => ({...c, _type: 'clinical', _tag: '临床进展'})),
                ...(allData.critical?.approvals || []).map(a => ({...a, _type: 'approval', _tag: '监管批准'}))
            ];
            item = criticalItems[index];
            tag = item?._tag || '';
            typeClass = item?._type || '';
            break;
        case 'deal':
            item = allData.daily?.deals?.[index];
            tag = 'BD交易';
            typeClass = 'deal';
            break;
        case 'clinical':
            item = allData.daily?.clinical?.[index];
            tag = '临床进展';
            typeClass = 'clinical';
            break;
        case 'paper':
            const allPapers = [];
            for (const [cat, papers] of Object.entries(allData.papers || {})) {
                allPapers.push(...(papers || []));
            }
            item = allPapers[index];
            tag = '科研文献';
            typeClass = 'clinical';
            break;
    }

    if (!item) return;

    // Set modal content
    document.getElementById('modalTag').textContent = tag;
    document.getElementById('modalTag').className = 'modal-tag ' + typeClass;

    // Title - show English title
    const title = item.title || item.title_cn || '无标题';
    document.getElementById('modalTitle').textContent = title;

    // Meta info
    let metaHtml = '';
    if (item.company) metaHtml += `<span class="modal-meta-item"><strong>公司:</strong> ${item.company}</span>`;
    if (item.companies?.length) metaHtml += `<span class="modal-meta-item"><strong>涉及公司:</strong> ${item.companies.join(', ')}</span>`;
    if (item.value) metaHtml += `<span class="modal-meta-item"><strong>交易金额:</strong> ${item.value}</span>`;
    if (item.indication) metaHtml += `<span class="modal-meta-item"><strong>适应症:</strong> ${item.indication}</span>`;
    if (item.stage) metaHtml += `<span class="modal-meta-item"><strong>临床阶段:</strong> ${item.stage}</span>`;
    if (item.date || item.pub_date) metaHtml += `<span class="modal-meta-item"><strong>日期:</strong> ${formatDate(item.date || item.pub_date)}</span>`;
    if (item.source) metaHtml += `<span class="modal-meta-item"><strong>来源:</strong> ${item.source}</span>`;
    if (item.journal) metaHtml += `<span class="modal-meta-item"><strong>期刊:</strong> ${item.journal}</span>`;
    if (item.pmid) metaHtml += `<span class="modal-meta-item"><strong>PMID:</strong> ${item.pmid}</span>`;
    if (item.authors?.length) metaHtml += `<span class="modal-meta-item"><strong>作者:</strong> ${item.authors.slice(0, 5).join(', ')}${item.authors.length > 5 ? ' et al.' : ''}</span>`;
    document.getElementById('modalMeta').innerHTML = metaHtml || '<span class="modal-meta-item">无详细信息</span>';

    // Chinese content - detailed (handle structured content with line breaks)
    let cnContent = '';
    if (item.description_cn) {
        // Convert newlines and section markers to formatted HTML
        cnContent += item.description_cn.replace(/\n/g, '<br>').replace(/【([^】]+)】/g, '<strong style="color:#166534;">[$1]</strong> ');
    } else if (item.summary_cn) {
        cnContent += item.summary_cn.replace(/\n/g, '<br>').replace(/【([^】]+)】/g, '<strong style="color:#166534;">[$1]</strong> ');
    }
    if (item.abstract_cn && item.abstract_cn !== item.summary_cn) {
        cnContent += `<div style="margin-top:1rem;"><strong style="color:#166534;">【详细中文摘要】</strong><br>${item.abstract_cn.replace(/\n/g, '<br>').replace(/【([^】]+)】/g, '<strong>[$1]</strong> ')}</div>`;
    }

    // Add AI analysis for all types (papers, deals, clinical, approvals)
    // For critical items, use _type to determine actual content type
    const actualType = (type === 'critical' && item._type) ? item._type : type;
    let cacheKey;
    if (item.pmid) {
        cacheKey = 'paper_' + item.pmid;
    } else if (actualType === 'paper' || !actualType || actualType === 'unknown') {
        cacheKey = 'paper_' + (item.title || '') + '_' + (item.date || '');
    } else {
        cacheKey = actualType + '_' + (item.title || '') + '_' + (item.date || item.pub_date || '');
    }
    const contentType = actualType || 'unknown';

    console.log('AI Analysis Check:', { cacheKey, contentType, originalType: type });

    // Generate appropriate prompt based on content type
    let analysisPrompt = '';
    if (contentType === 'paper' && item.abstract) {
        analysisPrompt = `请为以下生物医学论文提供详细的中文深度解读，使用专业分析师的风格。

【论文信息】
PMID: ${item.pmid || 'N/A'}
标题: ${item.title || item.title_cn || 'N/A'}
期刊: ${item.journal || 'N/A'}
发表日期: ${item.date || 'N/A'}
作者: ${(item.authors || []).slice(0, 5).join(', ')}${(item.authors || []).length > 5 ? ' et al.' : ''}

【原始摘要】
${item.abstract}

请按以下格式输出详细解读（如果某项信息不足则跳过）：

【研究背景与科学问题】
2-3句话描述研究背景和要解决的科学问题

【实验设计】
使用的方法、模型、技术路线、主要技术

【关键数据】
所有量化数据、统计学结果

【核心发现】
主要结论、创新点

【机制解析】
分子机制、信号通路

【产业意义】
对临床治疗的潜在影响、对biotech公司的意义

【局限性】
研究的不足之处

只用中文输出以上内容，每部分用【】标注。如果摘要信息不足，请基于已有信息尽量分析。`;
    } else if ((contentType === 'deal' || contentType === 'approval') && (item.description || item.description_cn || item.title)) {
        analysisPrompt = `请为以下BD交易/监管动态提供专业的中文深度分析，使用生物医药行业分析师的风格。

【交易信息】
标题: ${item.title || item.title_cn || 'N/A'}
公司: ${item.company || 'N/A'}
交易金额: ${item.value || '未披露'}
日期: ${item.date || item.pub_date || 'N/A'}
来源: ${item.source || 'N/A'}

【内容详情】
${item.description || item.description_cn || '无详细信息'}

请按以下格式输出详细分析：

【交易概况】
交易的简要说明和主要条款

【战略意义】
这笔交易对双方公司的战略价值

【行业影响】
对整个生物医药行业的潜在影响

【投资亮点】
从投资者角度的关键关注点

【风险提示】
潜在的风险因素

只用中文输出以上内容，每部分用【】标注。`;
    } else if ((contentType === 'approval' || contentType === 'deal') && (item.description || item.description_cn || item.title)) {
        // Use deal prompt for approvals as well
        analysisPrompt = `请为以下监管动态/BD交易提供专业的中文深度分析，使用生物医药行业分析师的风格。

【交易信息】
标题: ${item.title || item.title_cn || 'N/A'}
公司: ${item.company || 'N/A'}
交易金额: ${item.value || '未披露'}
日期: ${item.date || item.pub_date || 'N/A'}
来源: ${item.source || 'N/A'}

【内容详情】
${item.description || item.description_cn || '无详细信息'}

请按以下格式输出详细分析：

【交易概况】
交易的简要说明和主要条款

【战略意义】
这笔交易对双方公司的战略价值

【行业影响】
对整个生物医药行业的潜在影响

【投资亮点】
从投资者角度的关键关注点

【风险提示】
潜在的风险因素

只用中文输出以上内容，每部分用【】标注。`;
    } else if (contentType === 'clinical' && (item.description || item.description_cn || item.title)) {
        analysisPrompt = `请为以下临床进展提供专业的中文深度分析，使用生物医药行业分析师的风格。

【临床信息】
标题: ${item.title || item.title_cn || 'N/A'}
公司: ${item.company || 'N/A'}
适应症: ${item.indication || 'N/A'}
临床阶段: ${item.stage || 'N/A'}
日期: ${item.date || item.pub_date || 'N/A'}
来源: ${item.source || 'N/A'}

【内容详情】
${item.description || item.description_cn || '无详细信息'}

请按以下格式输出详细分析：

【临床概况】
试验的基本信息和设计

【数据解读】
关键临床数据和分析

【竞争格局】
同类产品在研情况对比

【上市前景】
获批可能性和商业化潜力

【投资要点】
从投资者角度的关键关注点

只用中文输出以上内容，每部分用【】标注。`;
    }

    // Show AI analysis section if we have content to analyze
    if (analysisPrompt) {
        const cached = getCachedAnalysis(cacheKey);

        if (cached && cached.analysis && cached.analysis.trim().length > 0) {
            // Show cached analysis immediately
            cnContent += `<div style="margin-top:1.5rem; padding:1rem; background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 100%); border-radius:12px; border-left:4px solid #16a34a;">
                <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem;">
                    <span style="background:#16a34a;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;">AI 深度解读</span>
                    <span style="color:#64748b;font-size:0.75rem;">已缓存 · 即时显示</span>
                </div>
                <div style="white-space:pre-wrap; line-height:1.7; font-size:0.9rem;">${cached.analysis.replace(/\n/g, '<br>').replace(/【([^】]+)】/g, '<strong style="color:#16a34a;">[$1]</strong> ')}</div>
            </div>`;
        } else {
            // Show loading and trigger AI analysis
            cnContent += `<div id="aiAnalysisLoading" style="margin-top:1.5rem; padding:1rem; background:#f8fafc; border-radius:12px; border-left:4px solid #3b82f6;">
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span style="background:#3b82f6;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;">AI 深度解读</span>
                    <span id="aiAnalysisStatus" style="color:#64748b;font-size:0.75rem;">正在生成...</span>
                </div>
                <div style="margin-top:1rem;">
                    <div style="display:flex;align-items:center;gap:0.5rem;color:#64748b;font-size:0.85rem;">
                        <div style="width:16px;height:16px;border:2px solid #3b82f6;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite;"></div>
                        首次生成需3-5秒，之后即时显示
                    </div>
                </div>
            </div>`;

            // Trigger AI analysis (async)
            setTimeout(async () => {
                const result = await generateDetailedAnalysis(cacheKey, analysisPrompt);
                if (result && result.analysis) {
                    const analysisHtml = `<div style="margin-top:1.5rem; padding:1rem; background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 100%); border-radius:12px; border-left:4px solid #16a34a;">
                        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem;">
                            <span style="background:#16a34a;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;">AI 深度解读</span>
                            <span style="color:#64748b;font-size:0.75rem;">已生成</span>
                        </div>
                        <div style="white-space:pre-wrap; line-height:1.7; font-size:0.9rem;">${result.analysis.replace(/\n/g, '<br>').replace(/【([^】]+)】/g, '<strong style="color:#16a34a;">[$1]</strong> ')}</div>
                    </div>`;

                    const loadingEl = document.getElementById('aiAnalysisLoading');
                    if (loadingEl) {
                        loadingEl.outerHTML = analysisHtml;
                    }
                } else {
                    const statusEl = document.getElementById('aiAnalysisStatus');
                    if (statusEl) {
                        statusEl.textContent = '生成失败，请查看Console错误';
                        statusEl.style.color = '#dc2626';
                    }
                }
            }, 100);
        }
    }

    if (!cnContent) cnContent = '<p style="color:#64748b;">暂无中文详情</p>';
    document.getElementById('modalCnContent').innerHTML = cnContent;

    // English content - clean display
    let enContent = '';
    if (item.title) enContent += `<p><strong>Title:</strong> ${item.title}</p>`;
    if (item.description) enContent += `<p style="margin-top:0.5rem;"><strong>Content:</strong> ${item.description.replace(/\.\.\./g, '').substring(0, 500)}${item.description.length > 500 ? '...' : ''}</p>`;
    if (item.abstract) enContent += `<p style="margin-top:0.5rem;"><strong>Abstract:</strong> ${item.abstract.substring(0, 600)}${item.abstract.length > 600 ? '...' : ''}</p>`;
    if (!enContent) enContent = '<p style="color:#64748b;">No original content available</p>';
    document.getElementById('modalEnContent').innerHTML = enContent;

    // Link
    const linkEl = document.getElementById('modalLink');
    if (item.link) {
        linkEl.href = item.link;
        linkEl.textContent = '阅读原文 →';
        linkEl.style.display = 'inline-block';
    } else if (item.pmid) {
        linkEl.href = `https://pubmed.ncbi.nlm.nih.gov/${item.pmid}/`;
        linkEl.textContent = '在 PubMed 查看 →';
        linkEl.style.display = 'inline-block';
    } else {
        linkEl.style.display = 'none';
    }

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function openPaperDetail(paper) {
    if (!paper) return;

    // Find paper index in allPapers array
    const allPapers = [];
    for (const [cat, papers] of Object.entries(allData?.papers || {})) {
        allPapers.push(...(papers || []));
    }
    const paperIndex = allPapers.findIndex(p => (p.pmid || p.title) === (paper.pmid || paper.title));

    currentModalItem = paper;
    openModal('paper', paperIndex >= 0 ? paperIndex : 0);
}

function closeModal() {
    document.getElementById('detailModal')?.classList.remove('active');
    document.body.style.overflow = '';
}

// Close modal events
document.addEventListener('click', (e) => {
    if (e.target.id === 'detailModal') closeModal();
});
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// ===== Helper Functions =====
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
    } catch {
        return dateStr;
    }
}

// ===== Sample Data =====
function loadSampleData() {
    const sampleData = {
        timestamp: new Date().toISOString(),
        critical: {
            deals: [
                { title: 'BMS与Prime Medicine达成25亿美元合作', company: 'Bristol Myers Squibb / Prime Medicine', value: '$2.5B', date: '2026-06-18', priority: 'critical', description_cn: '百时美施贵宝(BMS)与Prime Medicine宣布达成总额25亿美元的战略合作，共同开发体内基因编辑疗法。根据协议，BMS将支付预付款及里程金，合作将聚焦于多个治疗领域的基因编辑药物开发。' }
            ],
            clinical: [],
            approvals: []
        },
        daily: {
            deals: [],
            clinical: [],
            research: []
        },
        papers: {
            gene_editing: [{ title: 'Prime editing for hemoglobinopathies', journal: 'Nature Biotechnology', abstract: 'Demonstration of high-efficiency prime editing...', abstract_cn: '本研究展示了在人类造血干细胞中进行高效先导编辑，用于治疗镰状细胞病和β-地中海贫血。研究人员开发了一种新的先导编辑系统，实现了前所未有的编辑效率，为基因治疗开辟了新途径。', authors: ['Anzalone AV', 'Gao XD'], keywords: ['Prime Editing', 'Hematology'] }],
            cell_therapy: [],
            adc: [],
            glp1: [],
            io: []
        },
        companies: {
            international: [{ ticker: 'BEAM', name: 'Beam Therapeutics', type: 'Base/Prime Editing', pipeline: true, news: true }],
            china: []
        },
        earnings: []
    };
    updateLastUpdate(sampleData.timestamp);
    renderCritical(sampleData);
    renderDailyBrief(sampleData);
    renderPapersBySection(sampleData);
    renderCompanies();
    renderEarnings();
}
