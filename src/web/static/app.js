// src/web/static/app.js
// IPTV 管理面板前端逻辑

// API 基础地址
const API_BASE = '/api';

// 当前选项卡
let currentTab = 'dashboard';
let currentPage = 1;
const pageSize = 50;

// DOM 引用
const tabs = document.querySelectorAll('nav li');
const tabContents = document.querySelectorAll('.tab-content');
const statusEls = {
    stableCount: document.getElementById('stableCount'),
    fixedCount: document.getElementById('fixedCount'),
    candidateCount: document.getElementById('candidateCount'),
    sourcePoolCount: document.getElementById('sourcePoolCount'),
    lastUpdate: document.getElementById('lastUpdate'),
    configDisplay: document.getElementById('configDisplay'),
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 切换选项卡
    tabs.forEach(li => {
        li.addEventListener('click', () => {
            const tab = li.dataset.tab;
            switchTab(tab);
        });
    });

    // 刷新按钮
    document.getElementById('refreshBtn')?.addEventListener('click', () => {
        if (currentTab === 'channels') loadChannels();
        else loadDashboard();
    });

    // 搜索和筛选
    document.getElementById('searchInput')?.addEventListener('input', loadChannels);
    document.getElementById('categoryFilter')?.addEventListener('change', loadChannels);
    document.getElementById('fixedOnly')?.addEventListener('change', loadChannels);

    // 添加固定源
    document.getElementById('addFixedBtn')?.addEventListener('click', addFixedSource);

    // 加载默认仪表盘
    loadDashboard();
});

// 切换选项卡
function switchTab(tab) {
    currentTab = tab;
    // 更新导航
    tabs.forEach(li => {
        li.classList.toggle('active', li.dataset.tab === tab);
    });
    // 更新内容
    tabContents.forEach(section => {
        section.classList.toggle('active', section.id === tab);
    });
    // 加载数据
    if (tab === 'dashboard') loadDashboard();
    else if (tab === 'channels') loadChannels();
    else if (tab === 'fixed') loadFixedSources();
    else if (tab === 'config') loadConfig();
}

// ---------- 仪表盘 ----------
async function loadDashboard() {
    try {
        const resp = await fetch(`${API_BASE}/status`);
        const data = await resp.json();
        statusEls.stableCount.textContent = data.stable_count || 0;
        statusEls.fixedCount.textContent = data.fixed_count || 0;
        statusEls.candidateCount.textContent = data.candidate_pool?.total || 0;
        statusEls.sourcePoolCount.textContent = data.source_pool?.total || 0;
        statusEls.lastUpdate.textContent = data.last_update ? `最后更新: ${data.last_update}` : '最后更新: --';
        if (data.config) {
            statusEls.configDisplay.textContent = JSON.stringify(data.config, null, 2);
        }
    } catch (e) {
        console.error('加载仪表盘失败:', e);
    }
}

// ---------- 频道列表 ----------
async function loadChannels() {
    const search = document.getElementById('searchInput')?.value || '';
    const category = document.getElementById('categoryFilter')?.value || '';
    const fixedOnly = document.getElementById('fixedOnly')?.checked || false;

    try {
        const params = new URLSearchParams({
            search,
            category,
            fixed_only: fixedOnly,
        });
        const resp = await fetch(`${API_BASE}/channels?${params}`);
        const data = await resp.json();
        renderChannels(data.channels || [], data.total || 0);
    } catch (e) {
        console.error('加载频道失败:', e);
    }
}

function renderChannels(channels, total) {
    const tbody = document.getElementById('channelTableBody');
    if (!channels.length) {
        tbody.innerHTML = '<tr><td colspan="6">暂无频道</td></tr>';
        return;
    }
    let html = '';
    channels.forEach(ch => {
        const fixedBadge = ch.is_fixed ? '<span class="fixed-badge">固定</span>' : '';
        const latency = ch.latency ? `${ch.latency}ms` : '--';
        html += `
            <tr>
                <td><strong>${ch.name}</strong></td>
                <td>${ch.category || '其他'}</td>
                <td>${latency}</td>
                <td>${ch.codec || 'unknown'}</td>
                <td>${fixedBadge}</td>
                <td>
                    ${ch.is_fixed ? `<button class="remove-btn" data-name="${ch.name}">取消固定</button>` : ''}
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;

    // 取消固定按钮事件
    tbody.querySelectorAll('.remove-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const name = btn.dataset.name;
            if (confirm(`确定要取消固定 "${name}" 吗？`)) {
                await removeFixedSource(name);
                loadChannels(); // 刷新列表
                loadDashboard(); // 刷新统计
            }
        });
    });
}

// ---------- 固定源管理 ----------
async function loadFixedSources() {
    try {
        const resp = await fetch(`${API_BASE}/channels?fixed_only=true`);
        const data = await resp.json();
        renderFixedSources(data.channels || []);
    } catch (e) {
        console.error('加载固定源失败:', e);
    }
}

function renderFixedSources(channels) {
    const tbody = document.getElementById('fixedTableBody');
    if (!channels.length) {
        tbody.innerHTML = '<tr><td colspan="3">暂无固定源</td></tr>';
        return;
    }
    let html = '';
    channels.forEach(ch => {
        html += `
            <tr>
                <td><strong>${ch.name}</strong></td>
                <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${ch.url}</td>
                <td><button class="remove-btn" data-name="${ch.name}">🗑️ 删除</button></td>
            </tr>
        `;
    });
    tbody.innerHTML = html;

    // 删除按钮事件
    tbody.querySelectorAll('.remove-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const name = btn.dataset.name;
            if (confirm(`确定要删除固定源 "${name}" 吗？`)) {
                await removeFixedSource(name);
                loadFixedSources(); // 刷新
                loadDashboard();
            }
        });
    });
}

async function removeFixedSource(name) {
    try {
        const resp = await fetch(`${API_BASE}/fixed_sources/${encodeURIComponent(name)}`, {
            method: 'DELETE',
        });
        const data = await resp.json();
        if (resp.ok) {
            showMessage('addFixedMessage', `已删除固定源: ${name}`, 'success');
        } else {
            showMessage('addFixedMessage', data.error || '删除失败', 'error');
        }
    } catch (e) {
        showMessage('addFixedMessage', '网络错误', 'error');
    }
}

async function addFixedSource() {
    const name = document.getElementById('fixedName').value.trim();
    const url = document.getElementById('fixedUrl').value.trim();
    if (!name || !url) {
        showMessage('addFixedMessage', '请填写完整的频道名和URL', 'error');
        return;
    }
    try {
        const resp = await fetch(`${API_BASE}/fixed_sources`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url }),
        });
        const data = await resp.json();
        if (resp.ok) {
            showMessage('addFixedMessage', `✅ ${data.message}`, 'success');
            document.getElementById('fixedName').value = '';
            document.getElementById('fixedUrl').value = '';
            loadFixedSources();
            loadDashboard();
        } else {
            showMessage('addFixedMessage', data.error || '添加失败', 'error');
        }
    } catch (e) {
        showMessage('addFixedMessage', '网络错误', 'error');
    }
}

function showMessage(id, text, type) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.className = 'message ' + type;
    setTimeout(() => { el.textContent = ''; el.className = 'message'; }, 5000);
}

// ---------- 系统配置 ----------
async function loadConfig() {
    try {
        const resp = await fetch(`${API_BASE}/config`);
        const data = await resp.json();
        document.getElementById('fullConfigDisplay').textContent = JSON.stringify(data, null, 2);
    } catch (e) {
        console.error('加载配置失败:', e);
    }
}
