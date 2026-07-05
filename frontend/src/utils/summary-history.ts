export interface SummaryHistoryEntry {
  data?: any;
  topic: string;
  nResults: number;
  updatedAt: string;
}

export interface SummaryRestoreState {
  current: SummaryHistoryEntry | null;
  previous: SummaryHistoryEntry[];
}

function entryKey(entry: SummaryHistoryEntry | null | undefined): string {
  if (!entry) return '';
  return [entry.updatedAt || '', entry.topic || '', String(entry.nResults || '')].join('|');
}

/**
 * Normalizes the cached summary and the persisted per-chat history into a
 * single restore state.
 *
 * If the single-item cache is present, it stays current and the history list is
 * deduplicated behind it. If the cache is missing, the newest history entry is
 * promoted to current so older summaries are still reachable after a chat switch.
 */
export function buildSummaryRestoreState(
  cached: SummaryHistoryEntry | null,
  history: SummaryHistoryEntry[] | null | undefined,
): SummaryRestoreState {
  const merged: SummaryHistoryEntry[] = [];
  const seen = new Set<string>();

  const pushEntry = (entry: SummaryHistoryEntry | null | undefined) => {
    if (!entry) return;
    const key = entryKey(entry);
    if (seen.has(key)) return;
    seen.add(key);
    merged.push(entry);
  };

  pushEntry(cached?.data ? cached : null);
  (history || []).forEach((entry) => pushEntry(entry));

  const current = merged[0] ?? null;
  return {
    current,
    previous: merged.slice(1),
  };
}
