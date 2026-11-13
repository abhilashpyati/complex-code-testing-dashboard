/**
 * Complex Code Testing Dashboard — JavaScript
 * Handles: CodeMirror editor, sample loading, API calls, result rendering, charts
 */

'use strict';

/* ═══════════════════════════════════════════════
   STATE
══════════════════════════════════════════════ */
let editor = null;
let currentAnalysisId = null;
let currentResult = null;
let charts = {};
let currentFindingTab = 'flake8';
let currentFilter = 'all';
let loadingInterval = null;

/* ═══════════════════════════════════════════════
   INIT
══════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initEditor();
  loadSamples();
  setupFileUpload();
});

function initEditor() {
  editor = CodeMirror.fromTextArea(document.getElementById('codeInput'), {
    mode: 'python',
    theme: 'dracula',
    lineNumbers: true,
    indentUnit: 4,
    tabSize: 4,
    indentWithTabs: false,
    autofocus: false,
    lineWrapping: false,
    matchBrackets: true,
    autoCloseBrackets: true,
    extraKeys: { 'Ctrl-Enter': analyzeCode, 'Cmd-Enter': analyzeCode },
  });

  editor.on('change', () => {
    const lines = editor.lineCount();
    document.getElementById('lineCount').textContent = `${lines} line${lines !== 1 ? 's' : ''}`;
    hideSyntaxAlert();
  });
}

/* ═══════════════════════════════════════════════
   SAMPLES
══════════════════════════════════════════════ */
async function loadSamples() {
  try {
    const res = await fetch('/api/samples');
    const data = await res.json();
    renderSamples(data.samples || {});
  } catch (e) {
    document.getElementById('sampleGrid').innerHTML =
      '<p class="text-muted small p-3">Could not load samples</p>';
  }
}

function renderSamples(samples) {
  const grid = document.getElementById('sampleGrid');
  const icons = {
    scientific_calculator: '🧮',
    bank_account: '🏦',
    defective_code: '🐛',
  };
  const descs = {
    scientific_calculator: 'Well-structured calculator with math ops',
    bank_account: 'OOP banking with transactions & validation',
    defective_code: 'Intentional bugs, security & style issues',
  };

  if (!Object.keys(samples).length) {
    grid.innerHTML = '<p class="text-muted small p-3">No samples found</p>';
    return;
  }

  grid.innerHTML = Object.entries(samples).map(([key, s]) => `
    <div class="sample-card" onclick="loadSample('${key}')" id="sample-${key}" title="Load ${s.name}">
      <span class="sample-icon">${icons[key] || '📄'}</span>
      <div>
        <div class="sample-title">${s.name}</div>
        <div class="sample-desc">${descs[key] || s.filename}</div>
      </div>
    </div>
  `).join('');
}

function loadSample(key) {
  fetch('/api/samples')
    .then(r => r.json())
    .then(data => {
      const sample = data.samples[key];
      if (sample) {
        editor.setValue(sample.code);
        document.getElementById('uploadedFilename').textContent = sample.filename;
        hideSyntaxAlert();
        scrollToSection('inputSection');
        highlightSample(key);
      }
    });
}

function highlightSample(key) {
  document.querySelectorAll('.sample-card').forEach(c => c.classList.remove('active'));
  const el = document.getElementById(`sample-${key}`);
  if (el) el.classList.add('active');
}

/* ═══════════════════════════════════════════════
   FILE UPLOAD
══════════════════════════════════════════════ */
function setupFileUpload() {
  const inp = document.getElementById('fileUpload');
  inp.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.name.endsWith('.py')) {
      showSyntaxAlert('Only .py files are accepted.');
      return;
    }
    const text = await file.text();
    editor.setValue(text);
    document.getElementById('uploadedFilename').textContent = file.name;
    hideSyntaxAlert();
  });
}

/* ═══════════════════════════════════════════════
   ANALYSIS
══════════════════════════════════════════════ */
async function analyzeCode() {
  const code = editor.getValue().trim();
  if (!code) {
    showSyntaxAlert('Please enter or upload Python source code.');
    return;
  }

  const filename = document.getElementById('uploadedFilename').textContent || 'user_code.py';

  setAnalyzeBtn(false);
  showLoadingOverlay();
  setNavStatus('Analysing…', 'analysing');

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, filename }),
    });

    const data = await response.json();

    if (!response.ok) {
      if (data.validation_errors) {
        const err = data.validation_errors[0];
        showSyntaxAlert(
          err.line > 0
            ? `Line ${err.line}: ${err.message}`
            : err.message
        );
      } else {
        showSyntaxAlert(data.error || 'Analysis failed');
      }
      return;
    }

    currentResult = data;
    currentAnalysisId = data.analysis_id;
    renderResults(data);

  } catch (err) {
    showSyntaxAlert('Network error: ' + err.message);
  } finally {
    hideLoadingOverlay();
    setAnalyzeBtn(true);
    setNavStatus('Done', 'done');
  }
}

/* ═══════════════════════════════════════════════
   RENDER RESULTS
══════════════════════════════════════════════ */
function renderResults(data) {
  document.getElementById('resultsSection').classList.remove('d-none');
  document.getElementById('resultFilename').textContent = data.filename || 'user_code.py';
  document.getElementById('resultTimestamp').textContent = new Date(data.timestamp).toLocaleString();

  renderHealthScore(data);
  renderMetrics(data);
  renderCharts(data);
  renderCriteria(data);
  renderFindings(data);
  renderComplexity(data);
  renderDefectPrediction(data);
  renderSecurityDetail(data);
  setupDownloadButtons(data);

  setTimeout(() => {
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 100);
}

/* Health Score Ring */
function renderHealthScore(data) {
  const score = data.health_score || 0;
  const el = document.getElementById('healthValue');
  const ring = document.getElementById('healthRing');
  const label = document.getElementById('healthLabel');

  el.textContent = score;
  const circumference = 314;
  const offset = circumference - (score / 100) * circumference;
  ring.style.strokeDashoffset = offset;

  let color, labelText;
  if (score >= 70) { color = '#22c55e'; labelText = 'Good Quality'; }
  else if (score >= 40) { color = '#f59e0b'; labelText = 'Needs Improvement'; }
  else { color = '#ef4444'; labelText = 'Poor Quality'; }

  ring.style.stroke = color;
  el.style.color = color;
  label.textContent = labelText;
  label.style.color = color;
}

/* Metric Cards */
function renderMetrics(data) {
  const s = data.summary || {};
  const cov = data.coverage_metrics || {};
  const cx = (data.complexity || {}).overall || {};
  const pred = data.defect_prediction || {};

  setText('metricPassed', s.PASSED ?? '—');
  setText('metricWarning', s.WARNING ?? '—');
  setText('metricFailed', s.FAILED ?? '—');
  setText('metricNotExec', s.NOT_EXECUTED ?? '—');
  setText('metricStmtCov', cov.statement_coverage != null ? cov.statement_coverage.toFixed(1) + '%' : '—');
  setText('metricBranchCov', cov.branch_coverage != null ? cov.branch_coverage.toFixed(1) + '%' : '—');
  setText('metricComplexity', cx.average != null ? cx.average.toFixed(1) : '—');
  setText('metricRisk', pred.category || '—');
}

/* ─── CHARTS ─── */
function renderCharts(data) {
  destroyCharts();

  const s = data.summary || {};
  const cov = data.coverage_metrics || {};
  const cx = (data.complexity || {}).overall || {};
  const findings = data.findings || {};

  // 1. Radar Chart
  const radar = document.getElementById('radarChart').getContext('2d');
  const stmtCov = cov.statement_coverage || 0;
  const branchCov = cov.branch_coverage || 0;
  const totalCrit = (data.all_criteria || []).length || 25;
  const passRate = totalCrit > 0 ? ((s.PASSED || 0) / totalCrit) * 100 : 0;
  const noSecurity = Math.max(0, 100 - ((data.findings?.bandit?.length || 0) * 15));
  const noStatic = Math.max(0, 100 - (((findings.flake8?.length || 0) + (findings.pylint?.length || 0)) * 5));
  const complexScore = Math.max(0, 100 - Math.min(100, (cx.average || 1) * 8));

  charts.radar = new Chart(radar, {
    type: 'radar',
    data: {
      labels: ['Test Pass Rate', 'Statement Coverage', 'Branch Coverage', 'Security', 'Static Quality', 'Complexity'],
      datasets: [{
        label: 'Code Quality',
        data: [passRate, stmtCov, branchCov, noSecurity, noStatic, complexScore],
        backgroundColor: 'rgba(59,130,246,.15)',
        borderColor: '#3b82f6',
        pointBackgroundColor: '#3b82f6',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: '#3b82f6',
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } } },
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { color: '#475569', backdropColor: 'transparent', stepSize: 20 },
          grid: { color: 'rgba(255,255,255,.07)' },
          pointLabels: { color: '#94a3b8', font: { size: 11, family: 'Inter' } },
        },
      },
    },
  });

  // 2. Doughnut
  const doughnut = document.getElementById('doughnutChart').getContext('2d');
  charts.doughnut = new Chart(doughnut, {
    type: 'doughnut',
    data: {
      labels: ['Passed', 'Warning', 'Failed', 'Not Executed'],
      datasets: [{
        data: [s.PASSED || 0, s.WARNING || 0, s.FAILED || 0, s.NOT_EXECUTED || 0],
        backgroundColor: ['#22c55e', '#f59e0b', '#ef4444', '#475569'],
        borderColor: '#16213e',
        borderWidth: 3,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', padding: 12, font: { family: 'Inter', size: 11 } },
        },
      },
    },
  });

  // 3. Coverage Bar
  const covCtx = document.getElementById('coverageChart').getContext('2d');
  charts.coverage = new Chart(covCtx, {
    type: 'bar',
    data: {
      labels: ['Statement Coverage', 'Branch Coverage'],
      datasets: [{
        label: '%',
        data: [stmtCov, branchCov],
        backgroundColor: ['rgba(6,182,212,.7)', 'rgba(139,92,246,.7)'],
        borderColor: ['#06b6d4', '#8b5cf6'],
        borderWidth: 1,
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      indexAxis: 'y',
      scales: {
        x: { max: 100, ticks: { color: '#475569', callback: v => v + '%' }, grid: { color: 'rgba(255,255,255,.05)' } },
        y: { ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }, grid: { display: false } },
      },
      plugins: { legend: { display: false } },
    },
  });

  // 4. Complexity Distribution
  const dist = cx.distribution || {};
  const cxDistCtx = document.getElementById('complexityDistChart').getContext('2d');
  charts.complexityDist = new Chart(cxDistCtx, {
    type: 'bar',
    data: {
      labels: ['LOW (1-5)', 'MODERATE (6-12)', 'HIGH (13-25)', 'CRITICAL (>25)'],
      datasets: [{
        label: 'Functions',
        data: [dist.LOW || 0, dist.MODERATE || 0, dist.HIGH || 0, dist.CRITICAL || 0],
        backgroundColor: ['rgba(34,197,94,.7)', 'rgba(245,158,11,.7)', 'rgba(249,115,22,.7)', 'rgba(239,68,68,.7)'],
        borderRadius: 5,
      }],
    },
    options: {
      responsive: true,
      scales: {
        x: { ticks: { color: '#475569', font: { size: 10, family: 'Inter' } }, grid: { display: false } },
        y: { ticks: { color: '#475569', precision: 0 }, grid: { color: 'rgba(255,255,255,.05)' } },
      },
      plugins: { legend: { display: false } },
    },
  });
}

function destroyCharts() {
  Object.values(charts).forEach(c => c.destroy());
  charts = {};
}

/* ─── 25 CRITERIA ─── */
const TOOL_CONFIG = [
  { key: 'pytest',   label: 'PyTest',           icon: 'bi-play-circle',          prefix: 'PT' },
  { key: 'coverage', label: 'Coverage.py',       icon: 'bi-graph-up',             prefix: 'CV' },
  { key: 'flake8',   label: 'Flake8',            icon: 'bi-search',               prefix: 'FL' },
  { key: 'pylint',   label: 'Pylint',            icon: 'bi-clipboard2-check',     prefix: 'PL' },
  { key: 'bandit',   label: 'Bandit',            icon: 'bi-shield-lock',          prefix: 'BD' },
];

function renderCriteria(data) {
  const container = document.getElementById('toolPanels');
  container.innerHTML = '';

  const criteriaMap = data.criteria || {};

  TOOL_CONFIG.forEach((tool, idx) => {
    const list = criteriaMap[tool.key] || [];
    const summary = countStatuses(list);
    const panelEl = makeCriteriaPanel(tool, list, summary, idx === 0);
    container.appendChild(panelEl);
  });
}

function countStatuses(list) {
  const s = { PASSED: 0, WARNING: 0, FAILED: 0, NOT_EXECUTED: 0 };
  list.forEach(c => { s[c.status] = (s[c.status] || 0) + 1; });
  return s;
}

function makeCriteriaPanel(tool, criteria, summary, open) {
  const panel = document.createElement('div');
  panel.className = 'tool-panel';
  panel.dataset.tool = tool.key;

  const statBadges = `
    ${summary.PASSED ? `<span class="status-badge status-PASSED">${summary.PASSED} ✓</span>` : ''}
    ${summary.WARNING ? `<span class="status-badge status-WARNING">${summary.WARNING} ⚠</span>` : ''}
    ${summary.FAILED ? `<span class="status-badge status-FAILED">${summary.FAILED} ✗</span>` : ''}
    ${summary.NOT_EXECUTED ? `<span class="status-badge status-NOT_EXECUTED">${summary.NOT_EXECUTED} —</span>` : ''}
  `;

  panel.innerHTML = `
    <div class="tool-panel-header" onclick="togglePanel(this)">
      <div class="d-flex align-items-center gap-2">
        <i class="bi ${tool.icon} text-primary"></i>
        <span class="tool-name">${tool.label}</span>
        <span class="text-muted small">(${criteria.length} criteria)</span>
      </div>
      <div class="d-flex align-items-center gap-2">
        <div class="tool-stats">${statBadges}</div>
        <i class="bi bi-chevron-${open ? 'up' : 'down'} text-muted small"></i>
      </div>
    </div>
    <div class="tool-panel-body ${open ? 'open' : ''}">
      <table class="criteria-table">
        <thead>
          <tr>
            <th style="width:70px">ID</th>
            <th>Criterion</th>
            <th style="width:100px">Status</th>
            <th>Details</th>
            <th style="width:200px">Recommendation</th>
          </tr>
        </thead>
        <tbody>
          ${criteria.map(c => makeCriterionRow(c)).join('')}
        </tbody>
      </table>
    </div>
  `;
  return panel;
}

function makeCriterionRow(c) {
  return `
    <tr data-status="${c.status}" class="criterion-row">
      <td><span class="criterion-id">${c.id}</span></td>
      <td><span class="criterion-name">${escHtml(c.name)}</span></td>
      <td><span class="status-badge status-${c.status}">${c.status.replace('_', ' ')}</span></td>
      <td class="text-secondary" style="font-size:.82rem">${escHtml(c.details || '')}</td>
      <td class="text-muted" style="font-size:.78rem">${escHtml(c.recommendation || '')}</td>
    </tr>
  `;
}

function togglePanel(header) {
  const body = header.nextElementSibling;
  const icon = header.querySelector('.bi-chevron-up, .bi-chevron-down');
  body.classList.toggle('open');
  if (icon) {
    icon.classList.toggle('bi-chevron-up');
    icon.classList.toggle('bi-chevron-down');
  }
}

function filterCriteria(status, btn) {
  currentFilter = status;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.criterion-row').forEach(row => {
    if (status === 'all' || row.dataset.status === status) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
  // Open panels that have matching criteria
  document.querySelectorAll('.tool-panel').forEach(panel => {
    const hasVisible = Array.from(panel.querySelectorAll('.criterion-row')).some(
      r => r.style.display !== 'none'
    );
    const body = panel.querySelector('.tool-panel-body');
    if (hasVisible && status !== 'all') {
      body.classList.add('open');
    }
  });
}

/* ─── FINDINGS ─── */
function renderFindings(data) {
  const findings = data.findings || {};
  const totalCount = Object.values(findings).reduce((sum, arr) => sum + (arr?.length || 0), 0);
  document.getElementById('findingsCount').textContent = totalCount;
  renderFindingTab(currentFindingTab, findings);
}

function switchFindingTab(tab, btn) {
  currentFindingTab = tab;
  document.querySelectorAll('.finding-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (currentResult) renderFindingTab(tab, currentResult.findings || {});
}

function renderFindingTab(tab, findings) {
  const content = document.getElementById('findingsContent');
  const list = findings[tab] || [];

  if (!list.length) {
    content.innerHTML = `<div class="empty-state"><i class="bi bi-check-circle"></i>No ${tab} findings</div>`;
    return;
  }

  content.innerHTML = list.slice(0, 50).map(f => {
    const sev = f.severity || '';
    const sevHtml = sev ? `<span class="finding-sev sev-${sev}">${sev}</span>` : '';
    return `
      <div class="finding-row">
        <span class="finding-line">L${f.line || '?'}</span>
        <span class="finding-code">${escHtml(f.code || '')}</span>
        <span class="finding-msg">${escHtml(f.message || '')}</span>
        ${sevHtml}
      </div>
    `;
  }).join('');
}

/* ─── COMPLEXITY ─── */
function renderComplexity(data) {
  const cx = data.complexity || {};
  const overall = cx.overall || {};
  const fns = (cx.functions || []).slice(0, 10);
  const content = document.getElementById('complexityContent');

  if (!fns.length) {
    content.innerHTML = `
      <div class="empty-state"><i class="bi bi-diagram-3"></i>No complexity data available</div>
    `;
    return;
  }

  const maxCx = Math.max(...fns.map(f => f.complexity), 1);

  const overallHtml = `
    <div class="d-flex gap-4 mb-3 flex-wrap">
      <div>
        <div class="text-muted small">Average</div>
        <div class="fw-700 fs-5">${overall.average?.toFixed(1) || '—'}</div>
      </div>
      <div>
        <div class="text-muted small">Maximum</div>
        <div class="fw-700 fs-5">${overall.max || '—'}</div>
      </div>
      <div>
        <div class="text-muted small">Risk Level</div>
        <div class="fw-700 fs-5 risk-${overall.risk || 'LOW'}" style="color:${riskColor(overall.risk)}">${overall.risk || '—'}</div>
      </div>
      <div>
        <div class="text-muted small">Grade</div>
        <div class="grade-badge" style="background:${riskColor(overall.risk)}22;color:${riskColor(overall.risk)}">${overall.grade || '—'}</div>
      </div>
    </div>
  `;

  const rows = fns.map(f => {
    const pct = (f.complexity / maxCx) * 100;
    return `
      <div class="complexity-row">
        <span class="complexity-name" title="${f.type}: ${f.name} (line ${f.line})">${truncate(f.name, 20)}</span>
        <div class="complexity-bar-wrap">
          <div class="complexity-bar">
            <div class="complexity-bar-fill risk-${f.risk}" style="width:${pct}%"></div>
          </div>
        </div>
        <span class="complexity-val" style="color:${riskColor(f.risk)}">${f.complexity}</span>
        <div class="grade-badge ms-2" style="background:${riskColor(f.risk)}22;color:${riskColor(f.risk)};font-size:.7rem">${f.grade}</div>
      </div>
    `;
  }).join('');

  const recs = (cx.recommendations || []).map(r => `<li class="mb-1">${escHtml(r)}</li>`).join('');

  content.innerHTML = overallHtml + rows + (recs ? `<ul class="mt-3 small text-secondary">${recs}</ul>` : '');
}

/* ─── DEFECT PREDICTION ─── */
function renderDefectPrediction(data) {
  const pred = data.defect_prediction || {};
  const content = document.getElementById('defectContent');
  if (!Object.keys(pred).length) {
    content.innerHTML = '<div class="empty-state"><i class="bi bi-robot"></i>No prediction data</div>';
    return;
  }

  const score = pred.score || 0;
  const category = pred.category || 'LOW';
  const color = riskColor(category);
  const components = pred.components || {};
  const recs = (pred.recommendations || []).slice(0, 4);

  const compRows = Object.entries(components).map(([k, v]) => `
    <div class="component-row">
      <span class="component-label">${k.replace('_', ' ')}</span>
      <div class="component-bar">
        <div class="component-bar-fill" style="width:${v.score}%;background:${color}88"></div>
      </div>
      <span class="component-val">${v.contribution.toFixed(1)}</span>
    </div>
  `).join('');

  const recsHtml = recs.map(r => `<li class="mb-1 small">${escHtml(r)}</li>`).join('');
  const methodology = pred.methodology_note || '';

  content.innerHTML = `
    <div class="d-flex align-items-center gap-3 mb-3">
      <div>
        <div class="risk-score-label" style="color:${color}">${score.toFixed(0)}<span class="fs-6 fw-400 text-muted">/100</span></div>
        <div class="risk-category mt-1" style="color:${color}">${category} RISK</div>
      </div>
      <div class="flex-grow-1">
        <div class="risk-meter">
          <div class="risk-meter-fill" style="width:${score}%;background:linear-gradient(90deg,${color}88,${color})"></div>
        </div>
        <div class="d-flex justify-content-between text-muted" style="font-size:.7rem;margin-top:.2rem">
          <span>Low</span><span>Moderate</span><span>High</span><span>Critical</span>
        </div>
      </div>
    </div>
    <div class="mb-3">
      <div class="text-muted small mb-2 fw-600">Component Contributions</div>
      ${compRows}
    </div>
    ${recs.length ? `<div class="text-muted small mb-2 fw-600">Recommendations</div><ul class="ps-3">${recsHtml}</ul>` : ''}
    <div class="alert-inline alert-methodology mt-3" style="background:rgba(245,158,11,.08);border-left:3px solid #f59e0b;padding:.6rem .9rem;border-radius:0 6px 6px 0;font-size:.75rem;color:#94a3b8">
      ⚠️ <strong>Methodology:</strong> ${escHtml(methodology.substring(0, 250))}…
    </div>
  `;
}

/* ─── SECURITY DETAIL ─── */
function renderSecurityDetail(data) {
  const findings = (data.findings || {}).bandit || [];
  const card = document.getElementById('securityDetailCard');
  const content = document.getElementById('securityDetail');

  if (!findings.length) {
    card.classList.add('d-none');
    return;
  }
  card.classList.remove('d-none');

  const rows = findings.map(f => `
    <div class="finding-row">
      <span class="finding-sev sev-${f.severity || 'LOW'}">${f.severity || 'LOW'}</span>
      <span class="finding-code">${escHtml(f.code || '')}</span>
      <span class="finding-line">L${f.line || '?'}</span>
      <span class="finding-msg flex-grow-1">${escHtml(f.message || '')}</span>
      <span class="text-muted" style="font-size:.75rem">${escHtml(f.name || '')}</span>
      ${f.cwe ? `<span class="finding-code">CWE-${f.cwe}</span>` : ''}
    </div>
  `).join('');

  content.innerHTML = rows;
}

/* ─── DOWNLOAD ─── */
function setupDownloadButtons(data) {
  const id = data.analysis_id;
  document.getElementById('downloadJsonBtn').onclick = () => {
    window.location.href = `/api/report/${id}?format=json`;
  };
  document.getElementById('downloadHtmlBtn').onclick = () => {
    window.location.href = `/api/report/${id}?format=html`;
  };
}

/* ═══════════════════════════════════════════════
   UI HELPERS
══════════════════════════════════════════════ */
function clearEditor() {
  editor.setValue('');
  document.getElementById('uploadedFilename').textContent = '';
  hideSyntaxAlert();
  document.getElementById('fileUpload').value = '';
}

function showSyntaxAlert(msg) {
  const el = document.getElementById('syntaxAlert');
  document.getElementById('syntaxMessage').textContent = msg;
  el.classList.remove('d-none');
}

function hideSyntaxAlert() {
  document.getElementById('syntaxAlert').classList.add('d-none');
}

function setAnalyzeBtn(enabled) {
  const btn = document.getElementById('analyzeBtn');
  btn.disabled = !enabled;
  btn.innerHTML = enabled
    ? '<i class="bi bi-play-circle-fill me-2"></i>Run Analysis'
    : '<i class="bi bi-hourglass-split me-2"></i>Analysing…';
}

function setNavStatus(msg, type) {
  const el = document.getElementById('analysisStatus');
  el.textContent = msg;
  el.style.color = type === 'done' ? '#22c55e' : type === 'analysing' ? '#f59e0b' : '';
}

const LOADING_STEPS = ['pytest', 'coverage', 'static', 'bandit', 'style', 'complexity', 'predict'];

function showLoadingOverlay() {
  const overlay = document.getElementById('loadingOverlay');
  overlay.classList.remove('d-none');
  // Animate steps
  let i = 0;
  document.querySelectorAll('.loading-step').forEach(s => {
    s.className = 'loading-step';
    s.querySelector('i').className = 'bi bi-clock me-2';
  });
  loadingInterval = setInterval(() => {
    if (i < LOADING_STEPS.length) {
      const step = document.querySelector(`.loading-step[data-step="${LOADING_STEPS[i]}"]`);
      if (step) {
        step.classList.add('active');
        step.querySelector('i').className = 'bi bi-gear-wide-connected me-2';
      }
      if (i > 0) {
        const prev = document.querySelector(`.loading-step[data-step="${LOADING_STEPS[i - 1]}"]`);
        if (prev) {
          prev.classList.remove('active');
          prev.classList.add('done');
          prev.querySelector('i').className = 'bi bi-check-circle me-2';
        }
      }
      i++;
    }
  }, 3500);
}

function hideLoadingOverlay() {
  if (loadingInterval) clearInterval(loadingInterval);
  document.getElementById('loadingOverlay').classList.add('d-none');
}

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function truncate(str, len) {
  return str.length > len ? str.substring(0, len) + '…' : str;
}

function riskColor(risk) {
  const map = { LOW: '#22c55e', MODERATE: '#f59e0b', HIGH: '#f97316', CRITICAL: '#ef4444' };
  return map[risk] || '#6b7280';
}
