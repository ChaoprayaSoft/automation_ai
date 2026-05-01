document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    lucide.createIcons();

    const scrapeBtn = document.getElementById('scrape-btn');
    const groupUrlInput = document.getElementById('group-url');
    const postCountInput = document.getElementById('post-count');
    const loadingDiv = document.getElementById('loading');
    const resultsSection = document.getElementById('results');
    const postsContainer = document.getElementById('posts-container');
    const serverStatus = document.getElementById('server-status');
    const exportJsonBtn = document.getElementById('export-json-btn');
    const demoBtn = document.getElementById('demo-btn');

    let currentData = null;

    // Check server status
    async function checkStatus() {
        try {
            const response = await fetch('http://localhost:5000/api/status');
            if (response.ok) {
                serverStatus.classList.add('status-online');
                serverStatus.innerHTML = '<span class="dot"></span> Backend Online';
            }
        } catch (e) {
            console.warn('Backend not reachable yet');
        }
    }
    checkStatus();

    scrapeBtn.addEventListener('click', async () => {
        const url = groupUrlInput.value.trim();
        const count = parseInt(postCountInput.value) || 3;

        if (!url) {
            alert('Please enter a valid Facebook Group URL');
            return;
        }

        // Reset UI
        loadingDiv.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        postsContainer.innerHTML = '';
        
        try {
            const response = await fetch('http://localhost:5000/api/scrape-group', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, count })
            });

            if (!response.ok) throw new Error('Scraping failed');

            const data = await response.json();
            currentData = data;
            displayResults(data.posts);
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            loadingDiv.classList.add('hidden');
        }
    });

    demoBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const mockData = {
            posts: [
                {
                    text: "Exploring the future of AI in 2026. What are your thoughts on agentic systems?",
                    likes: "1.2k",
                    comments_count: "45",
                    comments: [
                        { author: "Alex Chen", text: "Truly revolutionary! Can't wait to see more." },
                        { author: "Sarah Jenkins", text: "How does this impact privacy?" }
                    ]
                },
                {
                    text: "Check out this amazing new tool for developers. It automates almost everything!",
                    likes: "850",
                    comments_count: "12",
                    comments: [
                        { author: "Mike Ross", text: "Is there a GitHub repo for this?" }
                    ]
                }
            ]
        };
        currentData = mockData;
        displayResults(mockData.posts);
    });

    function displayResults(posts) {
        resultsSection.classList.remove('hidden');
        
        if (!posts || posts.length === 0) {
            postsContainer.innerHTML = '<p class="status-badge">No posts found in this group.</p>';
            return;
        }

        posts.forEach((post, pIndex) => {
            const postCard = document.createElement('div');
            postCard.className = 'post-card glass';
            postCard.style.animationDelay = `${pIndex * 0.1}s`;
            
            const commentsHtml = post.comments.map(c => `
                <div class="comment-item">
                    <div class="comment-author">${c.author}</div>
                    <div class="comment-text">${c.text}</div>
                </div>
            `).join('');

            postCard.innerHTML = `
                <div class="post-content">
                    <div class="comment-author" style="font-size: 1.1rem; margin-bottom: 1rem;">Post #${pIndex + 1}</div>
                    <p>${post.text || 'No text content'}</p>
                </div>
                <div class="post-footer">
                    <div class="stats-row" style="display: flex; gap: 2rem;">
                        <span><strong>${post.likes || 0}</strong> Reactions</span>
                        <span><strong>${post.comments_count || 0}</strong> Comments</span>
                    </div>
                    <button class="btn-icon export-post" data-index="${pIndex}">
                        <i data-lucide="download"></i>
                    </button>
                </div>
                <div class="comments-section">
                    <h3 style="font-size: 0.9rem; margin-bottom: 1rem; color: var(--text-dim)">Recent Comments</h3>
                    <div class="comments-list">
                        ${commentsHtml || '<p class="comment-meta">No comments extracted for this post.</p>'}
                    </div>
                </div>
            `;
            postsContainer.appendChild(postCard);
        });

        // Re-initialize icons
        lucide.createIcons();

        // Add individual export listeners
        document.querySelectorAll('.export-post').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = e.currentTarget.dataset.index;
                exportPostToCSV(posts[index]);
            });
        });
    }

    exportJsonBtn.addEventListener('click', () => {
        if (!currentData) return;
        const dataStr = JSON.stringify(currentData, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `fb_group_data_${Date.now()}.json`;
        a.click();
    });

    function exportPostToCSV(post) {
        const csvRows = [
            ['Post Text', post.text.replace(/\n/g, ' ')],
            ['Likes', post.likes],
            ['Comments Count', post.comments_count],
            [],
            ['Comment Author', 'Comment Text'],
            ...post.comments.map(c => [c.author, c.text.replace(/\n/g, ' ')])
        ];

        const csvContent = csvRows.map(row => row.join(',')).join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `fb_group_post_${Date.now()}.csv`;
        a.click();
    }
});
