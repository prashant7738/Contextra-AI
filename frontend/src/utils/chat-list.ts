import { escapeHtml } from './escapeHtml';

export interface ChatListItem {
  id: number;
  local_id: number;
  name: string;
  created_at?: string | null;
}

/**
 * Build the sidebar chat list markup. Every server value is escaped: chat names
 * are user-controlled and this string is assigned to innerHTML.
 */
export function renderChatListHtml(
  chats: ChatListItem[],
  selectedLocalId: number | null,
  formatDate: (iso: string) => string,
): string {
  return chats
    .map((chat) => {
      const active = chat.local_id === selectedLocalId ? ' chat-item-active' : '';
      const created = chat.created_at ? formatDate(chat.created_at) : '';
      return `<div class="chat-item${active}" data-chat-id="${Number(chat.id)}" data-local-id="${Number(chat.local_id)}" data-created-at="${escapeHtml(chat.created_at || '')}">
          <button class="chat-select" type="button">
            <span>${escapeHtml(chat.name)}</span>
            <small>${escapeHtml(created)}</small>
          </button>
          <button class="chat-menu" type="button" title="Chat actions" aria-label="Chat actions">⋯</button>
        </div>`;
    })
    .join('');
}
