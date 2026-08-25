document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('news-container');
    const tabs = document.querySelectorAll('.tab');
    const lastUpdateEl = document.getElementById('last-update');
    const refreshBtn = document.getElementById('refresh-btn');
    let newsData = null;
    let currentRange = 'latest';

    const loadData = async () => {
        container.innerHTML = '<div style="text-align:center; padding: 40px; color: #666;">加载中...</div>';
        try {
            // 添加时间戳防止缓存
            const res = await fetch(`data/news.json?t=${new Date().getTime()}`);
            if (!res.ok) throw new Error('Data not found');
            newsData = await res.json();
            
            const updateDate = new Date(newsData.updatedAt);
            lastUpdateEl.textContent = `最后更新: ${updateDate.toLocaleString('zh-CN')}`;
            renderNews(currentRange);
        } catch (err) {
            container.innerHTML = '<div style="text-align:center; padding: 40px; color: #ff4d4f;">加载失败或暂无数据，请检查 data/news.json 是否存在</div>';
        }
    };

    const renderNews = (range) => {
        if (!newsData || !newsData[range] || newsData[range].length === 0) {
            container.innerHTML = '<div style="text-align:center; padding: 40px; color: #666;">当前时段暂无资讯</div>';
            return;
        }

        const items = newsData[range];
        
        // 按 category 分组
        const grouped = items.reduce((acc, item) => {
            if (!acc[item.category]) acc[item.category] = [];
            acc[item.category].push(item);
            return acc;
        }, {});

        let html = '';
        for (const [category, list] of Object.entries(grouped)) {
            // 同板块内按重要性降序排序
            list.sort((a, b) => b.importance - a.importance);

            html += `
                <div class="category-section">
                    <div class="category-title">${category}</div>
                    <div class="news-grid">
                        ${list.map(item => `
                            <div class="news-card">
                                <div class="card-meta">
                                    <span class="tag">${item.category}</span>
                                    <span class="importance">重要性: ${item.importance}/5</span>
                                </div>
                                <h3 class="card-title">${item.title}</h3>
                                <div class="card-summary">${item.summary}</div>
                                <ul class="card-highlights">
                                    ${item.highlights.map(h => `<li>${h}</li>`).join('')}
                                </ul>
                                <div class="card-footer">
                                    <span>${item.source} · ${new Date(item.publishedAt).toLocaleDateString('zh-CN')}</span>
                                    <a href="${item.url}" target="_blank" class="card-link">阅读原文</a>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        container.innerHTML = html;
    };

    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            tabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            currentRange = e.target.dataset.range;
            if (newsData) renderNews(currentRange);
        });
    });

    refreshBtn.addEventListener('click', () => {
        loadData();
    });

    // 初始加载
    loadData();
});
