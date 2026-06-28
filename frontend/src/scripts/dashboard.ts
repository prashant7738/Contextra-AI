// @ts-nocheck
/**
 * Dashboard runtime — bootstraps chat list, messages, composer, document upload,
 * detailed summary panel, and flashcards. Loaded once per dashboard page render.
 *
 * Behavior preserved verbatim from the previous inline <script>, with these
 * surgical swaps:
 *   - CDN marked + DOMPurify  →  bundled renderMarkdown (utils/markdown.ts)
 *   - raw fetch(`${API_BASE}/...`)  →  apiFetch('/...')  (utils/api.ts)
 *
 * Auth redirect (missing access_token) is already enforced by BaseLayout's
 * requireAuth pre-paint script; the user-presence check here is a defense
 * in depth for malformed localStorage.
 */
import { apiFetch } from '../utils/api';
import { renderMarkdown } from '../utils/markdown';

(function bootDashboard() {
  let user: any = null;
  try {
    const userJson = localStorage.getItem('current_user');
    if (userJson) user = JSON.parse(userJson);
  } catch {
    /* malformed user — fall through to redirect */
  }
  if (!user) {
    window.location.replace('/login');
    return;
  }

  const chatList = document.getElementById('chat-list');
  const chatForm = document.getElementById('chat-form');
  const chatNameInput = document.getElementById('chat-name') as HTMLInputElement | null;
  const refreshBtn = document.getElementById('refresh-chats');
  const chatTitle = document.getElementById('chat-title');
  const identityPill = document.getElementById('identity-pill');
  const profileName = document.getElementById('profile-name');
  const profileAvatar = document.getElementById('profile-avatar');
  const logoutBtn = document.getElementById('logout-btn');
  const summarizerBtn = document.getElementById('summarizer-btn');
  const flashcardBtn = document.getElementById('flashcard-btn');
  const navChatBtn = document.getElementById('nav-chat-btn');
  const profileMenuToggle = document.getElementById('profile-menu-toggle');
  const profileDropdown = document.getElementById('profile-dropdown');
  const topbar = document.getElementById('topbar');
  let currentView = 'chat';
  const summaryChatPill = document.getElementById('summary-chat-pill');
  const flashcardChatPill = document.getElementById('flashcard-chat-pill');
  const messageStream = document.getElementById('message-stream');
  const composer = document.getElementById('composer');
  const queryInput = document.getElementById('query-input') as HTMLTextAreaElement | null;
  const sendBtn = document.getElementById('send-btn') as HTMLButtonElement | null;
  const toggleUpload = document.getElementById('toggle-upload');
  const composerUpload = document.getElementById('composer-upload');
  const fileInput = document.getElementById('file-input') as HTMLInputElement | null;
  const uploadBtn = document.getElementById('upload-btn') as HTMLButtonElement | null;
  const dropzoneLabel = document.getElementById('dropzone-label');
  const statusLine = document.getElementById('status-line');
  const connectionPill = document.getElementById('connection-pill');

  const summaryForm = document.getElementById('summary-form');
  const summaryTopic = document.getElementById('summary-topic') as HTMLInputElement | null;
  const summaryResults = document.getElementById('summary-results') as HTMLInputElement | null;
  const summaryOutput = document.getElementById('summary-output');
  const summaryClearBtn = document.getElementById('summary-clear');

  const flashcardGenerateBtn = document.getElementById('flashcard-generate') as HTMLButtonElement | null;
  const flashcardClearBtn = document.getElementById('flashcard-clear');
  const flashcardResults = document.getElementById('flashcard-results') as HTMLInputElement | null;
  const flashcardOutput = document.getElementById('flashcard-output');
  const flashcardStatus = document.getElementById('flashcard-status');
  const flashcardTopicCount = document.getElementById('flashcard-topic-count');
  const flashcardCount = document.getElementById('flashcard-count');
  const flashcardChunkCount = document.getElementById('flashcard-chunk-count');

  const frameRails = document.getElementById('frame-rails');
  const leftResize = document.getElementById('left-resize');
  const mobileCaretBtn = document.getElementById('mobile-caret');
  const mobileProfileMenu = document.getElementById('mobile-profile-menu');
  const mobileSummBtn = document.getElementById('mobile-summarizer');
  const mobileFlashBtn = document.getElementById('mobile-flashcard');
  const mobileLogoutBtn = document.getElementById('mobile-logout');

  if (identityPill) identityPill.textContent = user.name;
  if (profileName) profileName.textContent = user.name || 'User';
  if (profileAvatar) {
    const initials = (user.name || 'User')
      .split(' ')
      .map((part: string) => part[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
    profileAvatar.textContent = initials || 'U';
  }

  let selectedChatId: number | null = null;
  let selectedUploadFile: File | null = null;
  const flashcardExpanded = new Set<number>();

  function setConnection(text: string, tone?: string) {
    if (!connectionPill) return;
    connectionPill.textContent = text;
    if (tone) connectionPill.dataset.tone = tone;
    else delete connectionPill.dataset.tone;
  }

  function setStatus(msg: string, tone?: string) {
    if (!statusLine) return;
    statusLine.textContent = msg;
    if (tone) statusLine.dataset.tone = tone;
    else delete statusLine.dataset.tone;
  }

  async function readError(resp: Response): Promise<string> {
    try {
      const j = await resp.json();
      return j.detail || JSON.stringify(j);
    } catch {
      return resp.statusText;
    }
  }

  async function loadChats() {
    try {
      const resp = await apiFetch(`/chats/?user_id=${user.id}`);
      if (!resp.ok) {
        throw new Error(`${resp.status}: ${await readError(resp)}`);
      }
      const chats = await resp.json();
      renderChats(chats);

      const hasSelectedChat = chats.some((chat: any) => chat.local_id === selectedChatId);
      if (!hasSelectedChat) {
        selectedChatId = null;
        if (chats.length > 0) {
          const firstChat = chats[0];
          await selectChat(firstChat.id, firstChat.local_id, firstChat.name, firstChat.created_at || '');
        } else {
          if (chatTitle) chatTitle.textContent = 'Select a chat';
          if (composer) composer.hidden = true;
          if (summaryChatPill) summaryChatPill.textContent = 'No chat selected';
          if (flashcardChatPill) flashcardChatPill.textContent = 'No chat selected';
          try { updateTopbarButtons(); } catch {}
        }
      }

      setConnection('Connected', 'success');
    } catch (err) {
      console.error('Load chats error:', err);
      if (!document.getElementById('chat-list')?.children.length) setConnection('Offline', 'danger');
    }
  }

  function renderChats(chats: any[]) {
    if (!chatList) return;
    if (!chats || chats.length === 0) {
      chatList.innerHTML = '<p class="empty">No chats yet. Create one above.</p>';
      return;
    }

    chats.sort((a: any, b: any) => {
      const da = a.created_at ? new Date(a.created_at).getTime() : 0;
      const db = b.created_at ? new Date(b.created_at).getTime() : 0;
      return db - da;
    });

    const html = chats
      .map((chat: any) => {
        const active = chat.local_id === selectedChatId ? ' chat-item-active' : '';
        const created = chat.created_at ? formatDate(chat.created_at) : '';
        return `<div class="chat-item${active}" data-chat-id="${chat.id}" data-local-id="${chat.local_id}" data-created-at="${chat.created_at || ''}">
          <button class="chat-select" type="button">
            <span>${chat.name}</span>
            <small>${created}</small>
          </button>
          <button class="chat-menu" type="button" title="Chat actions">⋯</button>
        </div>`;
      })
      .join('');

    chatList.innerHTML = html;
    const overlayList = document.getElementById('overlay-chat-list');
    if (overlayList) overlayList.innerHTML = html;

    const lists = [chatList, overlayList].filter(Boolean) as HTMLElement[];
    lists.forEach((list) => {
      list.querySelectorAll('.chat-select').forEach((btn) => {
        btn.addEventListener('click', (ev: any) => {
          const wrapper = ev.currentTarget.closest('.chat-item');
          if (!wrapper) return;
          const chatId = Number(wrapper.dataset.chatId);
          const localId = Number(wrapper.dataset.localId);
          const createdAt = wrapper.dataset.createdAt || '';
          const chatName = wrapper.querySelector('span')?.textContent || 'Chat';
          selectChat(chatId, localId, chatName, createdAt);
          if (list === overlayList) {
            const mo = document.getElementById('mobile-overlay');
            const mh = document.getElementById('mobile-hamburger');
            if (mo) { mo.hidden = true; mo.classList.remove('open'); }
            if (mh) mh.setAttribute('aria-expanded', 'false');
            if (messageStream) messageStream.style.display = '';
          }
        });
      });

      list.querySelectorAll('.chat-menu').forEach((btn) => {
        btn.addEventListener('click', (ev: any) => {
          ev.stopPropagation();
          closeAllChatMenus();
          const wrapper = ev.currentTarget.closest('.chat-item');
          if (!wrapper) return;
          const localId = Number(wrapper.dataset.localId);
          const chatName = wrapper.querySelector('span')?.textContent || 'this chat';

          const menu = document.createElement('div');
          menu.className = 'chat-actions-menu';

          const renameBtn = document.createElement('button');
          renameBtn.type = 'button';
          renameBtn.textContent = 'Rename';
          renameBtn.addEventListener('click', async (e: any) => {
            e.stopPropagation();
            closeAllChatMenus();
            const newName = await openModal({
              title: 'Rename chat',
              message: 'Enter a new name for this chat:',
              showInput: true,
              inputValue: chatName,
              confirmText: 'Save',
              confirmClass: 'button button-primary',
            });
            if (!newName) return;
            try {
              const resp = await apiFetch(`/chats/${localId}?user_id=${user.id}`, {
                method: 'PATCH',
                body: JSON.stringify({ name: newName }),
              });
              if (!resp.ok) throw new Error(`${resp.status}: ${await readError(resp)}`);
              setStatus('Chat renamed', 'success');
              await loadChats();
            } catch (err: any) {
              console.error('Rename chat error:', err);
              setStatus('Unable to rename chat: ' + (err?.message || err), 'danger');
            }
          });

          const deleteBtn = document.createElement('button');
          deleteBtn.type = 'button';
          deleteBtn.textContent = 'Delete';
          deleteBtn.style.color = 'var(--danger)';
          deleteBtn.addEventListener('click', async (e: any) => {
            e.stopPropagation();
            closeAllChatMenus();
            const ok = await openModal({
              title: 'Delete chat',
              message: `Delete '${chatName}' permanently? This cannot be undone.`,
              showInput: false,
              confirmText: 'Delete',
              confirmClass: 'btn-danger',
            });
            if (!ok) return;
            try {
              setStatus('Deleting chat...', 'warning');
              const resp = await apiFetch(`/chats/${localId}?user_id=${user.id}`, { method: 'DELETE' });
              if (!resp.ok) throw new Error(`${resp.status}: ${await readError(resp)}`);

              if (selectedChatId === localId) {
                selectedChatId = null;
                if (composer) composer.hidden = true;
                if (messageStream) messageStream.innerHTML = `<div class="empty-state"><h3>Select a chat</h3><p>Choose a chat from the left sidebar or create a new one to start asking questions about your notes.</p></div>`;
                if (chatTitle) chatTitle.textContent = 'Select a chat';
                if (summaryChatPill) summaryChatPill.textContent = 'No chat selected';
                if (flashcardChatPill) flashcardChatPill.textContent = 'No chat selected';
                try { updateTopbarButtons(); } catch {}
              }

              await loadChats();
              setStatus('Chat deleted', 'success');
            } catch (err: any) {
              console.error('Delete chat error:', err);
              setStatus('Unable to delete chat: ' + (err?.message || err), 'danger');
            }
          });

          menu.appendChild(renameBtn);
          menu.appendChild(deleteBtn);

          wrapper.appendChild(menu);
          setTimeout(() => {
            window.addEventListener('click', closeAllChatMenus, { once: true });
          }, 0);
        });
      });
    });

    function closeAllChatMenus() {
      document.querySelectorAll('.chat-actions-menu').forEach((m) => m.remove());
    }
  }

  async function selectChat(chatId: number, localId: number, chatName: string, _createdAt: string) {
    selectedChatId = localId;
    if (chatTitle) chatTitle.textContent = chatName;
    if (summaryChatPill) summaryChatPill.textContent = chatName;
    if (flashcardChatPill) flashcardChatPill.textContent = chatName;
    chatList?.querySelectorAll('.chat-item').forEach((c) => c.classList.remove('chat-item-active'));
    const activeBtn = chatList?.querySelector(`[data-local-id="${localId}"]`);
    if (activeBtn) activeBtn.classList.add('chat-item-active');
    if (composer) composer.hidden = false;
    try { updateTopbarButtons(); } catch {}
    if (topbar) {
      topbar.classList.add('fixed');
      document.body.classList.add('has-fixed-topbar');
    }
    setStatus('');
    resetSummary();
    clearFlashcards();
    await loadMessages(localId);

    try { await renderChatDocuments(localId); } catch (e) { console.debug('Refresh docs on select failed', e); }

    try {
      if (composer) composer.scrollIntoView({ behavior: 'smooth', block: 'end' });
      if (queryInput) queryInput.focus();
    } catch {
      /* ignore */
    }
  }

  const isMobile = () => window.matchMedia && window.matchMedia('(max-width:720px)').matches;

  document.addEventListener('click', (ev: any) => {
    if (!isMobile()) return;
    const target = ev.target;
    if (mobileProfileMenu && !mobileProfileMenu.hidden && !document.getElementById('profile-pill')?.contains(target)) {
      mobileProfileMenu.hidden = true;
      document.getElementById('profile-pill')?.classList.remove('open');
      mobileCaretBtn?.setAttribute('aria-expanded', 'false');
    }
  });

  if (mobileCaretBtn) {
    mobileCaretBtn.addEventListener('click', (e: any) => {
      e.stopPropagation();
      if (!isMobile()) return;
      const pill = document.getElementById('profile-pill');
      if (!pill) return;
      const open = pill.classList.toggle('open');
      mobileCaretBtn.setAttribute('aria-expanded', String(open));
      if (mobileProfileMenu) mobileProfileMenu.hidden = !open;
    });
  }

  const mobileHamburger = document.getElementById('mobile-hamburger');
  const mobileOverlay = document.getElementById('mobile-overlay');
  const mobileHamburgerClose = document.getElementById('mobile-hamburger-close');
  const overlaySummBtn = document.getElementById('overlay-summarizer');
  const overlayFlashBtn = document.getElementById('overlay-flashcard');
  const overlayLogoutBtn = document.getElementById('overlay-logout');

  function closeMobileOverlay() {
    if (!mobileOverlay) return;
    mobileOverlay.hidden = true;
    mobileOverlay.classList.remove('open');
    if (mobileHamburger) mobileHamburger.setAttribute('aria-expanded', 'false');
    if (messageStream) messageStream.style.display = '';
  }

  if (mobileHamburger && mobileOverlay) {
    closeMobileOverlay();

    mobileHamburger.addEventListener('click', (ev: any) => {
      ev.stopPropagation();
      if (!isMobile()) return;
      const open = !mobileOverlay.classList.contains('open');
      mobileOverlay.classList.toggle('open', open);
      mobileOverlay.hidden = !open;
      mobileHamburger.setAttribute('aria-expanded', String(open));
    });

    mobileHamburgerClose?.addEventListener('click', (e: any) => { e.stopPropagation(); closeMobileOverlay(); });

    document.addEventListener('click', (ev: any) => {
      if (!isMobile()) return;
      if (!mobileOverlay || mobileOverlay.hidden) return;
      const target = ev.target;
      if (!mobileOverlay.contains(target) && !mobileHamburger.contains(target)) closeMobileOverlay();
    });

    document.addEventListener('keydown', (ev: KeyboardEvent) => { if (ev.key === 'Escape') closeMobileOverlay(); });
  }

  overlaySummBtn?.addEventListener('click', () => { (summarizerBtn as HTMLElement | null)?.click(); closeMobileOverlay(); });
  overlayFlashBtn?.addEventListener('click', () => { (flashcardBtn as HTMLElement | null)?.click(); closeMobileOverlay(); });
  overlayLogoutBtn?.addEventListener('click', () => { (logoutBtn as HTMLElement | null)?.click(); });

  if (mobileSummBtn) {
    mobileSummBtn.addEventListener('click', () => {
      const btn = document.getElementById('summarizer-btn') as HTMLElement | null;
      btn?.click();
      if (mobileProfileMenu) mobileProfileMenu.hidden = true;
      document.getElementById('profile-pill')?.classList.remove('open');
      mobileCaretBtn?.setAttribute('aria-expanded', 'false');
    });
  }
  if (mobileFlashBtn) {
    mobileFlashBtn.addEventListener('click', () => {
      const btn = document.getElementById('flashcard-btn') as HTMLElement | null;
      btn?.click();
      if (mobileProfileMenu) mobileProfileMenu.hidden = true;
      document.getElementById('profile-pill')?.classList.remove('open');
      mobileCaretBtn?.setAttribute('aria-expanded', 'false');
    });
  }
  if (mobileLogoutBtn) {
    mobileLogoutBtn.addEventListener('click', () => {
      const btn = document.getElementById('logout-btn') as HTMLElement | null;
      btn?.click();
    });
  }

  async function loadMessages(chatId: number) {
    if (!messageStream) return;
    try {
      const resp = await apiFetch(`/chats/${chatId}/messages?user_id=${user.id}&limit=50`);
      if (!resp.ok) throw new Error(`${resp.status}: ${await readError(resp)}`);
      const messages = await resp.json();
      await renderMessages(messages, chatId);
    } catch (err: any) {
      console.error('Load messages error:', err);
      if (messageStream) messageStream.innerHTML = `<div class="empty-state"><h3>Error</h3><p>Failed to load messages: ${escapeHtml(err.message)}</p></div>`;
    }
  }

  async function renderMessages(messages: any[], chatId: number) {
    if (!messageStream) return;
    if (!messages || messages.length === 0) {
      messageStream.innerHTML = `<div class="empty-state"><h3>Start a conversation</h3><p>Ask a question about your notes to get started.</p></div>`;
      return;
    }
    messageStream.innerHTML = messages
      .map(
        (msg: any) => `
        <article class="turn">
          <div class="turn-meta">${formatDate(msg.created_at)}</div>
          <div class="turn-card">
            <div class="bubble bubble-user">
              <p class="bubble-label">You</p>
              <p>${escapeHtml(msg.user_message)}</p>
            </div>
            <div class="bubble bubble-bot">
              <p class="bubble-label">Assistant</p>
              <div class="bot-content">${renderMarkdown(msg.bot_response || '')}</div>
            </div>
          </div>
        </article>
      `,
      )
      .join('');
    messageStream.scrollTop = messageStream.scrollHeight;

    renderChatDocuments(chatId).catch((e) => console.debug('Could not render chat documents', e));
  }

  async function renderChatDocuments(chatId: number) {
    const listEl = document.getElementById('chat-doc-list-items');
    const container = document.getElementById('chat-doc-list');
    if (!listEl || !container) return;
    try {
      const docResp = await apiFetch(`/documents/?user_id=${user.id}&chat_id=${chatId}`);
      if (!docResp.ok) {
        listEl.innerHTML = '';
        container.style.display = 'none';
        return;
      }
      const docs = await docResp.json();
      if (!docs || docs.length === 0) {
        listEl.innerHTML = '';
        container.style.display = 'none';
        return;
      }
      listEl.innerHTML = docs.map((d: any) => `<li>${escapeHtml(d.filename)}</li>`).join('');
      container.style.display = '';
    } catch (err) {
      console.debug('Error fetching docs for chat', err);
      listEl.innerHTML = '';
      container.style.display = 'none';
    }
  }

  function formatDate(iso: string) {
    if (!iso) return 'Now';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return 'Now';
    return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function escapeHtml(text: string) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
  }

  async function sendQuery() {
    if (!queryInput || !selectedChatId) return;
    const request = queryInput.value.trim();
    if (!request) return;

    queryInput.value = '';
    setStatus('Thinking...', 'warning');
    if (sendBtn) sendBtn.disabled = true;

    if (messageStream) {
      const emptyState = messageStream.querySelector('.empty-state');
      if (emptyState) messageStream.innerHTML = '';
      messageStream.insertAdjacentHTML(
        'beforeend',
        `
          <div class="turn" id="pending-turn">
            <div class="bubble bubble-user">
              <p class="bubble-label">You</p>
              <p>${escapeHtml(request)}</p>
            </div>
            <div class="bubble bubble-bot">
              <p class="bubble-label">Assistant</p>
              <div class="bot-content"><p>Thinking...</p></div>
            </div>
          </div>
        `,
      );
      messageStream.scrollTop = messageStream.scrollHeight;
    }

    try {
      const resp = await apiFetch(`/chats/query?user_id=${user.id}`, {
        method: 'POST',
        body: JSON.stringify({ chat_id: selectedChatId, request }),
        timeoutMs: 120_000,
      });
      if (!resp.ok) throw new Error(`${resp.status}: ${await readError(resp)}`);
      const data = await resp.json();
      const pendingTurn = document.getElementById('pending-turn');
      if (pendingTurn) {
        const botBubble = pendingTurn.querySelector('.bubble-bot .bot-content');
        if (botBubble) {
          botBubble.innerHTML = renderMarkdown(data.answer || '');
        } else {
          console.warn('bot-content div not found, falling back to direct update');
        }
        pendingTurn.id = '';
      }
      if (queryInput) queryInput.value = '';
      setStatus('', 'success');
    } catch (err: any) {
      console.error('Query error:', err);
      const pendingTurn = document.getElementById('pending-turn');
      if (pendingTurn) {
        const botBubble = pendingTurn.querySelector('.bubble-bot .bot-content');
        if (botBubble) {
          botBubble.innerHTML = `<p style="color: #c33;">Error: ${escapeHtml(err.message)}</p>`;
        }
        pendingTurn.id = '';
      }
      setStatus('Query failed', 'danger');
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      if (messageStream) messageStream.scrollTop = messageStream.scrollHeight;
    }
  }

  async function uploadFile(file: File) {
    if (!file || !selectedChatId) return;
    const name = file.name || 'file';
    if (!name.toLowerCase().endsWith('.pdf')) {
      setStatus('Only PDF files are supported', 'danger');
      return;
    }
    setStatus(`Uploading ${file.name}...`, 'warning');
    if (uploadBtn) uploadBtn.disabled = true;
    try {
      const formData = new FormData();
      formData.append('files', file);
      const resp = await apiFetch(
        `/documents/ingest?user_id=${user.id}&chat_id=${selectedChatId}`,
        { method: 'POST', body: formData, timeoutMs: 120_000 },
      );
      if (!resp.ok) throw new Error(`${resp.status}: ${await readError(resp)}`);
      const results = await resp.json();
      const r = results[0];
      if (r.status === 'embedded and stored') {
        setStatus(`Uploaded ${file.name} — ${r.chunks_count} chunks indexed`, 'success');
      } else {
        setStatus(`Upload issue: ${r.status}`, 'warning');
      }
      if (fileInput) fileInput.value = '';
      selectedUploadFile = null;
      try { if (selectedChatId) await renderChatDocuments(selectedChatId); } catch (e) { console.debug('Refresh docs after upload failed', e); }
    } catch (err: any) {
      console.error('Upload error:', err);
      setStatus(`Upload failed: ${err.message}`, 'danger');
    } finally {
      if (uploadBtn) uploadBtn.disabled = false;
    }
  }

  async function generateSummary(ev: Event) {
    ev.preventDefault();
    if (!selectedChatId) {
      setStatus('Select a chat before generating summary', 'warning');
      return;
    }
    if (!summaryOutput) return;

    const topic = summaryTopic?.value?.trim() || 'all';
    const nResults = Number(summaryResults?.value || 5);
    const submitBtn = document.getElementById('summary-generate') as HTMLButtonElement | null;
    if (submitBtn) submitBtn.disabled = true;
    summaryOutput.innerHTML = '<p class="empty">Starting summary generation...</p>';

    try {
      const startResp = await apiFetch(`/chats/summary-task?user_id=${user.id}`, {
        method: 'POST',
        body: JSON.stringify({
          chat_id: selectedChatId,
          topic_name: topic,
          n_results: nResults,
          max_tokens: 900,
        }),
        timeoutMs: 30_000,
      });
      if (!startResp.ok) throw new Error(`${startResp.status}: ${await readError(startResp)}`);
      const { task_id } = await startResp.json();

      summaryOutput.innerHTML = '<p class="empty">⏳ Generating summary... <span class="poll-dots"></span></p>';

      let taskResp: any;
      while (true) {
        await new Promise((r) => setTimeout(r, 2000));
        const pollResp = await apiFetch(`/chats/summary-task/${task_id}`, { timeoutMs: 30_000 });
        if (!pollResp.ok) throw new Error(`${pollResp.status}: ${await readError(pollResp)}`);
        taskResp = await pollResp.json();

        if (taskResp.status === 'done') {
          renderSummary(taskResp.result);
          return;
        }
        if (taskResp.status === 'error') {
          throw new Error(taskResp.error || 'Summary generation failed');
        }
      }
    } catch (err: any) {
      console.error('Summary error:', err);
      summaryOutput.innerHTML = `<p class="empty">Unable to generate summary: ${escapeHtml(err.message)}</p>`;
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  function renderSummary(data: any) {
    if (!summaryOutput) return;

    const title = escapeHtml(data.title || data.topic || 'Summary');

    let bodyHtml = '';
    if (data.sections && data.sections.length > 0) {
      bodyHtml = data.sections
        .map(
          (section: any) => `
        <div class="summary-section">
          <h4 class="summary-section-heading">${escapeHtml(section.heading || 'Section')}</h4>
          <ul class="summary-section-list">
            ${(section.items || []).map((item: string) => `<li>${escapeHtml(item)}</li>`).join('')}
          </ul>
        </div>
      `,
        )
        .join('');
    } else if (data.summary) {
      bodyHtml = `<div class="summary-md-body">${renderMarkdown(data.summary)}</div>`;
    }

    const references = (data.references || [])
      .map(
        (ref: any) => `
      <li>${escapeHtml(ref.filename || 'Unknown source')} <small>p.${ref.page || '-'}</small></li>
    `,
      )
      .join('');

    summaryOutput.innerHTML = `
      <article class="summary-card">
        <div class="summary-card-head">
          <div class="summary-card-meta">
            <span class="pill">${escapeHtml(data.topic || 'all')}</span>
            <span class="pill">${Number(data.chunks_used || 0)} chunks</span>
          </div>
          <h3 class="summary-card-title">${title}</h3>
        </div>
        <div class="summary-card-body">
          ${bodyHtml}
        </div>
        ${references ? `<details class="summary-sources"><summary class="summary-sources-toggle">References</summary><ul>${references}</ul></details>` : ''}
      </article>
    `;
  }

  function resetSummary() {
    if (!summaryOutput) return;
    summaryOutput.innerHTML = '<p class="empty">Generate a focused summary for the selected chat.</p>';
  }

  function setFlashcardStatus(message: string, tone?: string) {
    if (!flashcardStatus) return;
    flashcardStatus.textContent = message;
    if (tone) flashcardStatus.dataset.tone = tone;
    else delete flashcardStatus.dataset.tone;
  }

  async function generateFlashcards() {
    if (!selectedChatId || !flashcardOutput) {
      setFlashcardStatus('Select a chat before generating flashcards', 'warning');
      return;
    }

    const nResults = Number(flashcardResults?.value || 5);
    if (flashcardChunkCount) flashcardChunkCount.textContent = String(nResults);
    if (flashcardGenerateBtn) flashcardGenerateBtn.disabled = true;
    flashcardOutput.innerHTML = '<p class="empty">Generating flashcards...</p>';
    setFlashcardStatus('Generating...', 'warning');

    try {
      const resp = await apiFetch(`/chats/flashcard?user_id=${user.id}&chat_id=${selectedChatId}`, {
        method: 'POST',
        body: JSON.stringify({ n_results: nResults, max_tokens: 1200 }),
        timeoutMs: 120_000,
      });

      if (!resp.ok) throw new Error(`${resp.status}: ${await readError(resp)}`);
      const data = await resp.json();
      renderFlashcards(data.flashcards || []);
      if (flashcardTopicCount) flashcardTopicCount.textContent = String(data.total_topics || 0);
      if (flashcardCount) flashcardCount.textContent = String(data.total_flashcards || 0);
      setFlashcardStatus('Flashcards generated', 'success');
    } catch (err: any) {
      console.error('Flashcard error:', err);
      flashcardOutput.innerHTML = `<p class="empty">Unable to generate flashcards: ${escapeHtml(err.message)}</p>`;
      setFlashcardStatus('Generation failed', 'danger');
    } finally {
      if (flashcardGenerateBtn) flashcardGenerateBtn.disabled = false;
    }
  }

  function renderFlashcards(cards: any[]) {
    if (!flashcardOutput) return;
    flashcardExpanded.clear();

    if (!cards.length) {
      flashcardOutput.innerHTML = '<p class="empty">No flashcards returned for this chat.</p>';
      return;
    }

    flashcardOutput.innerHTML = `
      <div class="flashcard-grid">
        ${cards
          .map((card: any, index: number) => {
            const refs = (card.references || [])
              .map(
                (ref: any) => `
              <li>${escapeHtml(ref.filename || 'Source')} <small>p.${ref.page || '-'}</small></li>
            `,
              )
              .join('');

            return `
              <article class="flashcard-card" data-card-index="${index}">
                <button class="flashcard-summary" type="button" data-toggle-index="${index}">
                  <div class="flashcard-topline">
                    <strong class="flashcard-topic">${escapeHtml(card.topic || 'Topic')}</strong>
                    <span class="flashcard-badge">Card ${index + 1}</span>
                  </div>
                  <p class="flashcard-summary-text">${escapeHtml(card.summary || '')}</p>
                  <span class="flashcard-hint">Expand</span>
                </button>
                <div class="flashcard-details">
                  <div class="flashcard-details-inner">
                    <p class="flashcard-explanation">${escapeHtml(card.explanation || 'No explanation')}</p>
                    ${refs ? `<details class="flashcard-sources"><summary class="flashcard-sources-toggle">References</summary><ul>${refs}</ul></details>` : ''}
                  </div>
                </div>
              </article>
            `;
          })
          .join('')}
      </div>
    `;

    flashcardOutput.querySelectorAll('[data-toggle-index]').forEach((btn: any) => {
      btn.addEventListener('click', () => {
        const index = Number(btn.dataset.toggleIndex);
        if (flashcardExpanded.has(index)) flashcardExpanded.delete(index);
        else flashcardExpanded.add(index);
        const card = flashcardOutput!.querySelector(`[data-card-index="${index}"]`);
        if (card) card.classList.toggle('flashcard-card-open', flashcardExpanded.has(index));
        const hint = btn.querySelector('.flashcard-hint');
        if (hint) hint.textContent = flashcardExpanded.has(index) ? 'Collapse' : 'Expand';
      });
    });
  }

  function clearFlashcards() {
    if (flashcardOutput) flashcardOutput.innerHTML = '<p class="empty">Generate flashcards to see learning cards here.</p>';
    if (flashcardTopicCount) flashcardTopicCount.textContent = '0';
    if (flashcardCount) flashcardCount.textContent = '0';
    setFlashcardStatus('');
  }

  function setSelectedUpload(file: File) {
    selectedUploadFile = file;
    if (!file) {
      setStatus('No file selected', 'warning');
      return;
    }
    setStatus(`Selected ${file.name}`, 'success');
  }

  function setupResizableRails() {
    if (!frameRails || !leftResize) return;

    const storedLeft = Number(localStorage.getItem('dashboard_left_width') || 320);
    frameRails.style.setProperty('--left-width', `${Math.max(260, Math.min(460, storedLeft))}px`);

    let activeSide: string | null = null;

    function onMove(ev: any) {
      if (!activeSide) return;
      const rect = frameRails!.getBoundingClientRect();
      if (activeSide === 'left') {
        const next = Math.max(260, Math.min(460, ev.clientX - rect.left));
        frameRails!.style.setProperty('--left-width', `${next}px`);
      }
    }

    function stopDrag() {
      if (!activeSide) return;
      const left = frameRails!.style.getPropertyValue('--left-width').replace('px', '');
      localStorage.setItem('dashboard_left_width', left);
      document.body.classList.remove('is-resizing');
      activeSide = null;
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', stopDrag);
    }

    function startDrag(side: string) {
      if (window.innerWidth < 1100) return;
      activeSide = side;
      document.body.classList.add('is-resizing');
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', stopDrag);
    }

    leftResize.addEventListener('pointerdown', (ev: any) => {
      if (ev.target.closest && ev.target.closest('.rail-toggle')) return;
      startDrag('left');
    });

    const leftToggle = document.getElementById('left-toggle');
    const leftRailEl = document.getElementById('left-rail');

    function applyRailState() {
      const l = localStorage.getItem('dashboard_left_collapsed') === '1';
      frameRails!.classList.toggle('left-collapsed', l);
      if (leftRailEl) leftRailEl.classList.toggle('collapsed', l);
      if (leftToggle) leftToggle.textContent = l ? '›' : '‹';
      if (leftToggle) leftToggle.setAttribute('aria-expanded', String(!l));
    }

    function toggleLeftRail() {
      const cur = localStorage.getItem('dashboard_left_collapsed') === '1';
      localStorage.setItem('dashboard_left_collapsed', cur ? '0' : '1');
      applyRailState();
    }

    leftToggle?.addEventListener('click', (e: any) => { e.stopPropagation(); toggleLeftRail(); });

    document.addEventListener('keydown', (ev: KeyboardEvent) => {
      if ((ev.altKey || ev.metaKey) && ev.key === '1') { ev.preventDefault(); toggleLeftRail(); }
    });

    if (localStorage.getItem('dashboard_left_collapsed') === null) localStorage.setItem('dashboard_left_collapsed', '0');
    applyRailState();
  }

  chatForm?.addEventListener('submit', async (ev: Event) => {
    ev.preventDefault();
    const name = chatNameInput?.value?.trim();
    if (!name) return;

    try {
      const resp = await apiFetch(`/chats/?user_id=${user.id}`, {
        method: 'POST',
        body: JSON.stringify({ name }),
      });
      if (!resp.ok) throw new Error(`${resp.status}: ${await readError(resp)}`);
      if (chatNameInput) chatNameInput.value = '';
      await loadChats();
    } catch (err: any) {
      console.error('Chat creation error:', err);
      alert('Error creating chat: ' + (err?.message || err));
    }
  });

  sendBtn?.addEventListener('click', sendQuery);
  queryInput?.addEventListener('keydown', (ev: KeyboardEvent) => {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      ev.preventDefault();
      sendQuery();
    }
  });

  dropzoneLabel?.addEventListener('dragover', (ev: any) => {
    ev.preventDefault();
    dropzoneLabel.classList.add('dropzone-active');
  });

  dropzoneLabel?.addEventListener('dragleave', () => {
    dropzoneLabel.classList.remove('dropzone-active');
  });

  dropzoneLabel?.addEventListener('drop', (ev: any) => {
    ev.preventDefault();
    dropzoneLabel.classList.remove('dropzone-active');
    const file = ev.dataTransfer?.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setStatus('Only PDF files are supported', 'danger');
      return;
    }
    setSelectedUpload(file);
  });

  fileInput?.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      const file = fileInput.files[0];
      if (file.type && file.type !== 'application/pdf') {
        setStatus('Only PDF files are supported', 'danger');
        fileInput.value = '';
        return;
      }
      setSelectedUpload(file);
    }
  });

  uploadBtn?.addEventListener('click', () => {
    if (selectedUploadFile) {
      uploadFile(selectedUploadFile);
    } else if (fileInput?.files && fileInput.files[0]) {
      uploadFile(fileInput.files[0]);
    } else {
      fileInput?.click();
    }
  });

  summaryForm?.addEventListener('submit', generateSummary);
  summaryClearBtn?.addEventListener('click', () => {
    if (summaryTopic) summaryTopic.value = '';
    resetSummary();
  });

  flashcardGenerateBtn?.addEventListener('click', generateFlashcards);
  flashcardClearBtn?.addEventListener('click', clearFlashcards);

  logoutBtn?.addEventListener('click', () => {
    ['access_token', 'refresh_token', 'current_user'].forEach((k) => localStorage.removeItem(k));
    window.location.replace('/login');
  });

  refreshBtn?.addEventListener('click', loadChats);

  function updateTopbarButtons() {
    const hasChat = Boolean(selectedChatId);
    if (summarizerBtn) (summarizerBtn as HTMLElement).style.display = hasChat ? '' : 'none';
    if (flashcardBtn) (flashcardBtn as HTMLElement).style.display = hasChat ? '' : 'none';
    updateNavActive();
  }

  function updateNavActive() {
    const set = (btn: Element | null, active: boolean) => {
      if (!btn) return;
      btn.classList.toggle('nav-tab-active', active);
      if (active) btn.setAttribute('aria-current', 'page');
      else btn.removeAttribute('aria-current');
    };
    set(navChatBtn, currentView === 'chat');
    set(summarizerBtn, currentView === 'summarizer');
    set(flashcardBtn, currentView === 'flashcard');
  }

  const summaryPanel = document.getElementById('summary-panel-container');
  const flashcardPanel = document.getElementById('flashcard-panel-container');
  const summaryClose = document.getElementById('summary-close');
  const flashcardClose = document.getElementById('flashcard-close');

  function showSummaryPanel() {
    if (!summaryPanel) return;
    if (messageStream) messageStream.style.display = 'none';
    summaryPanel.hidden = false;
    if (flashcardPanel) flashcardPanel.hidden = true;
    currentView = 'summarizer';
    updateNavActive();
    setComposerMode('upload');
  }

  function showFlashcardPanel() {
    if (!flashcardPanel) return;
    if (messageStream) messageStream.style.display = 'none';
    flashcardPanel.hidden = false;
    if (summaryPanel) summaryPanel.hidden = true;
    currentView = 'flashcard';
    updateNavActive();
    setComposerMode('upload');
  }

  function closePanels() {
    if (summaryPanel) summaryPanel.hidden = true;
    if (flashcardPanel) flashcardPanel.hidden = true;
    if (messageStream) messageStream.style.display = '';
    currentView = 'chat';
    updateNavActive();
    setComposerMode('chat');
  }

  function setComposerMode(mode: string) {
    const bar = document.querySelector('.composer-bar') as HTMLElement | null;
    if (!composerUpload || !bar) return;
    if (mode === 'upload') {
      composerUpload.hidden = false;
      bar.style.display = 'none';
    } else {
      composerUpload.hidden = true;
      bar.style.display = '';
    }
  }

  summarizerBtn?.addEventListener('click', () => { showSummaryPanel(); });
  flashcardBtn?.addEventListener('click', () => { showFlashcardPanel(); });
  summaryClose?.addEventListener('click', () => { closePanels(); });
  flashcardClose?.addEventListener('click', () => { closePanels(); });
  navChatBtn?.addEventListener('click', () => { closePanels(); });

  profileMenuToggle?.addEventListener('click', (e: any) => {
    e.stopPropagation();
    if (!profileDropdown) return;
    const isOpen = !profileDropdown.hidden;
    profileDropdown.hidden = isOpen;
    profileMenuToggle.setAttribute('aria-expanded', String(!isOpen));
  });

  document.addEventListener('click', (ev: any) => {
    if (!profileDropdown || profileDropdown.hidden) return;
    const pill = document.getElementById('profile-pill');
    if (!pill?.contains(ev.target)) {
      profileDropdown.hidden = true;
      profileMenuToggle?.setAttribute('aria-expanded', 'false');
    }
  });

  setupResizableRails();
  loadChats();

  // Modal helpers
  const actionModal = document.getElementById('action-modal');
  const modalTitle = document.getElementById('modal-title');
  const modalMessage = document.getElementById('modal-message');
  const modalInput = document.getElementById('modal-input') as HTMLInputElement | null;
  const modalError = document.getElementById('modal-error');
  const modalClose = document.getElementById('modal-close');
  const modalCancel = document.getElementById('modal-cancel');
  const modalConfirm = document.getElementById('modal-confirm') as HTMLButtonElement | null;

  let modalResolve: ((value: any) => void) | null = null;

  function openModal({
    title = 'Confirm',
    message = '',
    showInput = false,
    inputValue = '',
    confirmText = 'Confirm',
    confirmClass = 'btn-danger',
  }: {
    title?: string;
    message?: string;
    showInput?: boolean;
    inputValue?: string;
    confirmText?: string;
    confirmClass?: string;
  } = {}) {
    if (modalTitle) modalTitle.textContent = title;
    if (modalMessage) modalMessage.textContent = message;
    if (modalError) { modalError.hidden = true; modalError.textContent = ''; }
    if (modalInput) {
      modalInput.style.display = showInput ? '' : 'none';
      modalInput.value = inputValue || '';
    }
    if (modalConfirm) {
      modalConfirm.textContent = confirmText;
      modalConfirm.className = confirmClass;
    }
    if (actionModal) {
      actionModal.hidden = false;
      actionModal.setAttribute('open', '');
    }

    return new Promise((resolve) => {
      modalResolve = resolve;
    });
  }

  function closeModal() {
    if (actionModal) {
      actionModal.hidden = true;
      actionModal.removeAttribute('open');
    }
    if (modalError) { modalError.hidden = true; modalError.textContent = ''; }
    if (modalInput) modalInput.value = '';
    if (modalResolve) {
      modalResolve(null);
      modalResolve = null;
    }
  }

  modalClose?.addEventListener('click', closeModal);
  modalCancel?.addEventListener('click', closeModal);
  actionModal?.addEventListener('click', (ev: any) => { if (ev.target === actionModal) closeModal(); });
  document.addEventListener('keydown', (ev: KeyboardEvent) => {
    if (ev.key === 'Escape' && actionModal && !actionModal.hidden) closeModal();
  });

  modalConfirm?.addEventListener('click', () => {
    if (!modalResolve) return;
    const val = modalInput && modalInput.style.display === '' ? modalInput.value.trim() : true;
    modalResolve(val);
    modalResolve = null;
    closeModal();
  });
})();
