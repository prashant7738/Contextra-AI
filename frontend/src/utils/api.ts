import { AuthService } from './auth';

export const API_BASE_URL =
  (import.meta.env.PUBLIC_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

// Legacy alias kept for any importers still using `API_BASE`.
export const API_BASE = API_BASE_URL;

export const DEFAULT_TIMEOUT_MS = 15_000;

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

export interface ApiRequestOptions extends Omit<RequestInit, 'signal'> {
  /** Override the default 15-second request timeout. Set to `null` to disable. */
  timeoutMs?: number | null;
  /** Optional caller-provided signal — composed with the timeout signal. */
  signal?: AbortSignal;
}

/** Compose multiple AbortSignals into one (no AbortSignal.any in older runtimes). */
function composeSignals(signals: Array<AbortSignal | undefined>): AbortSignal | undefined {
  const real = signals.filter((s): s is AbortSignal => Boolean(s));
  if (real.length === 0) return undefined;
  if (real.length === 1) return real[0];
  const controller = new AbortController();
  const onAbort = (sig: AbortSignal) => () =>
    controller.abort((sig as AbortSignal & { reason?: unknown }).reason);
  for (const sig of real) {
    if (sig.aborted) {
      controller.abort((sig as AbortSignal & { reason?: unknown }).reason);
      break;
    }
    sig.addEventListener('abort', onAbort(sig), { once: true });
  }
  return controller.signal;
}

// ── Single-flight refresh ──────────────────────────────────────────
// Multiple concurrent 401s must not trigger multiple refresh calls
// (each would invalidate the previous refresh_token on the server).
let inFlightRefresh: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  if (inFlightRefresh) return inFlightRefresh;
  const refreshToken = AuthService.getRefreshToken();
  if (!refreshToken) return false;

  inFlightRefresh = (async () => {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
          signal: controller.signal,
        });
        if (!response.ok) {
          AuthService.clearTokens();
          return false;
        }
        const data = await response.json();
        AuthService.setTokens(data);
        return true;
      } finally {
        clearTimeout(timer);
      }
    } catch {
      AuthService.clearTokens();
      return false;
    } finally {
      inFlightRefresh = null;
    }
  })();

  return inFlightRefresh;
}

/**
 * Low-level fetch wrapper. Handles:
 *   - Authorization header from AuthService
 *   - Default 15s timeout via AbortController (configurable per call)
 *   - Single-flight refresh on 401 with one transparent retry
 *   - Redirect to /login when refresh fails
 *
 * Returns the raw `Response` so callers can stream, read blobs, etc.
 * Use `apiClient.get/post/put/delete` for JSON requests.
 */
export async function apiFetch(
  endpoint: string,
  options: ApiRequestOptions = {},
  retry: boolean = true,
): Promise<Response> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal: userSignal, headers, ...rest } = options;

  const timeoutController = timeoutMs == null ? null : new AbortController();
  const timer = timeoutController
    ? setTimeout(() => timeoutController.abort(), timeoutMs ?? DEFAULT_TIMEOUT_MS)
    : null;
  const signal = composeSignals([timeoutController?.signal, userSignal]);

  const baseHeaders: Record<string, string> = { ...AuthService.getAuthHeader() };
  // Only set Content-Type if there's a body and caller didn't already (FormData must NOT have one).
  const isFormData = typeof FormData !== 'undefined' && rest.body instanceof FormData;
  if (rest.body && !isFormData && !(headers && 'Content-Type' in (headers as object))) {
    baseHeaders['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...rest,
      headers: { ...baseHeaders, ...(headers as Record<string, string> | undefined) },
      signal,
    });

    if (response.status === 401 && retry && AuthService.getAccessToken()) {
      const refreshed = await refreshTokens();
      if (refreshed) {
        return apiFetch(endpoint, options, false);
      }
      if (typeof window !== 'undefined') {
        window.location.replace('/login');
      }
    }

    return response;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function makeRequest<T>(
  endpoint: string,
  options: ApiRequestOptions = {},
): Promise<ApiResponse<T>> {
  try {
    const response = await apiFetch(endpoint, options);

    if (response.status === 204) {
      return { status: 204 };
    }

    let payload: unknown = undefined;
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      payload = await response.json().catch(() => undefined);
    } else {
      const text = await response.text().catch(() => '');
      payload = text || undefined;
    }

    if (!response.ok) {
      const detail =
        (payload &&
          typeof payload === 'object' &&
          'detail' in (payload as Record<string, unknown>) &&
          String((payload as Record<string, unknown>).detail)) ||
        (typeof payload === 'string' ? payload : '') ||
        `Request failed with status ${response.status}`;
      return { error: detail, status: response.status };
    }

    return { data: payload as T, status: response.status };
  } catch (error) {
    const aborted =
      error instanceof DOMException && (error.name === 'AbortError' || error.name === 'TimeoutError');
    return {
      error: aborted
        ? 'Request timed out.'
        : error instanceof Error
        ? error.message
        : 'Network error',
      status: 0,
    };
  }
}

export const apiClient = {
  register: (name: string, email: string, password: string) =>
    makeRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    }),

  login: (email: string, password: string) =>
    makeRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  refreshToken: (refreshToken: string) =>
    makeRequest('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),

  getMe: () => makeRequest('/auth/me', { method: 'GET' }),

  getUsers: (skip: number = 0, limit: number = 100) =>
    makeRequest(`/users/?skip=${skip}&limit=${limit}`, { method: 'GET' }),

  get: <T = unknown>(endpoint: string, options?: ApiRequestOptions) =>
    makeRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T = unknown, B = unknown>(endpoint: string, body: B, options?: ApiRequestOptions) =>
    makeRequest<T>(endpoint, { ...options, method: 'POST', body: JSON.stringify(body) }),

  put: <T = unknown, B = unknown>(endpoint: string, body: B, options?: ApiRequestOptions) =>
    makeRequest<T>(endpoint, { ...options, method: 'PUT', body: JSON.stringify(body) }),

  delete: <T = unknown>(endpoint: string, options?: ApiRequestOptions) =>
    makeRequest<T>(endpoint, { ...options, method: 'DELETE' }),

  /** Upload a file (or any FormData payload). Skips JSON Content-Type. */
  upload: <T = unknown>(endpoint: string, form: FormData, options?: ApiRequestOptions) =>
    makeRequest<T>(endpoint, { ...options, method: 'POST', body: form }),
};

// Test-only hook: reset the in-flight refresh promise so unit tests are deterministic.
// Not exported through the package barrel; consumers must import explicitly.
export function __resetApiInternalsForTests(): void {
  inFlightRefresh = null;
}

