// Global state
let currentJobs = [];
let currentFilter = 'all';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadJobs();
});

// Load statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        document.getElementById('total-jobs').textContent = data.total_active_jobs;
        document.getElementById('new-today').textContent = data.new_today;
        document.getElementById('high-salary').textContent = data.high_salary_jobs;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load jobs with filters
async function loadJobs() {
    showLoading();

    try {
        const search = document.getElementById('search-input').value;
        const company = document.getElementById('company-filter').value;
        const salaryMin = document.getElementById('salary-min').value;
        const salaryMax = document.getElementById('salary-max').value;

        let url = '/api/jobs?';
        const params = new URLSearchParams();

        if (search) params.append('search', search);
        if (company) params.append('company', company);
        if (salaryMin) params.append('salary_min', salaryMin);
        if (salaryMax) params.append('salary_max', salaryMax);

        const response = await fetch(url + params.toString());
        const data = await response.json();

        currentJobs = data.jobs;
        currentFilter = 'all';
        displayJobs(data.jobs, '全求人', data.total);
    } catch (error) {
        console.error('Error loading jobs:', error);
        showError('求人の読み込みに失敗しました');
    } finally {
        hideLoading();
    }
}

// Search jobs
function searchJobs() {
    loadJobs();
}

// Clear filters
function clearFilters() {
    document.getElementById('search-input').value = '';
    document.getElementById('company-filter').value = '';
    document.getElementById('salary-min').value = '';
    document.getElementById('salary-max').value = '';
    loadJobs();
}

// Load new jobs posted today
async function loadNewToday() {
    showLoading();

    try {
        const response = await fetch('/api/jobs/new-today');
        const data = await response.json();

        currentJobs = data.jobs;
        currentFilter = 'new';
        displayJobs(data.jobs, '今日の新着求人', data.total);
    } catch (error) {
        console.error('Error loading new jobs:', error);
        showError('新着求人の読み込みに失敗しました');
    } finally {
        hideLoading();
    }
}

// Load jobs closed yesterday
async function loadClosedYesterday() {
    showLoading();

    try {
        const response = await fetch('/api/jobs/closed-yesterday');
        const data = await response.json();

        currentJobs = data.jobs;
        currentFilter = 'closed';
        displayJobs(data.jobs, '昨日のクローズ求人', data.total);
    } catch (error) {
        console.error('Error loading closed jobs:', error);
        showError('クローズ求人の読み込みに失敗しました');
    } finally {
        hideLoading();
    }
}

// Load high salary jobs
async function loadHighSalary() {
    showLoading();

    try {
        const response = await fetch('/api/jobs/high-salary?min_salary=10000000');
        const data = await response.json();

        currentJobs = data.jobs;
        currentFilter = 'high-salary';
        displayJobs(data.jobs, '年収1000万円以上の求人', data.total);
    } catch (error) {
        console.error('Error loading high salary jobs:', error);
        showError('高年収求人の読み込みに失敗しました');
    } finally {
        hideLoading();
    }
}

// Trigger manual scrape
async function triggerScrape() {
    if (!confirm('求人情報を更新しますか？数分かかる場合があります。')) {
        return;
    }

    showLoading();

    try {
        const response = await fetch('/api/scrape', { method: 'POST' });
        const data = await response.json();

        alert(`更新完了!\n新規: ${data.new_jobs}件\n更新: ${data.updated_jobs}件\nクローズ: ${data.closed_jobs}件`);

        // Reload stats and jobs
        await loadStats();
        await loadJobs();
    } catch (error) {
        console.error('Error triggering scrape:', error);
        alert('求人情報の更新に失敗しました');
    } finally {
        hideLoading();
    }
}

// Display jobs
function displayJobs(jobs, title, count) {
    document.getElementById('results-title').textContent = title;
    document.getElementById('results-count').textContent = `${count}件`;

    const container = document.getElementById('jobs-container');

    if (jobs.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <h3>求人が見つかりませんでした</h3>
                <p>検索条件を変更してお試しください</p>
            </div>
        `;
        return;
    }

    container.innerHTML = jobs.map(job => createJobCard(job)).join('');
}

// Create job card HTML
function createJobCard(job) {
    const salary = formatSalary(job.salary_min, job.salary_max);
    const companyClass = job.company.toLowerCase().replace(/\s+/g, '-');
    const cardClass = currentFilter === 'new' ? 'job-card new' :
                      currentFilter === 'closed' ? 'job-card closed' : 'job-card';

    const firstSeen = job.first_seen ? new Date(job.first_seen).toLocaleDateString('ja-JP') : '-';
    const lastSeen = job.last_seen ? new Date(job.last_seen).toLocaleDateString('ja-JP') : '-';

    return `
        <div class="${cardClass}" onclick="window.open('${job.url}', '_blank')">
            <div class="job-header">
                <span class="company-badge company-${companyClass}">${job.company}</span>
            </div>
            <h3 class="job-title">${escapeHtml(job.title)}</h3>
            ${salary ? `<div class="job-salary">${salary}</div>` : ''}
            ${job.description ? `<p class="job-description">${escapeHtml(job.description)}</p>` : ''}
            <div class="job-meta">
                ${job.location ? `<span>📍 ${escapeHtml(job.location)}</span>` : ''}
                ${job.employment_type ? `<span>💼 ${escapeHtml(job.employment_type)}</span>` : ''}
            </div>
            <div class="job-meta">
                <span>初回取得: ${firstSeen}</span>
                <span>最終確認: ${lastSeen}</span>
            </div>
            <a href="${job.url}" target="_blank" class="job-link" onclick="event.stopPropagation()">
                詳細を見る →
            </a>
        </div>
    `;
}

// Format salary
function formatSalary(min, max) {
    if (!min && !max) return '';

    const formatAmount = (amount) => {
        if (amount >= 10000000) {
            return `${(amount / 10000000).toFixed(0)}千万円`;
        } else if (amount >= 10000) {
            return `${(amount / 10000).toFixed(0)}万円`;
        }
        return `${amount}円`;
    };

    if (min && max) {
        return `💰 ${formatAmount(min)} 〜 ${formatAmount(max)}`;
    } else if (min) {
        return `💰 ${formatAmount(min)}以上`;
    } else if (max) {
        return `💰 ${formatAmount(max)}まで`;
    }

    return '';
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show loading
function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

// Hide loading
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// Show error
function showError(message) {
    alert(message);
}

// Add enter key support for search
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchJobs();
        }
    });

    // Add change listeners to filters
    document.getElementById('company-filter').addEventListener('change', searchJobs);
    document.getElementById('salary-min').addEventListener('change', searchJobs);
    document.getElementById('salary-max').addEventListener('change', searchJobs);
});
