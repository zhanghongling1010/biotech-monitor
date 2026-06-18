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

    container.innerHTML = items.map(item => `
        <div class="alert-card ${item.priority === 'critical' ? 'critical' : 'warning'}">
            <div class="card-header">
                <span class="tag ${item.type}">${item.tag}</span>
                <span class="date">${item.date || ''}</span>
            </div>
            <h4>${item.title}</h4>
            <p>${item.description || ''}</p>
            ${item.source ? `<div class="meta">来源: ${item.source}</div>` : ''}
        </div>
    `).join('');
}

// ===== Render Daily Brief =====
function renderDailyBrief(data) {
    // Deals
    const dealsList = document.getElementById('dealsList');
    dealsList.innerHTML = (data.daily?.deals || []).map(d => `
        <li>
            <span class="item-title">${d.title}</span>
            <span class="item-meta">${d.company} | ${d.value || ''} | ${d.date || ''}</span>
        </li>
    `).join('') || '<li>暂无新交易</li>';

    // Clinical
    const clinicalList = document.getElementById('clinicalList');
    clinicalList.innerHTML = (data.daily?.clinical || []).map(c => `
        <li>
            <span class="item-title">${c.title}</span>
            <span class="item-meta">${c.company} | ${c.indication} | ${c.stage}</span>
        </li>
    `).join('') || '<li>暂无临床进展</li>';

    // Research
    const researchList = document.getElementById('researchList');
    researchList.innerHTML = (data.daily?.research || []).slice(0, 5).map(r => `
        <li>
            <span class="item-title">${r.title}</span>
            <span class="item-meta">${r.journal} | ${r.date || ''}</span>
        </li>
    `).join('') || '<li>暂无新文献</li>';
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