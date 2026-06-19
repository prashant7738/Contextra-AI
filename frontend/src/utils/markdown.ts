import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Single configuration point for all markdown rendering across the app.
marked.setOptions({
  gfm: true,
  breaks: true,
});

/** Render Markdown to a safe HTML string. Use for `innerHTML` assignment. */
export function renderMarkdown(source: string): string {
  if (!source) return '';
  const rawHtml = marked.parse(source, { async: false }) as string;
  return DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
  });
}

/** Strip Markdown and HTML to a plain text excerpt. */
export function markdownToPlainText(source: string, maxLength?: number): string {
  if (!source) return '';
  const html = marked.parse(source, { async: false }) as string;
  const clean = DOMPurify.sanitize(html, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
  const text = clean.replace(/\s+/g, ' ').trim();
  if (maxLength && text.length > maxLength) {
    return text.slice(0, maxLength - 1).trimEnd() + '…';
  }
  return text;
}
