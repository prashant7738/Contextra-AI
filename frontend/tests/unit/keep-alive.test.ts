import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('startKeepAlive', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('pings /health immediately and every 2 minutes', async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const { startKeepAlive } = await import('../../src/scripts/keep-alive');
    const stop = startKeepAlive();

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/health$/);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'GET', cache: 'no-store' });

    await vi.advanceTimersByTimeAsync(120_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    stop();
    await vi.advanceTimersByTimeAsync(120_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('swallows fetch errors instead of throwing', async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error('network down');
    });
    vi.stubGlobal('fetch', fetchMock);
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { startKeepAlive } = await import('../../src/scripts/keep-alive');
    const stop = startKeepAlive();

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(errorSpy).toHaveBeenCalled();

    stop();
  });
});
