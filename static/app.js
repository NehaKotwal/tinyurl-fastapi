// API Base URL
const API_BASE = window.location.origin;

// DOM Elements
const shortenForm = document.getElementById('shortenForm');
const originalUrlInput = document.getElementById('originalUrl');
const customAliasInput = document.getElementById('customAlias');
const resultSection = document.getElementById('resultSection');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');
const shortUrlInput = document.getElementById('shortUrlInput');
const copyBtn = document.getElementById('copyBtn');
const originalUrlDisplay = document.getElementById('originalUrlDisplay');
const shortCodeDisplay = document.getElementById('shortCodeDisplay');
const createdAtDisplay = document.getElementById('createdAtDisplay');
const urlListSection = document.getElementById('urlListSection');
const urlList = document.getElementById('urlList');
const emptyState = document.getElementById('emptyState');
const refreshBtn = document.getElementById('refreshBtn');
const statsModal = document.getElementById('statsModal');
const closeModal = document.getElementById('closeModal');
const statsContent = document.getElementById('statsContent');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadUrlList();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    shortenForm.addEventListener('submit', handleShortenSubmit);
    copyBtn.addEventListener('copy', handleCopy);
    refreshBtn.addEventListener('click', loadUrlList);
    closeModal.addEventListener('click', hideStatsModal);

    // Close modal on outside click
    statsModal.addEventListener('click', (e) => {
        if (e.target === statsModal) {
            hideStatsModal();
        }
    });
}

// Handle form submission
async function handleShortenSubmit(e) {
    e.preventDefault();

    hideError();
    hideResult();

    const originalUrl = originalUrlInput.value.trim();
    const customAlias = customAliasInput.value.trim();

    try {
        const payload = {
            original_url: originalUrl
        };

        if (customAlias) {
            payload.custom_alias = customAlias;
        }

        const response = await fetch(`${API_BASE}/api/shorten`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to shorten URL');
        }

        displayResult(data);
        shortenForm.reset();

        // Reload URL list
        loadUrlList();

    } catch (error) {
        showError(error.message);
    }
}

// Display result
function displayResult(data) {
    shortUrlInput.value = data.short_url;
    originalUrlDisplay.textContent = data.original_url;
    shortCodeDisplay.textContent = data.custom_alias || data.short_code;
    createdAtDisplay.textContent = formatDate(data.created_at);

    resultSection.classList.remove('hidden');
}

// Hide result
function hideResult() {
    resultSection.classList.add('hidden');
}

// Show error
function showError(message) {
    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
}

// Hide error
function hideError() {
    errorSection.classList.add('hidden');
}

// Copy to clipboard
copyBtn.addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText(shortUrlInput.value);

        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        copyBtn.style.background = '#10b981';
        copyBtn.style.color = 'white';

        setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.style.background = '';
            copyBtn.style.color = '';
        }, 2000);

    } catch (error) {
        showError('Failed to copy to clipboard');
    }
});

// Load URL list
async function loadUrlList() {
    try {
        urlListSection.classList.remove('hidden');
        urlList.classList.add('hidden');
        emptyState.classList.add('hidden');

        const response = await fetch(`${API_BASE}/api/urls?limit=20&offset=0`);

        if (!response.ok) {
            throw new Error('Failed to load URLs');
        }

        const urls = await response.json();

        urlListSection.classList.add('hidden');

        if (urls.length === 0) {
            emptyState.classList.remove('hidden');
        } else {
            displayUrlList(urls);
            urlList.classList.remove('hidden');
        }

    } catch (error) {
        urlListSection.classList.add('hidden');
        showError('Failed to load URL list: ' + error.message);
    }
}

// Display URL list
function displayUrlList(urls) {
    urlList.innerHTML = '';

    urls.forEach(url => {
        const urlItem = createUrlItem(url);
        urlList.appendChild(urlItem);
    });
}

// Create URL item element
function createUrlItem(url) {
    const item = document.createElement('div');
    item.className = 'url-item';

    const shortCode = url.custom_alias || url.short_code;
    const shortUrl = `${API_BASE}/${shortCode}`;

    item.innerHTML = `
        <div class="url-item-header">
            <div>
                <div class="url-short">${shortUrl}</div>
                <div class="url-original">${url.original_url}</div>
            </div>
            <div class="url-actions">
                <button class="btn-link" onclick="viewStats('${shortCode}')">Stats</button>
                <button class="btn-link" onclick="copyUrl('${shortUrl}')">Copy</button>
            </div>
        </div>
        <div class="url-meta">
            <span>Clicks: ${url.click_count}</span>
            <span>Created: ${formatDate(url.created_at)}</span>
            ${url.expires_at ? `<span>Expires: ${formatDate(url.expires_at)}</span>` : ''}
        </div>
    `;

    return item;
}

// View stats
async function viewStats(shortCode) {
    try {
        const response = await fetch(`${API_BASE}/api/urls/${shortCode}/stats`);

        if (!response.ok) {
            throw new Error('Failed to load statistics');
        }

        const stats = await response.json();
        displayStats(stats);

    } catch (error) {
        showError('Failed to load statistics: ' + error.message);
    }
}

// Display stats modal
function displayStats(stats) {
    const shortUrl = `${API_BASE}/${stats.custom_alias || stats.short_code}`;

    statsContent.innerHTML = `
        <div class="stat-row">
            <span class="stat-label">Short URL</span>
            <span class="stat-value">${shortUrl}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Original URL</span>
            <span class="stat-value" style="word-break: break-all;">${stats.original_url}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Short Code</span>
            <span class="stat-value">${stats.custom_alias || stats.short_code}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Total Clicks</span>
            <span class="stat-value">${stats.click_count}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Created</span>
            <span class="stat-value">${formatDate(stats.created_at)}</span>
        </div>
        ${stats.last_accessed_at ? `
        <div class="stat-row">
            <span class="stat-label">Last Accessed</span>
            <span class="stat-value">${formatDate(stats.last_accessed_at)}</span>
        </div>
        ` : ''}
        ${stats.expires_at ? `
        <div class="stat-row">
            <span class="stat-label">Expires</span>
            <span class="stat-value">${formatDate(stats.expires_at)}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Status</span>
            <span class="stat-value">${stats.is_expired ? 'Expired' : 'Active'}</span>
        </div>
        ` : ''}
    `;

    statsModal.classList.remove('hidden');
}

// Hide stats modal
function hideStatsModal() {
    statsModal.classList.add('hidden');
}

// Copy URL (global function for onclick)
window.copyUrl = async function(url) {
    try {
        await navigator.clipboard.writeText(url);
        showTemporaryMessage('Copied to clipboard!');
    } catch (error) {
        showError('Failed to copy to clipboard');
    }
};

// Show temporary message
function showTemporaryMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        z-index: 1001;
        font-weight: 600;
    `;
    messageDiv.textContent = message;

    document.body.appendChild(messageDiv);

    setTimeout(() => {
        messageDiv.remove();
    }, 2000);
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}
