document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const elements = {
        newSessionBtn: document.getElementById('newSessionBtn'),
        sessionsList: document.getElementById('sessionsList'),
        messageInput: document.getElementById('messageInput'),
        sendBtn: document.getElementById('sendBtn'),
        messagesContainer: document.getElementById('messagesContainer'),
        initialGreeting: document.getElementById('initialGreeting'),
        productsScrollArea: document.getElementById('productsScrollArea'),
        emptyProducts: document.getElementById('emptyProducts'),
        productsGridLayout: document.getElementById('productsGridLayout'),
        featuredProductSlot: document.getElementById('featuredProductSlot'),
        gridProductsSlot: document.getElementById('gridProductsSlot'),
        productPanel: document.getElementById('productPanel'),
        toggleProductsBtn: document.getElementById('toggleProductsBtn'),
        closeProductPanel: document.getElementById('closeProductPanel')
    };

    // State
    let currentThreadId = null;
    let sessions = []; // [{thread_id, title}]
    let isTyping = false;
    let isNewSession = true;

    // Initialization
    async function init() {
        setupEventListeners();
        await loadPastSessionsFromPostgres();
        if (sessions.length > 0) {
            await switchSession(sessions[0].thread_id);
        } else {
            await createNewSession();
        }
    }

    function setupEventListeners() {
        elements.newSessionBtn.addEventListener('click', createNewSession);
        elements.sendBtn.addEventListener('click', handleSendMessage);
        
        elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });

        if (elements.toggleProductsBtn) {
            elements.toggleProductsBtn.addEventListener('click', () => {
                elements.productPanel.classList.add('open');
            });
        }

        if (elements.closeProductPanel) {
            elements.closeProductPanel.addEventListener('click', () => {
                elements.productPanel.classList.remove('open');
            });
        }
    }

    // Sessions Management from PostgreSQL
    async function loadPastSessionsFromPostgres() {
        try {
            const res = await fetch('/api/v1/threads');
            if (res.ok) {
                const data = await res.json();
                if (data.threads && data.threads.length > 0) {
                    sessions = data.threads;
                    renderSessions();
                }
            }
        } catch (err) {
            console.error('Error fetching past sessions from Postgres:', err);
        }
    }

    async function createNewSession() {
        try {
            const res = await fetch('/api/v1/threads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();
            currentThreadId = data.thread_id;
        } catch (err) {
            console.error('Error creating thread:', err);
            currentThreadId = 'session_' + Math.random().toString(36).substring(2, 10);
        }

        const sessionObj = {
            thread_id: currentThreadId,
            title: `New Chat`
        };

        sessions.unshift(sessionObj);
        isNewSession = true;
        renderSessions();

        // Clear UI
        elements.messagesContainer.innerHTML = '';
        elements.messagesContainer.appendChild(elements.initialGreeting);
        elements.initialGreeting.style.display = 'flex';
        
        elements.emptyProducts.style.display = 'flex';
        elements.productsGridLayout.style.display = 'none';
        elements.featuredProductSlot.innerHTML = '';
        elements.gridProductsSlot.innerHTML = '';

        elements.messageInput.focus();
    }

    function renderSessions() {
        elements.sessionsList.innerHTML = '';
        sessions.forEach(s => {
            const item = document.createElement('div');
            item.className = `session-item ${s.thread_id === currentThreadId ? 'active' : ''}`;
            
            item.innerHTML = `
                <div class="session-item-icon"><i class="far fa-comment-dots"></i></div>
                <div class="session-item-text" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</div>
            `;
            item.addEventListener('click', () => switchSession(s.thread_id));
            elements.sessionsList.appendChild(item);
        });
    }

    async function switchSession(threadId) {
        if (currentThreadId === threadId && elements.messagesContainer.children.length > 1) return;
        currentThreadId = threadId;
        isNewSession = false;
        renderSessions();

        // Clear and load messages for this session
        elements.messagesContainer.innerHTML = '';
        elements.initialGreeting.style.display = 'none';

        try {
            const res = await fetch(`/api/v1/threads/${threadId}/messages`);
            if (res.ok) {
                const data = await res.json();
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        addMessage(msg.content, msg.role === 'human' || msg.role === 'user' ? 'user' : 'assistant');
                    });
                } else {
                    elements.messagesContainer.appendChild(elements.initialGreeting);
                    elements.initialGreeting.style.display = 'flex';
                }
            }
        } catch (err) {
            console.error('Error loading session messages:', err);
        }
    }

    // Messaging
    async function handleSendMessage() {
        const text = elements.messageInput.value.trim();
        if (!text || isTyping) return;

        elements.messageInput.value = '';

        // Update session title on first message
        if (isNewSession) {
            const activeSession = sessions.find(s => s.thread_id === currentThreadId);
            if (activeSession) {
                activeSession.title = text.length > 30 ? text.substring(0, 30) + '...' : text;
                renderSessions();
            }
            isNewSession = false;
        }

        // Hide greeting
        if (elements.initialGreeting.style.display !== 'none') {
            elements.initialGreeting.style.display = 'none';
        }

        // Add user message
        addMessage(text, 'user');

        // Show typing indicator
        showTypingIndicator();
        isTyping = true;

        // Call API
        try {
            const res = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    thread_id: currentThreadId,
                    message: text
                })
            });

            const data = await res.json();

            hideTypingIndicator();
            isTyping = false;

            if (data.response) {
                addMessage(data.response, 'assistant');
            }

            // Always update product panel (clears old products if empty)
            renderProducts(data.products || []);
            if (data.products && data.products.length > 0 && window.innerWidth <= 768) {
                elements.productPanel.classList.add('open');
            }
        } catch (err) {
            console.error('Chat error:', err);
            hideTypingIndicator();
            isTyping = false;
            addMessage('عذراً، حصل مشكلة في الاتصال بالخادم. حاول مرة أخرى.', 'assistant');
        }
    }

    function addMessage(content, role) {
        const row = document.createElement('div');
        row.className = `message-row ${role}`;
        const isArabic = containsArabic(content);

        const timeStr = getCurrentTime();
        const avatarIcon = role === 'user' ? '<i class="fas fa-user"></i>' : '<svg width="16" height="16" viewBox="0 0 60 40" fill="none"><polygon points="14,0 26,20 2,20" fill="#0055ff"/><polygon points="26,0 38,20 14,20" fill="#0033a0"/><polygon points="38,0 50,20 26,20" fill="#0055ff"/></svg>';
        const roleLabel = role === 'user' ? 'YOU' : 'RAYA ASSISTANT';

        row.innerHTML = `
            <div class="msg-avatar">${avatarIcon}</div>
            <div class="msg-body">
                <div class="msg-meta">${roleLabel} • ${timeStr}</div>
                <div class="msg-bubble" dir="${isArabic ? 'rtl' : 'ltr'}">${escapeHtml(content)}</div>
            </div>
        `;

        elements.messagesContainer.appendChild(row);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.id = 'typingIndicator';
        indicator.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        elements.messagesContainer.appendChild(indicator);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const ind = document.getElementById('typingIndicator');
        if (ind) ind.remove();
    }

    // Render Products
    function renderProducts(products) {
        elements.emptyProducts.style.display = 'none';
        elements.productsGridLayout.style.display = 'block';
        elements.featuredProductSlot.innerHTML = '';
        elements.gridProductsSlot.innerHTML = '';

        if (!products || products.length === 0) return;

        // 1. Featured Product (Top / Best Match)
        const topProduct = products[0];
        const topPrice = Number(topProduct.price).toLocaleString('en-EG');
        const fallbackImg = 'https://api-rayashop.freetls.fastly.net/media/catalog/product/placeholder/default/raya_placeholder.png';

        const featuredCard = document.createElement('a');
        featuredCard.className = 'featured-card';
        featuredCard.href = topProduct.url || '#';
        featuredCard.target = '_blank';
        featuredCard.rel = 'noopener noreferrer';

        featuredCard.innerHTML = `
            <div class="best-match-badge">BEST MATCH</div>
            <div class="featured-image-wrapper">
                <img src="${topProduct.thumbnail || fallbackImg}" alt="${escapeHtml(topProduct.name)}" onerror="this.onerror=null; this.src='${fallbackImg}';">
            </div>
            <div class="featured-info">
                <div class="brand-tag">${escapeHtml(topProduct.brand || 'RAYASHOP')}</div>
                <div class="featured-title-price">
                    <div class="featured-title">${escapeHtml(topProduct.name)}</div>
                    <div class="featured-price">${topPrice} <span class="currency">EGP</span></div>
                </div>
                <div class="link-arrow"><i class="fas fa-arrow-up-right-from-square"></i></div>
            </div>
        `;

        elements.featuredProductSlot.appendChild(featuredCard);

        // 2. Remaining Products (2-Column Grid)
        const gridProducts = products.slice(1, 5);
        gridProducts.forEach(p => {
            const price = Number(p.price).toLocaleString('en-EG');
            const card = document.createElement('a');
            card.className = 'grid-card';
            card.href = p.url || '#';
            card.target = '_blank';
            card.rel = 'noopener noreferrer';

            card.innerHTML = `
                <div class="grid-image-wrapper">
                    <img src="${p.thumbnail || fallbackImg}" alt="${escapeHtml(p.name)}" onerror="this.onerror=null; this.src='${fallbackImg}';">
                </div>
                <div class="grid-info">
                    <div class="brand-tag">${escapeHtml(p.brand || 'RAYASHOP')}</div>
                    <div class="grid-title">${escapeHtml(p.name)}</div>
                    <div class="grid-bottom">
                        <div class="grid-price">${price} <span class="currency">EGP</span></div>
                        <div class="link-arrow"><i class="fas fa-arrow-up-right-from-square"></i></div>
                    </div>
                </div>
            `;

            elements.gridProductsSlot.appendChild(card);
        });
    }

    // Helpers
    function scrollToBottom() {
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
    }

    function containsArabic(text) {
        return /[\u0600-\u06FF]/.test(text);
    }

    function getCurrentTime() {
        const now = new Date();
        let hours = now.getHours();
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        return `${hours.toString().padStart(2, '0')}:${minutes}${ampm}`;
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Start
    init();
});
