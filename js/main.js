// ===== Configuration =====
const CONFIG = {
    dataUrl: 'data/daily/latest.json',
    updateInterval: 300000 // 5 minutes
};

// ===== State =====
let currentSection = 'today';
let currentFilter = 'all';
let currentCompanyType = 'international';

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
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const section = tab.dataset.section;
            showSection(section);
        });
    });
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
    currentSection = sectionId;
}

// ===== Filters =====
function initFilters() {
    const filters = document.querySelectorAll('.filter-btn');
    filters.forEach(btn => {
        btn.addEventListener('click', () => {
            filters.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderPapers();
        });
    });
}

// ===== Company Tabs =====
function initCompanyTabs() {
    const tabs = document.querySelectorAll('.company-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
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
        const data = await response.json();
        updateLastUpdate(data.timestamp);
        renderCritical(data);
        renderDailyBrief(data);
        renderPapersBySection(data);
        renderCompaniesByType(data);
        renderEarnings(data);
    } catch (error) {
        console.error('Failed to load data:', error);
        // Try loading sample data for demo
        loadSampleData();
    }
}

function updateLastUpdate(timestamp) {
    const date = new Date(timestamp);
    const formatted = date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
    document.getElementById('lastUpdate').textContent = `最后更新: ${formatted}`;
}

// ===== Render Critical Today =====
function renderCritical(data) {
    const container = document.getElementById('criticalCards');

    const items = [
        ...(data.critical?.deals || []).map(d => ({...d, type: 'deal', tag: 'BD交易'})),
        ...(data.critical?.clinical || []).map(c => ({...c, type: 'clinical', tag: '临床进展'})),
        ...(data.critical?.approvals || []).map(a => ({...a, type: 'approval', tag: '监管批准'}))
    ];

    if (items.length === 0) {
        container.innerHTML = '<div class="empty-state">今日无重大事件</div>';
        return;
    }

    container.innerHTML = items.map((item, idx) => `
        <div class="alert-card ${item.priority === 'critical' ? 'critical' : 'warning'}" onclick="toggleDetail('critical-${idx}')">
            <div class="card-header">
                <span class="tag ${item.type}">${item.tag}</span>
                <div class="header-right">
                    ${item.companies?.length ? `<span class="companies">${item.companies.join(', ')}</span>` : ''}
                    <span class="date">${formatDate(item.date || item.pub_date || '')}</span>
                    <span class="expand-icon">▼</span>
                </div>
            </div>
            <h4>${item.title}</h4>
            <div class="card-detail" id="critical-${idx}">
                ${item.description ? `<p class="description">${item.description}</p>` : ''}
                ${item.value ? `<div class="meta-item"><strong>交易金额:</strong> ${item.value}</div>` : ''}
                ${item.indication ? `<div class="meta-item"><strong>适应症:</strong> ${item.indication}</div>` : ''}
                ${item.stage ? `<div class="meta-item"><strong>阶段:</strong> ${item.stage}</div>` : ''}
                ${item.company ? `<div class="meta-item"><strong>公司:</strong> ${item.company}</div>` : ''}
                ${item.link ? `<a href="${item.link}" target="_blank" class="read-more" onclick="event.stopPropagation()">阅读原文 →</a>` : ''}
                ${item.source ? `<div class="meta">来源: ${item.source}</div>` : ''}
            </div>
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
            <div class="brief-item" onclick="toggleDetail('deal-${i}')">
                <div class="brief-item-header">
                    <span class="item-title">${d.title}</span>
                    <span class="expand-icon">▼</span>
                </div>
                <div class="brief-item-meta">
                    ${d.company ? `<span>${d.company}</span>` : ''}
                    ${d.value ? `<span class="value">${d.value}</span>` : ''}
                    ${d.date ? `<span class="date">${formatDate(d.date)}</span>` : ''}
                </div>
                <div class="card-detail" id="deal-${i}">
                    ${d.description ? `<p>${d.description}</p>` : ''}
                    ${d.link ? `<a href="${d.link}" target="_blank" class="read-more" onclick="event.stopPropagation()">阅读原文 →</a>` : ''}
                </div>
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
            <div class="brief-item" onclick="toggleDetail('clinical-${i}')">
                <div class="brief-item-header">
                    <span class="item-title">${c.title}</span>
                    <span class="expand-icon">▼</span>
                </div>
                <div class="brief-item-meta">
                    ${c.company ? `<span>${c.company}</span>` : ''}
                    ${c.indication ? `<span>${c.indication}</span>` : ''}
                    ${c.stage ? `<span class="stage">${c.stage}</span>` : ''}
                </div>
                <div class="card-detail" id="clinical-${i}">
                    ${c.description ? `<p>${c.description}</p>` : ''}
                    ${c.link ? `<a href="${c.link}" target="_blank" class="read-more" onclick="event.stopPropagation()">阅读原文 →</a>` : ''}
                </div>
            </div>
        `).join('');
    }

    // Research - Papers from PubMed
    const researchList = document.getElementById('researchList');
    const papers = [];
    for (const [cat, catPapers] of Object.entries(data.papers || {})) {
        papers.push(...(catPapers || []).slice(0, 3));
    }
    if (papers.length === 0) {
        researchList.innerHTML = '<div class="empty-card">暂无新文献</div>';
    } else {
        researchList.innerHTML = papers.slice(0, 8).map((p, i) => `
            <div class="brief-item paper-item" onclick="toggleDetail('paper-${i}')">
                <div class="brief-item-header">
                    <span class="item-title">${p.title}</span>
                    <span class="expand-icon">▼</span>
                </div>
                <div class="brief-item-meta">
                    <span class="journal">${p.journal}</span>
                    ${p.date ? `<span class="date">${p.date}</span>` : ''}
                </div>
                <div class="card-detail" id="paper-${i}">
                    ${p.abstract ? `<p class="abstract">${p.abstract}</p>` : ''}
                    ${p.authors?.length ? `<div class="authors">作者: ${p.authors.slice(0, 5).join(', ')}${p.authors.length > 5 ? ' et al.' : ''}</div>` : ''}
                    ${p.keywords?.length ? `<div class="keywords">关键词: ${p.keywords.slice(0, 6).join(', ')}</div>` : ''}
                </div>
            </div>
        `).join('');
    }
}

// ===== Render Papers by Section =====
function renderPapersBySection(data) {
    const papers = data.papers || {};

    renderPaperSection('geneEditingPapers', papers.gene_editing || []);
    renderPaperSection('cellTherapyPapers', papers.cell_therapy || []);
    renderPaperSection('ADCPapers', papers.adc || []);
    renderPaperSection('GLP1Papers', papers.glp1 || []);
    renderPaperSection('IOPapers', papers.io || []);
}

function renderPaperSection(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无相关文献</div>';
        return;
    }

    container.innerHTML = items.map(paper => `
        <div class="paper-card" data-category="${paper.category || ''}">
            <div class="paper-journal">${paper.journal}</div>
            <h4>${paper.title}</h4>
            <div class="authors">${paper.authors?.slice(0, 3).join(', ')}${paper.authors?.length > 3 ? ' et al.' : ''}</div>
            <p class="abstract">${paper.abstract}</p>
            <div class="tags">
                ${(paper.keywords || []).slice(0, 4).map(k => `<span class="tag">${k}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

function renderPapers() {
    // Filter logic can be enhanced here
    // For now, just re-render
}

// ===== Render Companies =====
function renderCompaniesByType(data) {
    const container = document.getElementById('companyGrid');
    const companies = data.companies || {
        international: [],
        china: []
    };

    const items = companies[currentCompanyType] || [];

    if (items.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无公司数据</div>';
        return;
    }

    container.innerHTML = items.map(company => `
        <div class="company-card">
            <div class="ticker">${company.ticker || company.code}</div>
            <h4>${company.name}</h4>
            <div class="company-type">${company.type || company.focus}</div>
            <div class="status">
                ${company.pipeline ? '<span class="status-item pipeline">Pipeline</span>' : ''}
                ${company.news ? '<span class="status-item news">News</span>' : ''}
                ${company.paper ? '<span class="status-item paper">Paper</span>' : ''}
            </div>
        </div>
    `).join('');
}

// ===== Render Earnings =====
function renderEarnings(data) {
    const container = document.getElementById('earningsList');
    const earnings = data.earnings || [];

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
                <span class="date ${isSoon ? 'soon' : ''}">${e.date} ${e.exchange}</span>
            </li>
        `;
    }).join('');
}

// ===== Helper Functions =====
function toggleDetail(id) {
    const detail = document.getElementById(id);
    if (detail) {
        detail.classList.toggle('expanded');
    }
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
    } catch {
        return dateStr;
    }
}

// ===== Sample Data for Demo =====
function loadSampleData() {
    const sampleData = {
        timestamp: new Date().toISOString(),
        critical: {
            deals: [
                {
                    title: 'BMS达成25亿美元基因编辑合作',
                    description: '与Prime Medicine合作开发体内基因编辑疗法',
                    company: 'Bristol Myers Squibb',
                    value: '$250M upfront',
                    date: '2024-01-15',
                    priority: 'critical'
                }
            ],
            clinical: [],
            approvals: []
        },
        daily: {
            deals: [
                { title: 'Roche扩展基因治疗管线', company: 'Roche', value: '未披露', date: '2024-01-15' },
                { title: 'Vertex收购血友病基因疗法公司', company: 'Vertex', value: '$500M', date: '2024-01-14' }
            ],
            clinical: [
                { title: 'BEAM-101 β-thalassemia研究更新', company: 'Beam', indication: 'β-地中海贫血', stage: 'Phase 1/2' }
            ],
            research: [
                { title: 'Prime editing实现90%效率突破', journal: 'Nature Biotechnology', date: '2024-01-15' }
            ]
        },
        papers: {
            gene_editing: [
                {
                    title: 'Prime editing for the treatment of hemoglobinopathies',
                    journal: 'Nature Biotechnology',
                    authors: ['Anzalone AV', 'Gao X'],
                    abstract: 'Demonstration of high-efficiency prime editing in human hematopoietic stem cells for the treatment of sickle cell disease and β-thalassemia.',
                    keywords: ['Prime Editing', 'Hemoglobinopathy', 'HSC'],
                    category: 'prime'
                }
            ],
            cell_therapy: [],
            adc: [],
            glp1: [],
            io: []
        },
        companies: {
            international: [
                { ticker: 'BEAM', name: 'Beam Therapeutics', type: 'Base/Prime Editing', pipeline: true, news: true, paper: true },
                { ticker: 'VERV', name: 'Verve Therapeutics', type: 'In Vivo Gene Editing', pipeline: true, news: false, paper: false },
                { ticker: 'NTLA', name: 'Intellia Therapeutics', type: 'In Vivo CRISPR', pipeline: true, news: true, paper: true },
                { ticker: 'EDIT', name: 'Editas Medicine', type: 'In Vivo CRISPR', pipeline: true, news: false, paper: false },
                { ticker: 'PRME', name: 'Prime Medicine', type: 'Prime Editing', pipeline: true, news: true, paper: true }
            ],
            china: [
                { code: '688265', name: '博雅基因', type: 'CRISPR/Cas9', pipeline: true, news: false, paper: false },
                { code: '688321', name: '邦耀生物', type: '基因编辑', pipeline: true, news: true, paper: false }
            ]
        },
        earnings: [
            { company: 'Beam Therapeutics', ticker: 'BEAM', date: '2024-02-15', exchange: 'NASDAQ' },
            { company: 'Intellia', ticker: 'NTLA', date: '2024-02-22', exchange: 'NASDAQ' },
            { company: 'Illumina', ticker: 'ILMN', date: '2024-02-13', exchange: 'NASDAQ' }
        ]
    };

    updateLastUpdate(sampleData.timestamp);
    renderCritical(sampleData);
    renderDailyBrief(sampleData);
    renderPapersBySection(sampleData);
    renderCompaniesByType(sampleData);
    renderEarnings(sampleData);
}