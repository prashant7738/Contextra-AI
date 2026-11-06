import { beforeEach, describe, expect, it } from 'vitest';
import { SUMMARY_HISTORY_LIMIT, createChatCache } from '../../src/scripts/dashboard/cache';

describe('createChatCache', () => {
  beforeEach(() => localStorage.clear());

  it('isolates users and chats', () => {
    const a = createChatCache(1);
    const b = createChatCache(2);
    a.write('summary', 5, { v: 'a' });
    expect(a.read('summary', 5)).toEqual({ v: 'a' });
    expect(b.read('summary', 5)).toBeNull();
    expect(a.read('summary', 6)).toBeNull();
    expect(a.read('flashcards', 5)).toBeNull();
  });

  it('keeps summary history newest first and bounded', () => {
    const cache = createChatCache(1);
    for (let i = 0; i < SUMMARY_HISTORY_LIMIT + 5; i++) cache.appendSummaryHistory(3, { topic: `t${i}` });
    const history = cache.readSummaryHistory(3);
    expect(history).toHaveLength(SUMMARY_HISTORY_LIMIT);
    expect(history[0].topic).toBe(`t${SUMMARY_HISTORY_LIMIT + 4}`);
  });

  it('survives corrupted storage', () => {
    localStorage.setItem('dashboard_summary_cache_1_1', '{not json');
    localStorage.setItem('dashboard_summary_history_1_1', '{"not":"an array"}');
    const cache = createChatCache(1);
    expect(cache.read('summary', 1)).toBeNull();
    expect(cache.readSummaryHistory(1)).toEqual([]);
  });

  it('uses key prefixes that logout() clears', () => {
    const cache = createChatCache(1);
    cache.write('summary', 1, {});
    cache.write('flashcards', 1, {});
    cache.appendSummaryHistory(1, { topic: 'x' });
    const keys = Object.keys(localStorage);
    expect(keys.every((k) => /^dashboard_(summary|flashcards)_/.test(k))).toBe(true);
  });
});
