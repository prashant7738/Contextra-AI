/**
 * Parse JSON with a fallback. Never throws.
 * Use at the boundary with persisted/serialized data (localStorage, URL, etc.).
 */
export function safeJsonParse<T>(raw: string | null | undefined, fallback: T): T {
  if (raw == null || raw === '') return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}
