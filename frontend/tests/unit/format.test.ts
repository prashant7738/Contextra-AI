import { describe, expect, it } from 'vitest';
import { formatDate, formatRelative, truncate } from '../../src/utils/format';

describe('truncate', () => {
  it('returns input unchanged when short enough', () => {
    expect(truncate('hi', 10)).toBe('hi');
  });
  it('appends ellipsis and keeps total length <= max', () => {
    const out = truncate('hello world', 8);
    expect(out.length).toBeLessThanOrEqual(8);
    expect(out.endsWith('…')).toBe(true);
  });
  it('handles empty input', () => {
    expect(truncate('', 5)).toBe('');
  });
});

describe('formatDate', () => {
  it('returns empty string for invalid input', () => {
    expect(formatDate('not-a-date')).toBe('');
    expect(formatDate(null)).toBe('');
    expect(formatDate(undefined)).toBe('');
  });
  it('formats a valid date', () => {
    const out = formatDate('2025-03-04T12:00:00Z');
    expect(out).toMatch(/2025/);
  });
});

describe('formatRelative', () => {
  const now = new Date('2025-03-04T12:00:00Z');
  it('returns empty for invalid input', () => {
    expect(formatRelative(null, now)).toBe('');
  });
  it('formats seconds ago', () => {
    const t = new Date(now.getTime() - 5_000);
    expect(formatRelative(t, now)).toMatch(/second|now/i);
  });
  it('formats hours ago', () => {
    const t = new Date(now.getTime() - 3 * 60 * 60 * 1000);
    expect(formatRelative(t, now)).toMatch(/hour/i);
  });
});
