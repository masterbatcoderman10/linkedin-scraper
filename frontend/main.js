const API_BASE = '';

const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const urlInput = document.getElementById('urlInput');
const scrapeBtn = document.getElementById('scrapeBtn');
const loadSessionBtn = document.getElementById('loadSessionBtn');
const sessionFile = document.getElementById('sessionFile');
const output = document.getElementById('output');

async function checkSession() {
    try {
        const res = await fetch(`${API_BASE}/api/session/status`);
        const data = await res.json();
        if (data.has_session) {
            statusDot.className = 'status-dot green';
            statusText.textContent = `Session: ${data.source}`;
        } else {
            statusDot.className = 'status-dot red';
            statusText.textContent = 'No session';
        }
    } catch (e) {
        statusDot.className = 'status-dot red';
        statusText.textContent = 'API unavailable';
    }
}

async function scrape() {
    const text = urlInput.value.trim();
    if (!text) {
        output.textContent = 'Error: No URLs provided';
        return;
    }

    const urls = text.split('\n').map(u => u.trim()).filter(u => u);
    const isMulti = urls.length > 1;

    const body = isMulti
        ? { urls, parallel: 3 }
        : { url: urls[0], parallel: 1 };

    scrapeBtn.disabled = true;
    output.textContent = 'Scraping...\n';

    try {
        const res = await fetch(`${API_BASE}/api/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        const data = await res.json();
        let resultText = '';

        for (const r of data.results) {
            if (r.status === 'ok') {
                resultText += `[OK] ${r.url}\n`;
                resultText += `---\n${r.markdown || ''}\n\n`;
            } else {
                resultText += `[ERROR] ${r.url}\n${r.error || 'Unknown error'}\n\n`;
            }
        }

        output.textContent = resultText || 'No results';
    } catch (e) {
        output.textContent = `Error: ${e.message}`;
    } finally {
        scrapeBtn.disabled = false;
    }
}

async function loadSession() {
    sessionFile.click();
}

sessionFile.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    loadSessionBtn.disabled = true;
    loadSessionBtn.textContent = 'Loading...';

    try {
        const res = await fetch(`${API_BASE}/api/session/load`, {
            method: 'POST',
            body: formData,
        });

        const data = await res.json();
        if (res.ok) {
            output.textContent = `Session loaded: ${data.message}`;
            await checkSession();
        } else {
            output.textContent = `Error: ${data.detail || 'Failed to load session'}`;
        }
    } catch (e) {
        output.textContent = `Error: ${e.message}`;
    } finally {
        loadSessionBtn.disabled = false;
        loadSessionBtn.textContent = 'Load Session';
        sessionFile.value = '';
    }
});

scrapeBtn.addEventListener('click', scrape);

checkSession();
