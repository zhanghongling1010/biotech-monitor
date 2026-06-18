// ===== Configuration =====
const CONFIG = {
    dataUrl: 'data/daily/latest.json',
    updateInterval: 300000
};

let currentSection = 'today';
let currentFilter = 'all';
let currentCompanyType = 'international';
let allData = null;

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

    container.innerHTML = companies.map(company => `
        <div class="company-card">
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

    // Chinese content - detailed
    let cnContent = '';
    if (item.description_cn) {
        cnContent += `<p>${item.description_cn}</p>`;
    } else if (item.summary_cn) {
        cnContent += `<p>${item.summary_cn}</p>`;
    }
    if (item.abstract_cn) {
        cnContent += `<h4 style="margin-top:1rem;font-size:0.9rem;color:#166534;">中文摘要</h4><p>${item.abstract_cn}</p>`;
    }
    if (!cnContent) cnContent = '<p style="color:#64748b;">暂无中文详情</p>';
    document.getElementById('modalCnContent').innerHTML = cnContent;

    // English content
    let enContent = '';
    if (item.title) enContent += `<p><strong>英文标题:</strong> ${item.title}</p>`;
    if (item.description) enContent += `<p><strong>英文正文:</strong> ${item.description}</p>`;
    if (item.abstract) enContent += `<p><strong>英文摘要:</strong> ${item.abstract}</p>`;
    if (!enContent) enContent = '<p style="color:#64748b;">无英文原文</p>';
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
    openModal('paper', -1);
    // Override with specific paper data
    document.getElementById('modalTag').textContent = '科研文献';
    document.getElementById('modalTag').className = 'modal-tag clinical';
    document.getElementById('modalTitle').textContent = paper.title_cn || paper.title || '无标题';

    let metaHtml = '';
    if (paper.journal) metaHtml += `<span class="modal-meta-item"><strong>期刊:</strong> ${paper.journal}</span>`;
    if (paper.date) metaHtml += `<span class="modal-meta-item"><strong>发表日期:</strong> ${paper.date}</span>`;
    if (paper.pmid) metaHtml += `<span class="modal-meta-item"><strong>PMID:</strong> ${paper.pmid}</span>`;
    if (paper.companies?.length) metaHtml += `<span class="modal-meta-item"><strong>相关公司:</strong> ${paper.companies.join(', ')}</span>`;
    document.getElementById('modalMeta').innerHTML = metaHtml;

    let cnContent = '';
    if (paper.summary_cn) cnContent += `<p>${paper.summary_cn}</p>`;
    if (paper.abstract_cn) cnContent += `<h4 style="margin-top:1rem;font-size:0.9rem;color:#166534;">中文摘要</h4><p>${paper.abstract_cn}</p>`;
    if (!cnContent) cnContent = '<p style="color:#64748b;">暂无中文翻译</p>';
    document.getElementById('modalCnContent').innerHTML = cnContent;

    let enContent = '';
    if (paper.title) enContent += `<p><strong>英文标题:</strong> ${paper.title}</p>`;
    if (paper.abstract) enContent += `<p><strong>英文摘要:</strong> ${paper.abstract}</p>`;
    if (paper.authors?.length) enContent += `<p><strong>作者:</strong> ${paper.authors.slice(0, 5).join(', ')}${paper.authors.length > 5 ? ' et al.' : ''}</p>`;
    if (paper.keywords?.length) enContent += `<p><strong>关键词:</strong> ${paper.keywords.join(', ')}</p>`;
    if (!enContent) enContent = '<p style="color:#64748b;">无英文原文</p>';
    document.getElementById('modalEnContent').innerHTML = enContent;

    const linkEl = document.getElementById('modalLink');
    if (paper.pmid) {
        linkEl.href = `https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`;
        linkEl.textContent = '在 PubMed 查看全文 →';
        linkEl.style.display = 'inline-block';
    } else {
        linkEl.style.display = 'none';
    }

    document.getElementById('detailModal').classList.add('active');
    document.body.style.overflow = 'hidden';
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
