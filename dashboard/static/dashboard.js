let refreshInterval = null;
let lastUpdateTime = null;

const RETAILER_CONFIG = {
    verizon: { name: 'Verizon', logo: 'VZ', class: 'verizon' },
    att: { name: 'AT&T', logo: 'AT', class: 'att' },
    target: { name: 'Target', logo: 'TG', class: 'target' },
    tmobile: { name: 'T-Mobile', logo: 'TM', class: 'tmobile' },
    walmart: { name: 'Walmart', logo: 'WM', class: 'walmart' },
    bestbuy: { name: 'Best Buy', logo: 'BB', class: 'bestbuy' }
};

function formatNumber(num) {
    if (num === null || num === undefined) return '—';
    return num.toLocaleString();
}

function formatDuration(seconds) {
    if (!seconds || seconds <= 0) return '—';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
    } else if (minutes > 0) {
        return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
    } else {
        return `${secs}s`;
    }
}

function getTimeSinceUpdate() {
    if (!lastUpdateTime) return '';
    
    const now = Date.now();
    const diff = Math.floor((now - lastUpdateTime) / 1000);
    
    if (diff < 5) return 'just now';
    if (diff < 60) return `${diff} seconds ago`;
    if (diff < 3600) {
        const mins = Math.floor(diff / 60);
        return `${mins} minute${mins > 1 ? 's' : ''} ago`;
    }
    
    const hours = Math.floor(diff / 3600);
    return `${hours} hour${hours > 1 ? 's' : ''} ago`;
}

function updateLastRefreshTime() {
    const element = document.getElementById('last-refresh');
    if (element && lastUpdateTime) {
        element.textContent = `Last refresh: ${getTimeSinceUpdate()}`;
    }
}

function getStatusInfo(retailer) {
    const status = retailer.status || 'pending';
    const statusMap = {
        running: { class: 'status-running', text: 'Running' },
        complete: { class: 'status-complete', text: 'Complete' },
        pending: { class: 'status-pending', text: 'Pending' },
        disabled: { class: 'status-disabled', text: 'Disabled' }
    };
    
    return statusMap[status] || statusMap.pending;
}

function renderPhases(retailer) {
    const phases = retailer.phases || [];
    if (phases.length === 0) {
        return '<span class="phase-tag phase-pending">No data</span>';
    }
    
    return phases.map(phase => {
        let statusClass = 'phase-pending';
        let icon = '';
        
        if (phase.status === 'complete') {
            statusClass = 'phase-complete';
            icon = ' ✓';
        } else if (phase.status === 'in_progress') {
            statusClass = 'phase-active';
            icon = ' ⟳';
        }
        
        return `<span class="phase-tag ${statusClass}">${phase.name}${icon}</span>`;
    }).join('');
}

function renderRetailerCard(retailerId, data) {
    const config = RETAILER_CONFIG[retailerId];
    if (!config) return '';
    
    const statusInfo = getStatusInfo(data);
    const progress = data.progress?.percentage || 0;
    const progressText = data.progress?.text || '0 / 0 stores (0%)';
    
    const stats = data.stats || {};
    const stat1Value = stats.stat1_value || '—';
    const stat1Label = stats.stat1_label || 'Stores';
    const stat2Value = stats.stat2_value || '—';
    const stat2Label = stats.stat2_label || 'Duration';
    const stat3Value = stats.stat3_value || '—';
    const stat3Label = stats.stat3_label || 'Requests';
    
    return `
        <div class="retailer-card ${config.class}">
            <div class="retailer-header">
                <div class="retailer-name">
                    <div class="retailer-logo">${config.logo}</div>
                    ${config.name}
                </div>
                <span class="retailer-status ${statusInfo.class}">${statusInfo.text}</span>
            </div>
            <div class="retailer-body">
                <div class="progress-section">
                    <div class="progress-header">
                        <span class="progress-label">Extraction Progress</span>
                        <span class="progress-value">${progressText}</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">${stat1Value}</div>
                        <div class="stat-label">${stat1Label}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${stat2Value}</div>
                        <div class="stat-label">${stat2Label}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${stat3Value}</div>
                        <div class="stat-label">${stat3Label}</div>
                    </div>
                </div>
                <div class="phase-indicators">
                    ${renderPhases(data)}
                </div>
            </div>
            <button class="run-history-toggle" onclick="toggleRunHistory('${retailerId}')">
                📜 View Run History
            </button>
            <div class="run-history-panel" id="history-${retailerId}">
                <div class="run-history-list" id="history-list-${retailerId}">
                    <div class="run-history-empty">Loading...</div>
                </div>
            </div>
        </div>
    `;
}

function updateGlobalStatus(data) {
    const globalStatusEl = document.getElementById('global-status');
    const activeCount = data.summary?.active_scrapers || 0;
    
    if (activeCount > 0) {
        globalStatusEl.className = 'global-status active';
        globalStatusEl.innerHTML = `
            <div class="pulse"></div>
            ${activeCount} Scraper${activeCount > 1 ? 's' : ''} Running
        `;
    } else {
        globalStatusEl.className = 'global-status';
        globalStatusEl.innerHTML = 'All Scrapers Idle';
    }
}

function updateSummaryCards(data) {
    const summary = data.summary || {};
    
    document.getElementById('total-stores').textContent = formatNumber(summary.total_stores || 0);
    document.getElementById('active-retailers').textContent = `${summary.active_retailers || 0} / ${summary.total_retailers || 6}`;
    document.getElementById('overall-progress').textContent = `${(summary.overall_progress || 0).toFixed(1)}%`;
    document.getElementById('estimated-time').textContent = formatDuration(summary.estimated_remaining_seconds);
}

function updateRetailers(data) {
    const container = document.getElementById('retailer-grid');
    const retailers = data.retailers || {};
    
    let html = '';
    for (const [retailerId, retailerData] of Object.entries(RETAILER_CONFIG)) {
        const data = retailers[retailerId] || { status: 'pending' };
        html += renderRetailerCard(retailerId, data);
    }
    
    container.innerHTML = html;
}

async function updateDashboard() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        updateGlobalStatus(data);
        updateSummaryCards(data);
        updateRetailers(data);
        
        lastUpdateTime = Date.now();
        updateLastRefreshTime();
        
        const errorEl = document.getElementById('error-message');
        if (errorEl) {
            errorEl.style.display = 'none';
        }
        
    } catch (error) {
        console.error('Error fetching status:', error);
        
        let errorEl = document.getElementById('error-message');
        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.id = 'error-message';
            errorEl.className = 'error';
            document.querySelector('.container').insertBefore(
                errorEl,
                document.querySelector('.summary-row')
            );
        }
        
        errorEl.innerHTML = `<strong>Error loading dashboard:</strong> ${error.message}`;
        errorEl.style.display = 'block';
    }
}

function startAutoRefresh(intervalSeconds = 5) {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    updateDashboard();
    
    refreshInterval = setInterval(updateDashboard, intervalSeconds * 1000);
    
    setInterval(updateLastRefreshTime, 1000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

let currentLogRetailer = null;
let currentLogRunId = null;
let activeLogFilters = new Set(['ALL']);

function toggleRunHistory(retailer) {
    const panel = document.getElementById(`history-${retailer}`);
    const button = panel.previousElementSibling;
    const isOpen = panel.classList.contains('open');
    
    if (isOpen) {
        panel.classList.remove('open');
        button.classList.remove('active');
        button.textContent = '📜 View Run History';
    } else {
        panel.classList.add('open');
        button.classList.add('active');
        button.textContent = '📜 Hide Run History';
        loadRunHistory(retailer);
    }
}

async function loadRunHistory(retailer) {
    const listContainer = document.getElementById(`history-list-${retailer}`);
    listContainer.innerHTML = '<div class="run-history-empty">Loading...</div>';
    
    try {
        const response = await fetch(`/api/runs/${retailer}?limit=5`);
        const data = await response.json();
        
        if (data.error) {
            listContainer.innerHTML = `<div class="run-history-empty">Error: ${data.error}</div>`;
            return;
        }
        
        if (!data.runs || data.runs.length === 0) {
            listContainer.innerHTML = '<div class="run-history-empty">No runs found</div>';
            return;
        }
        
        listContainer.innerHTML = data.runs.map(run => createRunItem(retailer, run)).join('');
    } catch (error) {
        console.error('Error loading run history:', error);
        listContainer.innerHTML = `<div class="run-history-empty">Failed to load run history</div>`;
    }
}

function createRunItem(retailer, run) {
    const config = RETAILER_CONFIG[retailer];
    const runId = run.run_id || 'unknown';
    const status = run.status || 'unknown';
    const startTime = run.started_at ? new Date(run.started_at).toLocaleString() : '—';
    const endTime = run.completed_at ? new Date(run.completed_at).toLocaleString() : 'In progress';
    const stores = run.stats?.stores_scraped || 0;
    
    let statusClass = '';
    let statusText = status;
    
    if (status === 'complete') {
        statusClass = 'complete';
        statusText = 'Complete';
    } else if (status === 'failed') {
        statusClass = 'failed';
        statusText = 'Failed';
    } else if (status === 'running') {
        statusClass = 'running';
        statusText = 'Running';
    }
    
    return `
        <div class="run-item status-${status}">
            <div class="run-item-header">
                <span class="run-id">${runId}</span>
                <span class="run-status-badge ${statusClass}">${statusText}</span>
            </div>
            <div class="run-item-details">
                Started: ${startTime}<br>
                ${run.completed_at ? `Ended: ${endTime}<br>` : ''}
                Stores: ${formatNumber(stores)}
            </div>
            <div class="run-item-actions">
                <button class="btn-view-logs" onclick="openLogViewer('${retailer}', '${runId}')">
                    View Logs
                </button>
            </div>
        </div>
    `;
}

function openLogViewer(retailer, runId) {
    currentLogRetailer = retailer;
    currentLogRunId = runId;
    activeLogFilters = new Set(['ALL']);
    
    const config = RETAILER_CONFIG[retailer];
    const modal = document.getElementById('log-modal');
    const modalTitle = document.getElementById('log-modal-title');
    const logContainer = document.getElementById('log-content');
    
    modalTitle.textContent = `Logs - ${config.name} - ${runId}`;
    logContainer.innerHTML = '<div class="log-loading">Loading logs...</div>';
    
    modal.classList.add('open');
    
    updateLogFilterButtons();
    loadLogs();
}

function closeLogViewer() {
    const modal = document.getElementById('log-modal');
    modal.classList.remove('open');
    currentLogRetailer = null;
    currentLogRunId = null;
}

async function loadLogs() {
    const logContainer = document.getElementById('log-content');
    
    try {
        const response = await fetch(`/api/logs/${currentLogRetailer}/${currentLogRunId}`);
        const data = await response.json();
        
        if (data.error) {
            logContainer.innerHTML = `<div class="log-error">Error loading logs: ${data.error}</div>`;
            return;
        }
        
        const logContent = data.content || '';
        const lines = logContent.split('\n');
        
        const parsedLines = lines
            .filter(line => line.trim())
            .map(line => parseLogLine(line));
        
        displayLogs(parsedLines);
        updateLogStats(parsedLines);
    } catch (error) {
        console.error('Error loading logs:', error);
        logContainer.innerHTML = `<div class="log-error">Failed to load logs: ${error.message}</div>`;
    }
}

function parseLogLine(line) {
    const levelMatch = line.match(/\b(DEBUG|INFO|WARNING|ERROR)\b/);
    const level = levelMatch ? levelMatch[1] : 'INFO';
    
    const timestampMatch = line.match(/(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/);
    const timestamp = timestampMatch ? timestampMatch[1] : null;
    
    return {
        raw: line,
        level: level,
        timestamp: timestamp
    };
}

function displayLogs(parsedLines) {
    const logContainer = document.getElementById('log-content');
    
    const html = parsedLines.map(logLine => {
        const shouldShow = activeLogFilters.has('ALL') || activeLogFilters.has(logLine.level);
        const hiddenClass = shouldShow ? '' : 'hidden';
        
        let formattedLine = logLine.raw;
        
        if (logLine.level) {
            formattedLine = formattedLine.replace(
                new RegExp(`\\b${logLine.level}\\b`),
                `<span class="log-level ${logLine.level}">${logLine.level}</span>`
            );
        }
        
        if (logLine.timestamp) {
            formattedLine = formattedLine.replace(
                logLine.timestamp,
                `<span class="log-timestamp">${logLine.timestamp}</span>`
            );
        }
        
        return `<div class="log-line level-${logLine.level} ${hiddenClass}">${formattedLine}</div>`;
    }).join('');
    
    logContainer.innerHTML = `<div class="log-container">${html}</div>`;
}

function updateLogStats(parsedLines) {
    const total = parsedLines.length;
    const visible = parsedLines.filter(line => 
        activeLogFilters.has('ALL') || activeLogFilters.has(line.level)
    ).length;
    
    const statsElement = document.getElementById('log-stats');
    statsElement.textContent = `Showing ${visible} of ${total} lines`;
}

function toggleLogFilter(level) {
    if (level === 'ALL') {
        activeLogFilters.clear();
        activeLogFilters.add('ALL');
    } else {
        activeLogFilters.delete('ALL');
        
        if (activeLogFilters.has(level)) {
            activeLogFilters.delete(level);
        } else {
            activeLogFilters.add(level);
        }
        
        if (activeLogFilters.size === 0) {
            activeLogFilters.add('ALL');
        }
    }
    
    updateLogFilterButtons();
    
    const logLines = document.querySelectorAll('.log-line');
    logLines.forEach(line => {
        const lineLevel = Array.from(line.classList)
            .find(cls => cls.startsWith('level-'))
            ?.replace('level-', '');
        
        if (activeLogFilters.has('ALL') || activeLogFilters.has(lineLevel)) {
            line.classList.remove('hidden');
        } else {
            line.classList.add('hidden');
        }
    });
    
    const total = logLines.length;
    const visible = document.querySelectorAll('.log-line:not(.hidden)').length;
    document.getElementById('log-stats').textContent = `Showing ${visible} of ${total} lines`;
}

function updateLogFilterButtons() {
    const buttons = document.querySelectorAll('.log-filter-btn');
    buttons.forEach(btn => {
        const level = btn.dataset.level;
        if (activeLogFilters.has(level)) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    startAutoRefresh(5);
    
    const logModal = document.getElementById('log-modal');
    if (logModal) {
        logModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeLogViewer();
            }
        });
    }
});

document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        startAutoRefresh(5);
    }
});
