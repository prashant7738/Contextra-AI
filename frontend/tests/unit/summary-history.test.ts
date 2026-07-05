import { describe, expect, it } from 'vitest';
import { buildSummaryRestoreState } from '../../src/utils/summary-history';

describe('buildSummaryRestoreState', () => {
  it('keeps the cached summary as current and preserves older history entries', () => {
    const cached = {
      data: { title: 'Latest' },
      topic: 'all',
      nResults: 5,
      updatedAt: '2026-07-05T10:00:00.000Z',
    };
    const older = {
      data: { title: 'Older' },
      topic: 'chapter 1',
      nResults: 3,
      updatedAt: '2026-07-05T09:00:00.000Z',
    };

    expect(buildSummaryRestoreState(cached, [cached, older])).toEqual({
      current: cached,
      previous: [older],
    });
  });

  it('falls back to the newest history entry when cache is missing', () => {
    const newest = {
      data: { title: 'Newest from history' },
      topic: 'chapter 2',
      nResults: 10,
      updatedAt: '2026-07-05T11:00:00.000Z',
    };
    const older = {
      data: { title: 'Older from history' },
      topic: 'chapter 1',
      nResults: 5,
      updatedAt: '2026-07-05T08:00:00.000Z',
    };

    expect(buildSummaryRestoreState(null, [newest, older])).toEqual({
      current: newest,
      previous: [older],
    });
  });
});
