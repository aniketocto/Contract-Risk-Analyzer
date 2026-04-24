/* ================================================================
   Contract Risk Analyzer — Frontend Logic
   ================================================================ */

// ── DOM References ──────────────────────────────────────────────
const dropZone        = document.getElementById('drop-zone');
const fileInput       = document.getElementById('file-input');
const browseBtn       = document.getElementById('browse-btn');
const filePreview     = document.getElementById('file-preview');
const fileNameEl      = document.getElementById('file-name');
const fileSizeEl      = document.getElementById('file-size');
const removeFileBtn   = document.getElementById('remove-file');
const analyzeBtn      = document.getElementById('analyze-btn');
const resultsContainer= document.getElementById('results-container');
const pipelineStatus  = document.getElementById('pipeline-status');
const errorToast      = document.getElementById('error-toast');
const errorMessage    = document.getElementById('error-message');
const userRoleSelect  = document.getElementById('user-role');

// Filter controls
const filterCategory = document.getElementById('filter-category');
const filterRisk     = document.getElementById('filter-risk');

let selectedFile = null;
let analysisData = null;

// ── Category color map ──────────────────────────────────────────
const CATEGORY_COLORS = {
    'Liability':              { css: 'tag-liability',            bar: '#f43f5e' },
    'Termination':            { css: 'tag-termination',          bar: '#f97316' },
    'Intellectual Property':  { css: 'tag-intellectual-property', bar: '#8b5cf6' },
    'Payment':                { css: 'tag-payment',              bar: '#f59e0b' },
    'Confidentiality':        { css: 'tag-confidentiality',      bar: '#06b6d4' },
    'Indemnification':        { css: 'tag-indemnification',      bar: '#ec4899' },
    'Governing Law':          { css: 'tag-governing-law',        bar: '#3b82f6' },
    'Other':                  { css: 'tag-other',                bar: '#64748b' },
};

const RISK_COLORS = {
    'High':   { css: 'risk-high',   bar: '#f43f5e', bg: 'rgba(244, 63, 94, 0.12)' },
    'Medium': { css: 'risk-medium', bar: '#f59e0b', bg: 'rgba(245, 158, 11, 0.12)' },
    'Low':    { css: 'risk-low',    bar: '#10b981', bg: 'rgba(16, 185, 129, 0.12)' },
};


// ── File Upload Handling ────────────────────────────────────────
browseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
});

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) setFile(e.target.files[0]);
});

// Drag & drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) setFile(e.dataTransfer.files[0]);
});

removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    clearFile();
});


function setFile(file) {
    selectedFile = file;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = formatFileSize(file.size);
    filePreview.classList.remove('hidden');
    dropZone.querySelector('.drop-zone-content').classList.add('hidden');
    analyzeBtn.disabled = false;
}

function clearFile() {
    selectedFile = null;
    fileInput.value = '';
    filePreview.classList.add('hidden');
    dropZone.querySelector('.drop-zone-content').classList.remove('hidden');
    analyzeBtn.disabled = true;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}


// ── Analyze Button ──────────────────────────────────────────────
analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    // UI: loading state
    const btnText   = analyzeBtn.querySelector('.btn-text');
    const btnLoader = analyzeBtn.querySelector('.btn-loader');
    btnText.classList.add('hidden');
    btnLoader.classList.remove('hidden');
    analyzeBtn.disabled = true;
    setStatus('processing', 'Analyzing...');
    resultsContainer.classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('user_role', userRoleSelect.value);

        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (data.status !== 'success') {
            throw new Error(data.error || 'Analysis failed');
        }

        analysisData = data;
        renderResults(data);
        setStatus('ready', 'Complete');

    } catch (err) {
        showError(err.message);
        setStatus('error', 'Error');
    } finally {
        btnText.classList.remove('hidden');
        btnLoader.classList.add('hidden');
        analyzeBtn.disabled = false;
    }
});


// ── Render Results ──────────────────────────────────────────────
function renderResults(data) {
    // Stats
    document.getElementById('stat-clauses').textContent   = data.total_clauses;
    document.getElementById('stat-sections').textContent  = data.total_sections;

    // Risk stats
    const rb = data.risk_breakdown || {};
    document.getElementById('stat-high-risk').textContent = rb.High || 0;
    document.getElementById('stat-med-risk').textContent  = rb.Medium || 0;

    // Category breakdown bars
    renderCategoryBars(data.category_breakdown, data.total_clauses);

    // Risk breakdown bars
    renderRiskBars(data.risk_breakdown, data.total_clauses);

    // Populate category filter
    populateCategoryFilter(data.category_breakdown);

    // Clauses list
    renderClauses(data.clauses);

    // Section tree
    renderSectionTree(data.sections);

    // Show results
    resultsContainer.classList.remove('hidden');

    // Smooth scroll to results
    setTimeout(() => {
        document.getElementById('stats-row').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}


// ── Category Bars ───────────────────────────────────────────────
function renderCategoryBars(breakdown, total) {
    const container = document.getElementById('category-bars');
    container.innerHTML = '';

    const sorted = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);
    const maxVal = sorted.length > 0 ? sorted[0][1] : 1;

    sorted.forEach(([cat, count], idx) => {
        const pct = (count / maxVal) * 100;
        const color = (CATEGORY_COLORS[cat] || CATEGORY_COLORS['Other']).bar;

        const row = document.createElement('div');
        row.className = 'cat-row';
        row.innerHTML = `
            <span class="cat-label">${cat}</span>
            <div class="cat-bar-track">
                <div class="cat-bar-fill" style="width: 0%; background: ${color};"></div>
            </div>
            <span class="cat-count">${count}</span>
        `;
        container.appendChild(row);

        requestAnimationFrame(() => {
            setTimeout(() => {
                row.querySelector('.cat-bar-fill').style.width = pct + '%';
            }, 80 + idx * 60);
        });
    });
}


// ── Risk Breakdown Bars ─────────────────────────────────────────
function renderRiskBars(breakdown, total) {
    const container = document.getElementById('risk-bars');
    container.innerHTML = '';

    const order = ['High', 'Medium', 'Low'];
    const maxVal = Math.max(...order.map(k => breakdown[k] || 0), 1);

    order.forEach((level, idx) => {
        const count = breakdown[level] || 0;
        const pct = (count / maxVal) * 100;
        const color = RISK_COLORS[level].bar;

        const row = document.createElement('div');
        row.className = 'cat-row';
        row.innerHTML = `
            <span class="cat-label">${level} Risk</span>
            <div class="cat-bar-track">
                <div class="cat-bar-fill" style="width: 0%; background: ${color};"></div>
            </div>
            <span class="cat-count">${count}</span>
        `;
        container.appendChild(row);

        requestAnimationFrame(() => {
            setTimeout(() => {
                row.querySelector('.cat-bar-fill').style.width = pct + '%';
            }, 80 + idx * 100);
        });
    });
}


// ── Category Filter Dropdown ────────────────────────────────────
function populateCategoryFilter(breakdown) {
    filterCategory.innerHTML = '<option value="all">All Categories</option>';
    Object.keys(breakdown).sort().forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat;
        opt.textContent = cat;
        filterCategory.appendChild(opt);
    });
}


// ── Clauses List ────────────────────────────────────────────────
function renderClauses(clauses) {
    const container = document.getElementById('clauses-list');
    container.innerHTML = '';

    const catFilter  = filterCategory.value;
    const riskFilter = filterRisk.value;

    const filtered = clauses.filter(c => {
        if (catFilter !== 'all' && c.type !== catFilter) return false;
        if (riskFilter !== 'all' && c.risk !== riskFilter) return false;
        return true;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                No clauses match the selected filters.
            </div>`;
        return;
    }

    filtered.forEach((clause, idx) => {
        const tagClass = getCategoryTagClass(clause.type);
        const riskInfo = RISK_COLORS[clause.risk] || RISK_COLORS['Low'];
        const riskClass = riskInfo.css;

        const card = document.createElement('div');
        card.className = 'clause-card';
        card.style.animationDelay = `${idx * 0.04}s`;

        // Border accent based on risk
        if (clause.risk === 'High') {
            card.style.borderLeft = '3px solid #f43f5e';
        } else if (clause.risk === 'Medium') {
            card.style.borderLeft = '3px solid #f59e0b';
        }

        const displayText = escapeHtml(clause.text).replace(/\n/g, '<br>');
        const reason = clause.reason ? escapeHtml(clause.reason) : '';

        card.innerHTML = `
            <div class="clause-id">${clause.id}</div>
            <div class="clause-body">
                <div class="clause-text" onclick="this.classList.toggle('expanded')">${displayText}</div>
                ${reason ? `<div class="clause-reason"><span class="reason-label">Risk:</span> ${reason}</div>` : ''}
            </div>
            <div class="clause-meta">
                <span class="category-tag ${tagClass}">${clause.type}</span>
                <span class="risk-tag ${riskClass}">${clause.risk}</span>
            </div>
        `;
        container.appendChild(card);
    });
}

// Re-render clauses on filter change
filterCategory.addEventListener('change', () => {
    if (analysisData) renderClauses(analysisData.clauses);
});

filterRisk.addEventListener('change', () => {
    if (analysisData) renderClauses(analysisData.clauses);
});


// ── Section Tree ────────────────────────────────────────────────
function renderSectionTree(sections) {
    const container = document.getElementById('section-tree');
    container.innerHTML = '';

    sections.forEach((sec, idx) => {
        container.appendChild(createTreeNode(sec, idx));
    });
}

function createTreeNode(node, idx) {
    const el = document.createElement('div');
    el.className = 'tree-node';
    el.style.animationDelay = `${idx * 0.05}s`;

    const hasChildren = node.children && node.children.length > 0;

    const section = document.createElement('div');
    section.className = 'tree-section';

    const header = document.createElement('div');
    header.className = 'tree-header';
    header.innerHTML = `
        ${hasChildren ? '<span class="tree-toggle open">&#9654;</span>' : '<span style="width: 12px;"></span>'}
        <span class="tree-id">${node.id}</span>
        <span class="tree-title">${escapeHtml(node.title || node.text?.substring(0, 80) || '')}</span>
    `;
    section.appendChild(header);

    if (hasChildren) {
        const childrenContainer = document.createElement('div');
        childrenContainer.className = 'tree-children';

        node.children.forEach((child, cidx) => {
            if (child.children && child.children.length > 0) {
                childrenContainer.appendChild(createTreeNode(child, cidx));
            } else {
                const clauseEl = document.createElement('div');
                clauseEl.className = 'tree-clause';
                clauseEl.innerHTML = `
                    <span class="tree-id">${child.id}</span>
                    <span>${escapeHtml((child.text || '').substring(0, 150))}${child.text?.length > 150 ? '...' : ''}</span>
                `;
                childrenContainer.appendChild(clauseEl);
            }
        });

        section.appendChild(childrenContainer);

        header.addEventListener('click', () => {
            const toggle = header.querySelector('.tree-toggle');
            const children = section.querySelector('.tree-children');
            toggle.classList.toggle('open');
            children.classList.toggle('collapsed');
        });
    }

    el.appendChild(section);
    return el;
}


// ── Helpers ──────────────────────────────────────────────────────
function getCategoryTagClass(category) {
    const entry = CATEGORY_COLORS[category];
    return entry ? entry.css : 'tag-other';
}

function setStatus(type, text) {
    pipelineStatus.className = 'status-badge ' + type;
    pipelineStatus.querySelector('span:last-child').textContent = text;
}

function showError(msg) {
    errorMessage.textContent = msg;
    errorToast.classList.remove('hidden');
    errorToast.classList.add('visible');
    setTimeout(() => {
        errorToast.classList.remove('visible');
        setTimeout(() => errorToast.classList.add('hidden'), 300);
    }, 5000);
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
