import { describe, expect, it } from 'vitest';
import { safeJsonParse } from '../../src/utils/safe-json';

describe('safeJsonParse', () => {
  it('parses valid JSON', () => {
    expect(safeJsonParse('{"a":1}', {})).toEqual({ a: 1 });
  });

  it('returns fallback for null/undefined/empty', () => {
    expect(safeJsonParse(null, 'x')).toBe('x');
    expect(safeJsonParse(undefined, 'x')).toBe('x');
    expect(safeJsonParse('', 'x')).toBe('x');
  });

  it('returns fallback for malformed JSON without throwing', () => {
    expect(safeJsonParse('{not json}', null)).toBe(null);
    expect(safeJsonParse('undefined', 42)).toBe(42);
  });

  it('preserves the type of the fallback', () => {
    const out = safeJsonParse<{ x: number }>('garbage', { x: 0 });
    expect(out.x).toBe(0);
  });
});
