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
            const response = await fetch('/api/status');
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
            const response = await fetch('/api/scrape-group', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, count })
            });

            const text = await response.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch (e) {
                console.error('Server response was not JSON:', text);
                throw new Error('Server timed out or returned an invalid response. Try a smaller number of posts (e.g., 3 or 5).');
            }

            if (!response.ok) {
                throw new Error(data.error || 'Scraping failed');
            }

            currentData = data;
            displayResults(data);
        } catch (error) {
            console.error('Scrape Error:', error);
            let userMsg = error.message;
            if (userMsg.includes('Unexpected end of JSON input')) {
                userMsg = 'Request timed out. Try analyzing fewer posts at a time.';
            }
            
            alert('Error: ' + userMsg);
            
            postsContainer.innerHTML = `
                <div class="glass" style="padding: 2rem; border-left: 4px solid #ff4b4b; margin-top: 2rem;">
                    <h3 style="color: #ff4b4b; margin-bottom: 1rem;">Analysis Failed</h3>
                    <p>${userMsg}</p>
                    <p style="font-size: 0.8rem; color: var(--text-dim); margin-top: 1rem;">
                        Note: Render.com has a 30-second limit. If you request too many posts, the server might cut the connection.
                    </p>
                </div>
            `;
            resultsSection.classList.remove('hidden');
        } finally {
            loadingDiv.classList.add('hidden');
        }
    });

    demoBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const mockData = {
            group_name: "Demo AI Enthusiasts Group",
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
        displayResults(mockData);
    });

    function displayResults(data) {
        const { posts, group_name } = data;
        resultsSection.classList.remove('hidden');
        
        // Add Group Header
        const headerHtml = `
            <div class="group-header glass" style="padding: 1.5rem; margin-bottom: 2rem; border-left: 4px solid var(--primary);">
                <div style="font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Source Group</div>
                <h2 style="font-size: 1.8rem; margin: 0;">${group_name || 'Facebook Group'}</h2>
            </div>
        `;

        if (!posts || !Array.isArray(posts) || posts.length === 0) {
            postsContainer.innerHTML = headerHtml + '<p class="status-badge">No posts found or results were invalid.</p>';
            return;
        }

        postsContainer.innerHTML = headerHtml;

        posts.forEach((post, pIndex) => {
            const postCard = document.createElement('div');
            postCard.className = 'post-card glass';
            postCard.style.animationDelay = `${pIndex * 0.1}s`;
            
            const commentsHtml = post.comments && post.comments.length > 0 
                ? post.comments.map(c => `
                    <div class="comment-item">
                        <div class="comment-author">${c.author}</div>
                        <div class="comment-text">${c.text}</div>
                    </div>
                `).join('')
                : '';

            postCard.innerHTML = `
                <div class="post-content">
                    <div class="comment-author" style="font-size: 1.1rem; margin-bottom: 1rem;">Post #${pIndex + 1}</div>
                    <p style="white-space: pre-wrap;">${post.text || 'No text content'}</p>
                </div>
                <div class="post-footer">
                    <div class="stats-row" style="display: flex; gap: 2rem;">
                        <span><strong style="color: var(--primary)">${post.likes || 0}</strong> Reactions</span>
                        <span><strong style="color: var(--accent)">${post.comments_count || 0}</strong> Comments</span>
                    </div>
                    <button class="btn-icon export-post" data-index="${pIndex}">
                        <i data-lucide="download"></i>
                    </button>
                </div>
                ${commentsHtml ? `
                <div class="comments-section">
                    <h3 style="font-size: 0.9rem; margin-bottom: 1rem; color: var(--text-dim)">Recent Comments</h3>
                    <div class="comments-list">
                        ${commentsHtml}
                    </div>
                </div>` : ''}
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
