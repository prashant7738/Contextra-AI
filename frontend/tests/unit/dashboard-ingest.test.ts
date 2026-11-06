import { afterEach, describe, expect, it, vi } from 'vitest';

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

async function load() {
  vi.resetModules();
  return import('../../src/scripts/dashboard/ingest');
}

describe('dashboard ingest helpers', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('uploadDirect posts multipart form data and returns the task id', async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => json({ task_id: 42, status: 'pending' }));
    vi.stubGlobal('fetch', fetchMock);
    const { uploadDirect } = await load();
    const id = await uploadDirect(new File(['%PDF-'], 'a.pdf'), 1, 3);
    expect(id).toBe(42);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/documents\/ingest\/direct\?user_id=1&chat_id=3$/);
    expect(init!.body).toBeInstanceOf(FormData);
  });

  it('surfaces readable API errors', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async () => json({ detail: 'Only PDF files are supported' }, 422)));
    const { uploadDirect } = await load();
    await expect(uploadDirect(new File(['x'], 'a.txt'), 1, 3)).rejects.toThrow('422: Only PDF files are supported');
  });

  it('uploadViaPresign: presign, PUT to storage, confirm', async () => {
    const calls: string[] = [];
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      calls.push(`${init?.method ?? 'GET'} ${url.replace(/^https?:\/\/[^/]+/, '')}`);
      if (url.includes('/presign')) return json({ task_id: 7, upload_url: 'https://storage.example/upload?token=t' });
      if (url.startsWith('https://storage.example')) return new Response(null, { status: 200 });
      return json({ task_id: 7, status: 'pending' });
    }));
    const { uploadViaPresign } = await load();
    expect(await uploadViaPresign(new File(['%PDF-'], 'a.pdf'), 1, 3)).toBe(7);
    expect(calls).toEqual([
      'POST /documents/ingest/presign?user_id=1&chat_id=3',
      'PUT /upload?token=t',
      'POST /documents/ingest/7/confirm?user_id=1',
    ]);
  });

  it('pollIngestionTask resolves on completion and reports progress', async () => {
    const statuses = [...Array(11).fill('processing'), 'completed'];
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async () => json({ task_id: 1, status: statuses.shift(), chunks_count: 9 })));
    const { pollIngestionTask } = await load();
    const progress: number[] = [];
    const done = await pollIngestionTask(1, 1, { sleep: async () => {}, onProgress: (s) => progress.push(s) });
    expect(done.chunks_count).toBe(9);
    expect(progress).toEqual([20]);
  });

  it('pollIngestionTask throws the server error message on failure', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async () => json({ task_id: 1, status: 'failed', error_message: 'No readable text' })));
    const { pollIngestionTask } = await load();
    await expect(pollIngestionTask(1, 1, { sleep: async () => {} })).rejects.toThrow('No readable text');
  });

  it('pollIngestionTask times out', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async () => json({ task_id: 1, status: 'processing' })));
    const { pollIngestionTask } = await load();
    await expect(pollIngestionTask(1, 1, { sleep: async () => {}, maxAttempts: 3 })).rejects.toThrow(/timed out/);
  });
});
