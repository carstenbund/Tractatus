/**
 * Tractatus Web Interface - Frontend Application
 */

const API_BASE = '/api';
const MAX_HISTORY = 20;
const LAST_PROP_COOKIE = 'lastPropositionId';

// State
let commandHistory = [];
let currentLanguage = 'en';
let currentTreeData = [];
let treeLayoutNodes = [];
let activePropositionId = null;

// DOM Elements
const commandInput = document.getElementById('commandInput');
const commandBtn = document.getElementById('commandBtn');
const currentName = document.getElementById('currentName');
const currentText = document.getElementById('currentText');
const propId = document.getElementById('propId');
const propLevel = document.getElementById('propLevel');
const childrenList = document.getElementById('childrenList');
const treeView = document.getElementById('treeView');
const treeCanvas = document.getElementById('treeCanvas');
const treeEmpty = document.getElementById('treeEmpty');
const treeTooltip = document.getElementById('treeTooltip');
const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');
const agentAction = document.getElementById('agentAction');
const agentTargets = document.getElementById('agentTargets');
const agentResponse = document.getElementById('agentResponse');
const agentSpinner = document.getElementById('agentSpinner');
const agentPrompt = document.getElementById('agentPrompt');
const configList = document.getElementById('configList');
const messageBox = document.getElementById('messageBox');
const errorBox = document.getElementById('errorBox');
const commandHistoryEl = document.getElementById('commandHistory');

const TREE_LAYOUT = {
    paddingX: 48,
    paddingY: 80,
    levelHeight: 120,
    nodeRadius: 18,
    minWidth: 280,
    minHeight: 280,
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadInitialData();
});

function setupEventListeners() {
    commandBtn.addEventListener('click', () => executeCommandFromInput());
    commandInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') executeCommandFromInput();
    });
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    if (treeCanvas) {
        treeCanvas.addEventListener('click', handleTreeCanvasClick);
        treeCanvas.addEventListener('mousemove', handleTreeCanvasHover);
        treeCanvas.addEventListener('mouseleave', hideTreeTooltip);
    }

    window.addEventListener('resize', () => {
        renderTreeCanvas();
    });
}

function loadInitialData() {
    // Load config
    fetch(`${API_BASE}/config`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                displayConfig(data.data);
            }
        })
        .catch(err => showError(`Failed to load config: ${err}`));

    // Try to load a starting proposition
    const lastPropId = getCookie(LAST_PROP_COOKIE);
    if (lastPropId) {
        executeCommand(`get id:${lastPropId}`);
    } else {
        executeCommand('get 1');
    }
}

/**
 * Execute command from input field
 */
function executeCommandFromInput() {
    const command = commandInput.value.trim();
    if (!command) return;

    executeCommand(command);
    addToHistory(command);
    commandInput.value = '';
}

/**
 * Execute a command with support for CLI-style shortcuts
 */
function executeCommand(command) {
    const text = command.trim();
    if (!text) return;

    // --- 1. Handle "ag:" prefix (e.g., "ag:comment 1.1" or "ag:1") ---
    if (text.startsWith('ag:')) {
        const remainder = text.substring(3).trim();
        if (remainder) {
            const parts = remainder.split(/\s+/);
            // Check if first part looks like an action
            const actions = ['comment', 'comparison', 'compare', 'websearch', 'web', 'reference', 'ref'];
            if (actions.includes(parts[0].toLowerCase())) {
                apiAgent(parts[0].toLowerCase(), parts.slice(1), '');
            } else {
                // Treat as targets with default comment action
                apiAgent('comment', parts, '');
            }
        }
        return;
    }

    // --- 2. Handle inline agent (e.g., "1 ag" or "1 ag:comment") ---
    if (text.includes(' ag')) {
        const [head, tail] = text.split(/\s+ag/, 2);
        if (head) {
            // First execute the navigation
            executeCommand(head);
        }
        // Then execute agent action
        if (tail && tail.startsWith(':')) {
            // "1 ag:comment" format
            const action = tail.substring(1).trim().split(/\s+/)[0] || 'comment';
            apiAgent(action, [], '');
        } else {
            // "1 ag" format - default to comment
            apiAgent('comment', [], '');
        }
        return;
    }

    // --- 3. Handle range queries (e.g., "1-2" or "1:2") ---
    if (/^\d+(\.\d+)*\s*[-:]\s*\d+(\.\d+)*$/.test(text)) {
        apiGet(text);
        return;
    }

    // --- 4. Handle bare numbers or id:/name: prefixes ---
    if (/^\d/.test(text) || text.startsWith('id:') || text.startsWith('name:')) {
        apiGet(text);
        return;
    }

    // --- 5. Standard command parsing ---
    const parts = text.split(/\s+/);
    const cmd = parts[0].toLowerCase();
    const args = parts.slice(1);

    switch (cmd) {
        case 'get':
            apiGet(args.join(' '));
            break;
        case 'list':
            apiList(args.join(' ') || undefined);
            break;
        case 'children':
            apiChildren();
            break;
        case 'parent':
            apiParent();
            break;
        case 'next':
        case 'n':
            apiNext();
            break;
        case 'previous':
        case 'prev':
        case 'p':
            apiPrevious();
            break;
        case 'tree':
            apiTree(args.join(' ') || undefined);
            break;
        case 'search':
            apiSearch(args.join(' '));
            break;
        case 'translations':
            apiTranslations();
            break;
        case 'translate':
            apiTranslate(args[0]);
            break;
        case 'ag':
        case 'agent':
            apiAgent(args[0] || 'comment', args.slice(1), '');
            break;
        default:
            showError(`Unknown command: ${cmd}`);
    }
}

/**
 * API Calls
 */
async function apiGet(key) {
    if (!key) {
        showError('Usage: get <name or id:N>');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/get`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key }),
        });
        const data = await res.json();

        if (data.success) {
            displayProposition(data.data);
            showMessage(`Loaded: ${data.data.name}`);
            refreshTree();
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

async function apiList(target) {
    try {
        const res = await fetch(`${API_BASE}/list`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target || '' }),
        });
        const data = await res.json();

        if (data.success) {
            displayChildren(data.data.children);
            if (data.data.current) {
                displayProposition(data.data.current);
                refreshTree();
            }
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

async function apiChildren() {
    try {
        const res = await fetch(`${API_BASE}/children`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            displayChildren(data.data.children);
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

async function apiParent() {
    try {
        const res = await fetch(`${API_BASE}/parent`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            displayProposition(data.data);
            showMessage('Moved to parent');
            refreshTree();
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

async function apiNext() {
    try {
        const res = await fetch(`${API_BASE}/next`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            displayProposition(data.data);
            showMessage('Next proposition');
            refreshTree();
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

async function apiPrevious() {
    try {
        const res = await fetch(`${API_BASE}/previous`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            displayProposition(data.data);
            showMessage('Previous proposition');
            refreshTree();
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

async function apiTree(target, options = {}) {
    const { updateCurrent = true } = options;
    try {
        const res = await fetch(`${API_BASE}/tree`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target || '' }),
        });
        const data = await res.json();

        if (data.success) {
            displayTree(data.data.tree);
            if (updateCurrent && data.data.current) {
                displayProposition(data.data.current);
            }
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

function refreshTree(target) {
    apiTree(target, { updateCurrent: false });
}

async function apiSearch(term) {
    if (!term) {
        showError('Search term required');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ term }),
        });
        const data = await res.json();

        if (data.success) {
            displaySearchResults(data.data.results);
            showMessage(`Found ${data.data.count} results`);
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

function performSearch() {
    const term = searchInput.value.trim();
    apiSearch(term);
}

async function apiTranslations() {
    try {
        const res = await fetch(`${API_BASE}/translations`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            displayTranslations(data.data.translations);
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

async function apiTranslate(lang) {
    if (!lang) {
        showError('Language code required (e.g., "en", "de")');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lang }),
        });
        const data = await res.json();

        if (data.success) {
            showMessage(`Translation (${lang}): ${data.data.translation.text.substring(0, 100)}...`);
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

async function apiAgent(action, targets, userInput) {
    try {
        // Clear previous response and show spinner
        if (agentResponse) {
            agentResponse.innerHTML = '';
        }
        if (agentSpinner) {
            agentSpinner.classList.remove('hidden');
        }

        const res = await fetch(`${API_BASE}/agent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: action || 'comment',
                targets: targets && targets.length > 0 ? targets : [],
                language: currentLanguage,
                user_input: userInput || '',
            }),
        });
        const data = await res.json();

        // Hide spinner
        if (agentSpinner) {
            agentSpinner.classList.add('hidden');
        }

        if (data.success) {
            displayAgentResponse(data.data, userInput);
        } else {
            showError(data.error);
        }
    } catch (err) {
        // Hide spinner on error
        if (agentSpinner) {
            agentSpinner.classList.add('hidden');
        }
        showError(`API error: ${err}`);
    }
}

function invokeAgent() {
    const action = agentAction.value;
    const targetsStr = agentTargets.value.trim();
    const targets = targetsStr ? targetsStr.split(/\s+/) : [];
    const userInput = agentPrompt ? agentPrompt.value.trim() : '';
    apiAgent(action, targets, userInput);
    if (agentPrompt) {
        agentPrompt.value = '';
    }
}

function changeLanguage() {
    const select = document.getElementById('languageSelect');
    currentLanguage = select.value;
    showMessage(`Language changed to ${currentLanguage === 'de' ? 'Deutsch' : 'English'}`);

    // Reload current proposition in new language
    if (document.getElementById('currentName').textContent !== 'No proposition loaded') {
        loadInitialData();
    }
}

async function setConfigValue(key) {
    const input = document.getElementById(`config-input-${key}`);
    const value = input.value;

    try {
        const res = await fetch(`${API_BASE}/config/set`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, value }),
        });
        const data = await res.json();

        if (data.success) {
            showMessage(`Updated ${key} = ${value}`);
            loadInitialData(); // Reload config
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

/**
 * Display Functions
 */
function displayProposition(prop) {
    currentName.textContent = prop.name || 'Unknown';
    currentText.textContent = prop.text || '';
    propId.textContent = `ID: ${prop.id}`;
    propLevel.textContent = `Level: ${prop.level || 'N/A'}`;
    if (prop.language) {
        currentLanguage = prop.language;
    }
    activePropositionId = prop.id;
    if (prop && typeof prop.id !== 'undefined' && prop.id !== null) {
        setCookie(LAST_PROP_COOKIE, prop.id, 365);
    }
    renderTreeCanvas();
}

function displayChildren(children) {
    if (!children || children.length === 0) {
        childrenList.innerHTML = '<p>No children</p>';
        return;
    }

    childrenList.innerHTML = children
        .map(
            (child) =>
                `<div class="list-item" onclick="executeCommand('get ${child.name}')">
            <div class="list-item-name">${child.name}</div>
            <div class="list-item-text">${child.text_short}</div>
        </div>`
        )
        .join('');
}

function displayTree(treeData) {
    currentTreeData = Array.isArray(treeData) ? treeData : [];
    if (!currentTreeData.length) {
        if (treeEmpty) {
            treeEmpty.classList.remove('hidden');
        }
        hideTreeTooltip();
        renderTreeCanvas();
        return;
    }

    if (treeEmpty) {
        treeEmpty.classList.add('hidden');
    }
    renderTreeCanvas();
}

function displaySearchResults(results) {
    if (!results || results.length === 0) {
        searchResults.innerHTML = '<p>No results</p>';
        return;
    }

    searchResults.innerHTML = results
        .map(
            (result) =>
                `<div class="list-item" onclick="executeCommand('get ${result.name}')">
            <div class="list-item-name">${result.name}</div>
            <div class="list-item-text">${result.text_short}</div>
        </div>`
        )
        .join('');
}

function displayTranslations(translations) {
    if (!translations || translations.length === 0) {
        searchResults.innerHTML = '<p>No translations</p>';
        return;
    }

    searchResults.innerHTML = translations
        .map(
            (t) =>
                `<div class="list-item">
            <div class="list-item-name">${t.lang} (${t.source})</div>
            <div class="list-item-text">${t.text.substring(0, 100)}...</div>
        </div>`
        )
        .join('');
}

function displayAgentResponse(response, userInput) {
    if (!agentResponse) return;

    if (userInput) {
        appendAgentMessage('user', userInput.trim());
    }

    const actionLabel = response && response.action ? response.action : 'Assistant';
    const content = response && response.content ? response.content : '';
    const propositions = response && Array.isArray(response.propositions)
        ? response.propositions
        : [];
    appendAgentMessage('assistant', content, actionLabel, propositions);
    switchTab('agent');
}

function setCookie(name, value, days = 365) {
    const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/`;
}

function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split('; ') : [];
    for (const cookie of cookies) {
        if (cookie.startsWith(`${name}=`)) {
            return decodeURIComponent(cookie.substring(name.length + 1));
        }
    }
    return null;
}

function appendAgentMessage(role, message, actionLabel, propositions = []) {
    if (!agentResponse) return;

    const container = document.createElement('div');
    container.className = `agent-msg agent-msg-${role}`;

    if (role === 'user') {
        const title = document.createElement('div');
        title.className = 'agent-msg-title';
        title.textContent = 'You';
        container.appendChild(title);
    }

    if (role === 'assistant' && actionLabel) {
        const title = document.createElement('div');
        title.className = 'agent-msg-title';
        title.textContent = actionLabel;
        container.appendChild(title);
    }

    if (
        role === 'assistant' &&
        Array.isArray(propositions) &&
        propositions.length > 0
    ) {
        const meta = document.createElement('div');
        meta.className = 'agent-msg-meta';
        const names = propositions.map((p) => p.name).join(', ');
        meta.textContent = `Propositions: ${names}`;
        container.appendChild(meta);
    }

    const body = document.createElement('div');
    body.className = 'agent-msg-content';
    body.textContent = message || '';
    container.appendChild(body);

    agentResponse.appendChild(container);
    agentResponse.scrollTop = agentResponse.scrollHeight;
}

/**
 * Tree Rendering & Interaction
 */
function renderTreeCanvas() {
    if (!treeCanvas || !treeView) {
        return;
    }

    hideTreeTooltip();

    const containerWidth = treeView.clientWidth || TREE_LAYOUT.minWidth;
    const width = Math.max(containerWidth, TREE_LAYOUT.minWidth);

    if (!currentTreeData.length) {
        const canvas = prepareTreeCanvas(width, TREE_LAYOUT.minHeight);
        if (canvas) {
            canvas.ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        treeLayoutNodes = [];
        return;
    }

    const root = buildTreeHierarchy(currentTreeData);
    if (!root) {
        const canvas = prepareTreeCanvas(width, TREE_LAYOUT.minHeight);
        if (canvas) {
            canvas.ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        treeLayoutNodes = [];
        return;
    }

    const { maxDepth, leafCount } = assignTreeCoordinates(root);
    const height = Math.max(
        TREE_LAYOUT.minHeight,
        TREE_LAYOUT.paddingY * 2 + TREE_LAYOUT.levelHeight * Math.max(maxDepth, 1)
    );
    const canvas = prepareTreeCanvas(width, height);
    if (!canvas) {
        return;
    }

    const availableWidth = Math.max(
        canvas.width - TREE_LAYOUT.paddingX * 2,
        TREE_LAYOUT.minWidth - TREE_LAYOUT.paddingX * 2
    );
    const horizontalUnit = leafCount > 1 ? availableWidth / (leafCount - 1) : 0;
    const centerX = TREE_LAYOUT.paddingX + availableWidth / 2;

    function applyPositions(node) {
        node.screenX =
            leafCount > 1
                ? TREE_LAYOUT.paddingX + node.xIndex * horizontalUnit
                : centerX;
        node.screenY = TREE_LAYOUT.paddingY + node.depth * TREE_LAYOUT.levelHeight;
        node.children.forEach((child) => applyPositions(child));
    }

    applyPositions(root);

    treeLayoutNodes = [];
    collectTreeNodes(root);

    const ctx = canvas.ctx;
    ctx.strokeStyle = '#c3cdf6';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    drawTreeConnections(ctx, root);

    drawTreeNodes(ctx, root);
}

function prepareTreeCanvas(width, height) {
    if (!treeCanvas) return null;
    const ratio = window.devicePixelRatio || 1;
    const adjustedWidth = Math.max(width, TREE_LAYOUT.minWidth);
    const adjustedHeight = Math.max(height, TREE_LAYOUT.minHeight);
    treeCanvas.width = adjustedWidth * ratio;
    treeCanvas.height = adjustedHeight * ratio;
    treeCanvas.style.width = `${adjustedWidth}px`;
    treeCanvas.style.height = `${adjustedHeight}px`;
    const ctx = treeCanvas.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(ratio, ratio);
    ctx.clearRect(0, 0, adjustedWidth, adjustedHeight);
    return { ctx, width: adjustedWidth, height: adjustedHeight };
}

function buildTreeHierarchy(treeData) {
    if (!Array.isArray(treeData) || !treeData.length) {
        return null;
    }

    // Reconstruct the hierarchy using the depth values provided by the API
    // response. Building the tree purely from ``parent_id`` can re-create
    // accidental cycles that exist in the database (e.g. a node referencing
    // itself as the parent), which in turn caused recursive rendering helpers
    // to overflow the stack. By relying on the pre-computed depth ordering we
    // preserve the intended structure and avoid self-references.
    const nodes = treeData.map((item) => ({ ...item, children: [] }));
    const stack = [];

    nodes.forEach((node) => {
        while (stack.length && stack[stack.length - 1].depth >= node.depth) {
            stack.pop();
        }

        if (stack.length) {
            stack[stack.length - 1].children.push(node);
        }

        stack.push(node);
    });

    return nodes[0];
}

function assignTreeCoordinates(root) {
    let leafIndex = 0;
    let maxDepth = 0;

    function traverse(node, depth) {
        node.depth = depth;
        maxDepth = Math.max(maxDepth, depth);
        if (!node.children.length) {
            node.xIndex = leafIndex;
            leafIndex += 1;
        } else {
            node.children.forEach((child) => traverse(child, depth + 1));
            const first = node.children[0].xIndex;
            const last = node.children[node.children.length - 1].xIndex;
            node.xIndex = (first + last) / 2;
        }
    }

    traverse(root, 0);
    return { maxDepth, leafCount: Math.max(leafIndex, 1) };
}

function collectTreeNodes(node) {
    treeLayoutNodes.push(node);
    node.children.forEach((child) => collectTreeNodes(child));
}

function drawTreeConnections(ctx, node) {
    node.children.forEach((child) => {
        ctx.beginPath();
        ctx.moveTo(node.screenX, node.screenY);
        ctx.lineTo(child.screenX, child.screenY);
        ctx.stroke();
        drawTreeConnections(ctx, child);
    });
}

function drawTreeNodes(ctx, node) {
    const isActive = activePropositionId === node.id;
    const radius = TREE_LAYOUT.nodeRadius;

    ctx.beginPath();
    ctx.fillStyle = isActive ? '#667eea' : '#ffffff';
    ctx.strokeStyle = isActive ? '#667eea' : '#2f2f2f';
    ctx.lineWidth = isActive ? 3 : 1.5;
    ctx.arc(node.screenX, node.screenY, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.font = isActive ? '600 13px "Segoe UI", sans-serif' : '12px "Segoe UI", sans-serif';
    ctx.fillStyle = isActive ? '#ffffff' : '#333333';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText(node.name, node.screenX, node.screenY - radius - 8);

    node.children.forEach((child) => drawTreeNodes(ctx, child));
}

function handleTreeCanvasClick(event) {
    if (!treeCanvas || treeLayoutNodes.length === 0) return;
    const { x, y } = getRelativeCanvasPoint(event);
    const hit = findTreeNodeAt(x, y);
    if (hit) {
        executeCommand(`get ${hit.name}`);
    }
}

function handleTreeCanvasHover(event) {
    if (!treeCanvas || treeLayoutNodes.length === 0 || !treeTooltip) return;
    const { x, y } = getRelativeCanvasPoint(event);
    const hit = findTreeNodeAt(x, y);
    if (!hit) {
        hideTreeTooltip();
        return;
    }
    showTreeTooltip(hit, event);
}

function getRelativeCanvasPoint(event) {
    const rect = treeCanvas.getBoundingClientRect();
    return {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
    };
}

function findTreeNodeAt(x, y) {
    const radius = TREE_LAYOUT.nodeRadius + 4;
    return treeLayoutNodes.find((node) => {
        const dx = x - node.screenX;
        const dy = y - node.screenY;
        return Math.sqrt(dx * dx + dy * dy) <= radius;
    });
}

function showTreeTooltip(node, event) {
    if (!treeTooltip || !treeView) return;

    treeTooltip.innerHTML = '';
    const title = document.createElement('div');
    title.className = 'tree-tooltip-title';
    title.textContent = node.name;
    const body = document.createElement('div');
    body.className = 'tree-tooltip-body';
    body.textContent = node.text_short || node.text || '';
    treeTooltip.appendChild(title);
    treeTooltip.appendChild(body);

    treeTooltip.classList.remove('hidden');
    treeTooltip.classList.add('show');
    treeTooltip.style.left = '0px';
    treeTooltip.style.top = '0px';

    const containerRect = treeView.getBoundingClientRect();
    const tooltipWidth = treeTooltip.offsetWidth;
    const tooltipHeight = treeTooltip.offsetHeight;

    let left = event.clientX - containerRect.left + 16;
    let top = event.clientY - containerRect.top - tooltipHeight - 16;

    const maxLeft = containerRect.width - tooltipWidth - 16;
    left = Math.max(16, Math.min(left, maxLeft));
    if (top < 16) {
        top = event.clientY - containerRect.top + 16;
    }
    const maxTop = containerRect.height - tooltipHeight - 16;
    top = Math.max(16, Math.min(top, maxTop));

    treeTooltip.style.left = `${left}px`;
    treeTooltip.style.top = `${top}px`;
}

function hideTreeTooltip() {
    if (!treeTooltip) return;
    treeTooltip.classList.add('hidden');
    treeTooltip.classList.remove('show');
}

function displayConfig(config) {
    if (config && typeof config.lang === 'string' && config.lang) {
        currentLanguage = config.lang;
    }
    configList.innerHTML = Object.entries(config)
        .map(
            ([key, value]) =>
                `<div class="config-item">
            <div class="config-item-key">${key}</div>
            <div class="config-item-value">
                <input
                    type="text"
                    id="config-input-${key}"
                    value="${value}"
                    onkeypress="if(event.key==='Enter') setConfigValue('${key}')"
                />
                <button onclick="setConfigValue('${key}')">Save</button>
            </div>
        </div>`
        )
        .join('');
}

/**
 * Utility Functions
 */
function switchTab(tabName, evt) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach((tab) => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach((btn) => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const tab = document.getElementById(`${tabName}-tab`);
    if (tab) {
        tab.classList.add('active');
        // Mark button as active
        if (evt && evt.target) {
            evt.target.classList.add('active');
        } else {
            const button = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
            if (button) {
                button.classList.add('active');
            }
        }
        if (tabName === 'tree') {
            renderTreeCanvas();
        }
    }
}

function showMessage(msg) {
    messageBox.textContent = msg;
    messageBox.classList.add('show');
    messageBox.classList.remove('hidden');
    setTimeout(() => {
        messageBox.classList.remove('show');
    }, 3000);
}

function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.add('show');
    errorBox.classList.remove('hidden');
    setTimeout(() => {
        errorBox.classList.remove('show');
    }, 5000);
}

function addToHistory(command) {
    commandHistory.push(command);
    if (commandHistory.length > MAX_HISTORY) {
        commandHistory.shift();
    }

    commandHistoryEl.innerHTML = commandHistory
        .slice()
        .reverse()
        .map(
            (cmd) =>
                `<div class="history-item" onclick="commandInput.value='${cmd.replace(/'/g, "\\'")}'; executeCommandFromInput();">${cmd}</div>`
        )
        .join('');
}
