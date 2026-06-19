/** Small formatting helpers used across the UI. Pure functions, no side effects. */

const SECOND = 1000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const WEEK = 7 * DAY;

const rtf =
  typeof Intl !== 'undefined' && 'RelativeTimeFormat' in Intl
    ? new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
    : null;

/** "Mar 4, 2025" — locale-aware, short month. Returns '' for invalid input. */
export function formatDate(input: string | number | Date | null | undefined): string {
  if (input == null) return '';
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

/** "3 hours ago" / "in 2 days". Returns '' for invalid input. */
export function formatRelative(
  input: string | number | Date | null | undefined,
  now: Date = new Date(),
): string {
  if (input == null) return '';
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.getTime())) return '';
  const diff = d.getTime() - now.getTime();
  const abs = Math.abs(diff);

  if (!rtf) return formatDate(d);
  if (abs < MINUTE) return rtf.format(Math.round(diff / SECOND), 'second');
  if (abs < HOUR) return rtf.format(Math.round(diff / MINUTE), 'minute');
  if (abs < DAY) return rtf.format(Math.round(diff / HOUR), 'hour');
  if (abs < WEEK) return rtf.format(Math.round(diff / DAY), 'day');
  return formatDate(d);
}

/** Truncate with ellipsis. Never returns a string longer than `max`. */
export function truncate(text: string, max: number): string {
  if (!text) return '';
  if (text.length <= max) return text;
  return text.slice(0, Math.max(0, max - 1)).trimEnd() + '…';
}
