import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// We re-import the module per test to control module-level state.
async function loadApi() {
  vi.resetModules();
  return await import('../../src/utils/api');
}

describe('apiClient.get — auth, refresh, single-flight', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('sends Authorization header when access token is present', async () => {
    localStorage.setItem('access_token', 'tok');
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const { apiClient } = await loadApi();
    const res = await apiClient.get('/me');

    expect(res.status).toBe(200);
    expect(res.data).toEqual({ ok: true });
    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok');
  });

  it('refreshes on 401 and retries the request once', async () => {
    localStorage.setItem('access_token', 'expired');
    localStorage.setItem('refresh_token', 'refresh');

    const fetchMock = vi
      .fn()
      // 1. Original call — 401
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'expired' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        }),
      )
      // 2. Refresh endpoint — success
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: 'fresh',
            refresh_token: 'r2',
            token_type: 'bearer',
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        ),
      )
      // 3. Retried call — success
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ data: 'ok' }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);

    const { apiClient } = await loadApi();
    const res = await apiClient.get('/protected');

    expect(res.status).toBe(200);
    expect(res.data).toEqual({ data: 'ok' });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(localStorage.getItem('access_token')).toBe('fresh');
    expect(localStorage.getItem('refresh_token')).toBe('r2');
  });

  it('single-flights concurrent refreshes: 3 concurrent 401s hit /refresh only once', async () => {
    localStorage.setItem('access_token', 'expired');
    localStorage.setItem('refresh_token', 'refresh');

    let refreshCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo, _init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/auth/refresh')) {
        refreshCalls += 1;
        // Small delay so concurrent callers overlap.
        await new Promise((r) => setTimeout(r, 10));
        return new Response(
          JSON.stringify({ access_token: 'fresh', refresh_token: 'r2', token_type: 'bearer' }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }
      // Protected calls: first time return 401, subsequent return 200.
      const auth = (_init?.headers as Record<string, string> | undefined)?.Authorization;
      if (auth === 'Bearer expired') {
        return new Response(JSON.stringify({ detail: 'expired' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ ok: 1 }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    const { apiClient } = await loadApi();
    const results = await Promise.all([
      apiClient.get('/a'),
      apiClient.get('/b'),
      apiClient.get('/c'),
    ]);

    expect(results.every((r) => r.status === 200)).toBe(true);
    expect(refreshCalls).toBe(1);
  });

  it('clears tokens and reports error when refresh fails', async () => {
    localStorage.setItem('access_token', 'expired');
    localStorage.setItem('refresh_token', 'bad');
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { replace: vi.fn(), href: '' },
    });

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('', { status: 401 }))
      .mockResolvedValueOnce(new Response('', { status: 401 }));
    vi.stubGlobal('fetch', fetchMock);

    const { apiClient } = await loadApi();
    await apiClient.get('/protected');

    expect(localStorage.getItem('access_token')).toBe(null);
    expect((window.location.replace as ReturnType<typeof vi.fn>)).toHaveBeenCalledWith('/login');
  });

  it('upload() sends FormData without setting Content-Type', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const { apiClient } = await loadApi();
    const fd = new FormData();
    fd.append('file', new Blob(['hi']), 'a.txt');
    await apiClient.upload('/upload', fd);

    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBe(fd);
    expect((init.headers as Record<string, string>)['Content-Type']).toBeUndefined();
  });
});
