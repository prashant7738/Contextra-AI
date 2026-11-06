/**
 * Per-user, per-chat localStorage cache for generated study artifacts.
 * Storage failures (private mode, quota) are ignored: the cache is a convenience.
 * Keys start with dashboard_summary_ / dashboard_flashcards_ so logout() can
 * clear them (see utils/api.ts).
 */
import type { SummaryHistoryEntry } from './render';

export type CacheKind = 'summary' | 'flashcards';

export const SUMMARY_HISTORY_LIMIT = 20;

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore storage failures */
  }
}

export function createChatCache(userId: number) {
  const cacheKey = (kind: CacheKind, chatId: number) => `dashboard_${kind}_cache_${userId}_${chatId}`;
  const historyKey = (chatId: number) => `dashboard_summary_history_${userId}_${chatId}`;

  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    read(kind: CacheKind, chatId: number): any {
      return read(cacheKey(kind, chatId), null);
    },
    write(kind: CacheKind, chatId: number, value: unknown): void {
      write(cacheKey(kind, chatId), value);
    },
    /** Saved summaries for this chat, newest first. */
    readSummaryHistory(chatId: number): SummaryHistoryEntry[] {
      const history = read<unknown>(historyKey(chatId), []);
      return Array.isArray(history) ? (history as SummaryHistoryEntry[]) : [];
    },
    appendSummaryHistory(chatId: number, entry: SummaryHistoryEntry): void {
      const history = this.readSummaryHistory(chatId);
      history.unshift(entry);
      write(historyKey(chatId), history.slice(0, SUMMARY_HISTORY_LIMIT));
    },
  };
}

export type ChatCache = ReturnType<typeof createChatCache>;
