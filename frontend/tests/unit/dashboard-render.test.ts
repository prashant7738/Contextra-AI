import { describe, expect, it } from 'vitest';
import {
  chatReferencesHtml,
  flashcardsHtml,
  formatFileSize,
  messagesHtml,
  referenceItemsHtml,
  summaryCardHtml,
  summaryHistoryHtml,
  uploadPreviewHtml,
} from '../../src/scripts/dashboard/render';

const XSS = '<img src=x onerror=alert(1)>';

function mount(html: string): HTMLElement {
  const el = document.createElement('div');
  el.innerHTML = html;
  return el;
}

describe('dashboard renderers escape untrusted values', () => {
  it('references (filename and page)', () => {
    const el = mount(referenceItemsHtml([{ filename: XSS, page: '"><b>1</b>' }]));
    expect(el.querySelector('img, b')).toBeNull();
    expect(el.textContent).toContain(XSS);
  });

  it('chat messages: user text escaped, bot markdown sanitized', () => {
    const el = mount(
      messagesHtml([{ user_message: XSS, bot_response: `**bold** <script>alert(1)</script>${XSS}`, created_at: '2026-01-01T00:00:00Z' }], () => 'when'),
    );
    expect(el.querySelector('script, [onerror]')).toBeNull(); // DOMPurify keeps <img src> but strips handlers
    expect(el.querySelector('.bubble-user img')).toBeNull();
    expect(el.querySelector('.bubble-user p:last-child')?.textContent).toBe(XSS);
    expect(el.querySelector('.bot-content strong')?.textContent).toBe('bold');
  });

  it('summary card with sections, title, topic and references', () => {
    const el = mount(
      summaryCardHtml({ title: XSS, topic: XSS, chunks_used: 3, sections: [{ heading: XSS, items: [XSS] }], references: [{ filename: 'a.pdf', page: 2 }] }),
    );
    expect(el.querySelector('img')).toBeNull();
    expect(el.querySelector('.summary-card-title')?.textContent).toBe(XSS);
    expect(el.querySelector('.summary-section-list li')?.textContent).toBe(XSS);
    expect(el.querySelector('.summary-sources li')?.textContent).toContain('a.pdf');
    expect(el.textContent).toContain('3 chunks');
  });

  it('summary card falls back to sanitized markdown when there are no sections', () => {
    const el = mount(summaryCardHtml({ summary: `# Head\n${XSS}` }));
    expect(el.querySelector('img[onerror]')).toBeNull();
    expect(el.querySelector('.summary-md-body h1')?.textContent).toBe('Head');
    expect(el.querySelector('.summary-sources')).toBeNull();
  });

  it('summary history entries', () => {
    const el = mount(summaryHistoryHtml([{ topic: XSS, data: { title: XSS, sections: [{ heading: 'H', items: ['i'] }] }, updatedAt: '2026-01-01T00:00:00Z' }]));
    expect(el.querySelector('img')).toBeNull();
    expect(el.querySelector('.summary-history-title')?.textContent).toBe(XSS);
    expect(el.querySelectorAll('.summary-history-item')).toHaveLength(1);
  });

  it('flashcards', () => {
    const el = mount(flashcardsHtml([{ topic: XSS, summary: XSS, explanation: XSS, references: [{ filename: XSS, page: 1 }] }]));
    expect(el.querySelector('img')).toBeNull();
    expect(el.querySelector('.flashcard-topic')?.textContent).toBe(XSS);
    expect(el.querySelector('[data-toggle-index="0"]')?.getAttribute('aria-expanded')).toBe('false');
  });

  it('upload preview', () => {
    const el = mount(uploadPreviewHtml({ name: XSS, size: 2048 }, 'uploading'));
    expect(el.querySelector('.upload-preview-copy img')).toBeNull();
    expect(el.querySelector('.upload-preview-name')?.textContent).toBe(XSS);
    expect(el.textContent).toContain('2.0 KB · in progress');
  });

  it('chat references block is empty when there are none', () => {
    expect(chatReferencesHtml([])).toBe('');
    expect(mount(chatReferencesHtml([{ filename: 'n.pdf', page: 4 }])).querySelector('.chat-sources li')?.textContent).toBe('n.pdf p.4');
  });

  it('formats file sizes', () => {
    expect(formatFileSize(0)).toBe('0 KB');
    expect(formatFileSize(512)).toBe('512 B');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(25 * 1024 * 1024)).toBe('25 MB');
  });
});
