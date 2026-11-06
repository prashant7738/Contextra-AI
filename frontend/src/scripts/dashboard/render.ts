/**
 * Pure HTML builders for the dashboard. Every value that comes from the
 * server, the user or localStorage is escaped here (or sanitized markdown),
 * because the results are assigned to innerHTML.
 */
import { escapeHtml } from '../../utils/escapeHtml';
import { renderMarkdown } from '../../utils/markdown';

export interface Reference {
  filename?: string | null;
  page?: number | string | null;
  document_id?: number | null;
}

export interface SummarySection {
  heading?: string;
  items?: string[];
}

export interface SummaryData {
  title?: string | null;
  topic?: string | null;
  summary?: string | null;
  sections?: SummarySection[];
  references?: Reference[];
  chunks_used?: number;
}

export interface SummaryHistoryEntry {
  data?: SummaryData;
  topic?: string;
  nResults?: number;
  updatedAt?: string;
}

export interface Flashcard {
  topic?: string;
  summary?: string;
  explanation?: string;
  references?: Reference[];
}

export interface ChatMessage {
  user_message: string;
  bot_response?: string | null;
  created_at: string;
}

export type UploadState = 'idle' | 'ready' | 'uploading';

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return 'Now';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Now';
  return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 KB';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

export function referenceItemsHtml(references: Reference[] | undefined, fallbackName = 'Unknown source'): string {
  if (!Array.isArray(references)) return '';
  return references
    .map(
      (ref) =>
        `<li>${escapeHtml(ref.filename || fallbackName)} <small>p.${escapeHtml(ref.page || '-')}</small></li>`,
    )
    .join('');
}

function sourcesDetailsHtml(itemsHtml: string, extraClass = ''): string {
  if (!itemsHtml) return '';
  const cls = extraClass ? `summary-sources ${extraClass}` : 'summary-sources';
  return `<details class="${cls}"><summary class="summary-sources-toggle">References</summary><ul>${itemsHtml}</ul></details>`;
}

/** Collapsible references shown under a chat answer. */
export function chatReferencesHtml(references: Reference[] | undefined): string {
  return sourcesDetailsHtml(referenceItemsHtml(references), 'chat-sources');
}

export function messagesHtml(messages: ChatMessage[], formatDate: (iso: string) => string = formatDateTime): string {
  return messages
    .map(
      (msg) => `
        <article class="turn">
          <div class="turn-meta">${escapeHtml(formatDate(msg.created_at))}</div>
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
}

/** Structured sections when present, otherwise the sanitized markdown summary. */
export function summaryBodyHtml(data: SummaryData): string {
  if (data.sections && data.sections.length > 0) {
    return data.sections
      .map(
        (section) => `
        <div class="summary-section">
          <h4 class="summary-section-heading">${escapeHtml(section.heading || 'Section')}</h4>
          <ul class="summary-section-list">
            ${(section.items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
          </ul>
        </div>
      `,
      )
      .join('');
  }
  if (data.summary) return `<div class="summary-md-body">${renderMarkdown(data.summary)}</div>`;
  return '';
}

export function summaryCardHtml(data: SummaryData): string {
  return `
      <article class="summary-card">
        <div class="summary-card-head">
          <div class="summary-card-meta">
            <span class="pill">${escapeHtml(data.topic || 'all')}</span>
            <span class="pill">${Number(data.chunks_used || 0)} chunks</span>
          </div>
          <h3 class="summary-card-title">${escapeHtml(data.title || data.topic || 'Summary')}</h3>
        </div>
        <div class="summary-card-body">
          ${summaryBodyHtml(data)}
        </div>
        ${sourcesDetailsHtml(referenceItemsHtml(data.references))}
      </article>
    `;
}

export function summaryHistoryHtml(entries: SummaryHistoryEntry[]): string {
  return entries
    .map((entry, idx) => {
      const d = entry.data || {};
      const when = entry.updatedAt ? formatDateTime(entry.updatedAt) : '';
      return `
          <details class="summary-history-item" data-history-index="${idx}">
            <summary class="summary-history-toggle">
              <div class="summary-history-toggle-inner">
                <div class="summary-history-meta">
                  <span class="pill pill-sm">${escapeHtml(d.topic || entry.topic || 'all')}</span>
                  <span class="summary-history-when">${escapeHtml(when)}</span>
                </div>
                <span class="summary-history-title">${escapeHtml(d.title || d.topic || entry.topic || 'Summary')}</span>
              </div>
              <span class="summary-history-chevron" aria-hidden="true">›</span>
            </summary>
            <div class="summary-history-body">
              <article class="summary-card summary-card-sm">
                <div class="summary-card-body">${summaryBodyHtml(d)}</div>
                ${sourcesDetailsHtml(referenceItemsHtml(d.references))}
              </article>
            </div>
          </details>
        `;
    })
    .join('');
}

export function flashcardsHtml(cards: Flashcard[]): string {
  return `
      <div class="flashcard-grid">
        ${cards
          .map((card, index) => {
            const refs = referenceItemsHtml(card.references, 'Source');
            return `
              <article class="flashcard-card" data-card-index="${index}">
                <div class="flashcard-summary" role="button" tabindex="0" aria-expanded="false" data-toggle-index="${index}">
                  <div class="flashcard-topline">
                    <strong class="flashcard-topic">${escapeHtml(card.topic || 'Topic')}</strong>
                    <span class="flashcard-badge">Card ${index + 1}</span>
                  </div>
                  <p class="flashcard-summary-text">${escapeHtml(card.summary || '')}</p>
                  <span class="flashcard-hint">Expand</span>
                </div>
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
}

export function uploadPreviewHtml(file: { name: string; size: number }, state: UploadState): string {
  const uploading = state === 'uploading';
  return `
      <div class="upload-preview-card">
        <div class="upload-preview-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z"/>
            <polyline points="14 2 14 8 20 8"/>
            <path d="M9 14h6"/>
            <path d="M9 18h6"/>
          </svg>
        </div>
        <div class="upload-preview-copy">
          <span class="upload-preview-label">${uploading ? 'Uploading PDF' : 'Selected PDF'}</span>
          <strong class="upload-preview-name">${escapeHtml(file.name)}</strong>
          <span class="upload-preview-meta">${formatFileSize(file.size)}${uploading ? ' · in progress' : ''}</span>
        </div>
        <button class="upload-preview-remove" type="button" data-upload-remove>${uploading ? 'Pending' : 'Remove'}</button>
      </div>
    `;
}
