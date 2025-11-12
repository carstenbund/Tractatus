/**
 * Tractatus Web Interface - Frontend Application
 */

const API_BASE = '/api';
const MAX_HISTORY = 20;

// State
let commandHistory = [];
let currentLanguage = 'en';

// DOM Elements
const commandInput = document.getElementById('commandInput');
const commandBtn = document.getElementById('commandBtn');
const currentName = document.getElementById('currentName');
const currentText = document.getElementById('currentText');
const propId = document.getElementById('propId');
const propLevel = document.getElementById('propLevel');
const childrenList = document.getElementById('childrenList');
const treeView = document.getElementById('treeView');
const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');
const agentAction = document.getElementById('agentAction');
const agentTargets = document.getElementById('agentTargets');
const agentResponse = document.getElementById('agentResponse');
const configList = document.getElementById('configList');
const messageBox = document.getElementById('messageBox');
const errorBox = document.getElementById('errorBox');
commandHistory = document.getElementById('commandHistory');

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
    executeCommand('get 1');
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
 * Execute a command
 */
function executeCommand(command) {
    const parts = command.split(/\s+/);
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
            apiAgent(args[0] || 'comment', args.slice(1));
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
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

async function apiTree(target) {
    try {
        const res = await fetch(`${API_BASE}/tree`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target || '' }),
        });
        const data = await res.json();

        if (data.success) {
            displayTree(data.data.tree);
            if (data.data.current) {
                displayProposition(data.data.current);
            }
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
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

async function apiAgent(action, targets) {
    try {
        const res = await fetch(`${API_BASE}/agent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: action || 'comment',
                targets: targets && targets.length > 0 ? targets : [],
                language: currentLanguage,
            }),
        });
        const data = await res.json();

        if (data.success) {
            displayAgentResponse(data.data);
        } else {
            showError(data.error);
        }
    } catch (err) {
        showError(`API error: ${err}`);
    }
}

function invokeAgent() {
    const action = agentAction.value;
    const targetsStr = agentTargets.value.trim();
    const targets = targetsStr ? targetsStr.split(/\s+/) : [];
    apiAgent(action, targets);
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
    if (!treeData || treeData.length === 0) {
        treeView.innerHTML = '<p>No tree data</p>';
        return;
    }

    treeView.innerHTML = treeData
        .map(
            (item) =>
                `<div class="tree-item level-${item.depth}" onclick="executeCommand('get ${item.name}')">
            ${item.name}: ${item.text_short}
        </div>`
        )
        .join('');
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

function displayAgentResponse(response) {
    agentResponse.classList.remove('empty');
    agentResponse.textContent = response.content;
    switchTab('agent');
}

function displayConfig(config) {
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
function switchTab(tabName) {
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
        event.target.classList.add('active');
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

    const historyList = document.getElementById('commandHistory');
    historyList.innerHTML = commandHistory
        .slice()
        .reverse()
        .map(
            (cmd) =>
                `<div class="history-item" onclick="commandInput.value='${cmd.replace(/'/g, "\\'")}'; executeCommandFromInput();">${cmd}</div>`
        )
        .join('');
}
