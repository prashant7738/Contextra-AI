import { describe, expect, it } from 'vitest';
import { renderChatListHtml } from '../../src/utils/chat-list';

const fmt = (iso: string) => `fmt(${iso})`;

describe('renderChatListHtml', () => {
  it('escapes user-controlled chat names', () => {
    const html = renderChatListHtml(
      [{ id: 1, local_id: 1, name: '<img src=x onerror=alert(1)>', created_at: '2026-01-01' }],
      null,
      fmt,
    );
    const container = document.createElement('div');
    container.innerHTML = html;
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('.chat-select span')?.textContent).toBe('<img src=x onerror=alert(1)>');
  });

  it('marks the selected chat active and keeps data attributes', () => {
    const html = renderChatListHtml(
      [
        { id: 10, local_id: 1, name: 'A', created_at: '2026-01-01' },
        { id: 11, local_id: 2, name: 'B', created_at: null },
      ],
      2,
      fmt,
    );
    const container = document.createElement('div');
    container.innerHTML = html;
    const items = container.querySelectorAll<HTMLElement>('.chat-item');
    expect(items).toHaveLength(2);
    expect(items[0].classList.contains('chat-item-active')).toBe(false);
    expect(items[1].classList.contains('chat-item-active')).toBe(true);
    expect(items[1].dataset.chatId).toBe('11');
    expect(items[1].dataset.localId).toBe('2');
    expect(items[0].querySelector('small')?.textContent).toBe('fmt(2026-01-01)');
  });

  it('cannot break out of attributes via created_at', () => {
    const html = renderChatListHtml(
      [{ id: 1, local_id: 1, name: 'A', created_at: '" onmouseover="alert(1)' }],
      null,
      fmt,
    );
    const container = document.createElement('div');
    container.innerHTML = html;
    expect(container.querySelector('.chat-item')?.getAttribute('onmouseover')).toBeNull();
  });
});
