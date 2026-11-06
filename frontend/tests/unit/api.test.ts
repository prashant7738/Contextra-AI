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
    const fetchMock = vi.fn<typeof fetch>(async () =>
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
    const init = fetchMock.mock.calls[0][1]!;
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
    const fetchMock = vi.fn<typeof fetch>(async (input: RequestInfo | URL, _init?: RequestInit) => {
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
    const fetchMock = vi.fn<typeof fetch>(async () =>
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

    const init = fetchMock.mock.calls[0][1]!;
    expect(init.body).toBe(fd);
    expect((init.headers as Record<string, string>)['Content-Type']).toBeUndefined();
  });
});

describe('extractErrorDetail', () => {
  it('reads string, validation-list and missing details', async () => {
    const { extractErrorDetail } = await import('../../src/utils/api');
    expect(extractErrorDetail({ detail: 'Email already registered' }, 400)).toBe('Email already registered');
    expect(
      extractErrorDetail(
        { detail: [{ loc: ['body', 'email'], msg: 'Value error, Enter a valid email address' }, { msg: 'Too short' }] },
        422,
      ),
    ).toBe('Enter a valid email address; Too short');
    expect(extractErrorDetail(undefined, 503)).toBe('Request failed with status 503');
    expect(extractErrorDetail('Bad gateway', 502)).toBe('Bad gateway');
  });
});

describe('refresh edge cases and logout', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('keeps the session when another tab already rotated the refresh token', async () => {
    localStorage.setItem('access_token', 'expired');
    localStorage.setItem('refresh_token', 'old');
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/auth/refresh')) {
        // Meanwhile the other tab stored fresh tokens.
        localStorage.setItem('access_token', 'from-other-tab');
        localStorage.setItem('refresh_token', 'new');
        return new Response(JSON.stringify({ detail: 'used' }), { status: 401, headers: { 'content-type': 'application/json' } });
      }
      const auth = new Headers(init?.headers).get('Authorization');
      return auth === 'Bearer from-other-tab'
        ? new Response(JSON.stringify({ ok: 1 }), { status: 200, headers: { 'content-type': 'application/json' } })
        : new Response(JSON.stringify({ detail: 'expired' }), { status: 401, headers: { 'content-type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);

    const { apiClient } = await loadApi();
    const res = await apiClient.get('/protected');
    expect(res.status).toBe(200);
    expect(localStorage.getItem('refresh_token')).toBe('new');
  });

  it('does not sign the user out when the refresh request fails on the network', async () => {
    localStorage.setItem('access_token', 'expired');
    localStorage.setItem('refresh_token', 'r');
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (String(input).endsWith('/auth/refresh')) throw new TypeError('Failed to fetch');
      return new Response(JSON.stringify({ detail: 'expired' }), { status: 401, headers: { 'content-type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);
    const { apiClient } = await loadApi();
    await apiClient.get('/protected');
    expect(localStorage.getItem('refresh_token')).toBe('r');
  });

  it('logout revokes server-side and clears tokens and cached study data', async () => {
    localStorage.setItem('access_token', 'a');
    localStorage.setItem('refresh_token', 'r');
    localStorage.setItem('current_user', '{"id":1,"email":"x"}');
    localStorage.setItem('dashboard_summary_cache_1_2', '{}');
    localStorage.setItem('dashboard_flashcards_cache_1_2', '{}');
    localStorage.setItem('dashboard_left_width', '300');
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetchMock);

    const { logout } = await loadApi();
    logout();

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/auth\/logout$/);
    expect(JSON.parse(String(init!.body))).toEqual({ refresh_token: 'r' });
    expect(init!.keepalive).toBe(true);
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('current_user')).toBeNull();
    expect(localStorage.getItem('dashboard_summary_cache_1_2')).toBeNull();
    expect(localStorage.getItem('dashboard_flashcards_cache_1_2')).toBeNull();
    expect(localStorage.getItem('dashboard_left_width')).toBe('300');
  });
});
