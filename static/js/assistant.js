/**
 * AI Business Twin — AI Assistant Chat Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('access_token');
  if (!token) { window.location.href = '/login'; return; }

  // Logout
  document.getElementById('logout-btn').addEventListener('click', () => {
    localStorage.removeItem('access_token');
    window.location.href = '/';
  });

  // Load business name
  fetch('/api/business', { headers: { 'Authorization': 'Bearer ' + token } })
    .then(r => {
      if (r.status === 404) { window.location.href = '/setup'; return null; }
      if (!r.ok) { localStorage.removeItem('access_token'); window.location.href = '/login'; return null; }
      return r.json();
    })
    .then(biz => { if (biz) document.getElementById('user-name').textContent = biz.business_name; })
    .catch(() => {});

  const messagesEl = document.getElementById('chat-messages');
  const inputEl = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  const history = [];

  // Simple markdown to HTML converter
  function md(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/^### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^## (.+)$/gm, '<h3>$1</h3>')
      .replace(/^# (.+)$/gm, '<h2>$1</h2>')
      .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/gs, (m) => '<ul>' + m + '</ul>')
      .replace(/<\/ul>\s*<ul>/g, '')
      .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
      .replace(/\n{2,}/g, '</p><p>')
      .replace(/\n/g, '<br>')
      .replace(/^/, '<p>').replace(/$/, '</p>')
      .replace(/<p><h/g, '<h').replace(/<\/h(\d)><\/p>/g, '</h$1>')
      .replace(/<p><ul>/g, '<ul>').replace(/<\/ul><\/p>/g, '</ul>')
      .replace(/<p><\/p>/g, '');
  }

  function addMessage(role, content) {
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    const avatar = role === 'user' ? '👤' : '✦';
    div.innerHTML = `
      <div class="chat-avatar">${avatar}</div>
      <div class="chat-bubble">${role === 'user' ? escapeHtml(content) : md(content)}</div>`;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function escapeHtml(t) {
    return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'chat-message assistant';
    div.id = 'typing-indicator';
    div.innerHTML = `
      <div class="chat-avatar">✦</div>
      <div class="chat-bubble">
        <div class="chat-typing"><span></span><span></span><span></span></div>
      </div>`;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeTyping() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
  }

  async function sendMessage(question) {
    if (!question.trim()) return;
    addMessage('user', question);
    history.push({ role: 'user', content: question });
    inputEl.value = '';
    sendBtn.disabled = true;
    showTyping();

    try {
      const resp = await fetch('/api/assistant', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({
          question: question,
          history: history.slice(-6)
        })
      });
      removeTyping();

      if (!resp.ok) {
        const err = await resp.json();
        addMessage('assistant', `Sorry, I encountered an error: ${err.detail || 'Please try again.'}`);
      } else {
        const data = await resp.json();
        addMessage('assistant', data.response);
        history.push({ role: 'assistant', content: data.response });

        if (!data.has_data) {
          addMessage('assistant', '💡 **Tip:** Upload your business data first to get data-backed answers. Go to **Upload** to add your CSV/Excel files.');
        }
      }
    } catch (e) {
      removeTyping();
      addMessage('assistant', 'Network error. Please check your connection and try again.');
    }
    sendBtn.disabled = false;
    inputEl.focus();
  }

  // Send button
  sendBtn.addEventListener('click', () => sendMessage(inputEl.value));

  // Enter key (shift+enter for newline)
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputEl.value);
    }
  });

  // Auto-resize textarea
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
  });

  // Suggestion chips
  document.getElementById('suggestions')?.addEventListener('click', (e) => {
    const chip = e.target.closest('.suggestion-chip');
    if (chip) sendMessage(chip.dataset.q);
  });
});
