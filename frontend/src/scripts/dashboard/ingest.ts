/**
 * PDF upload and ingestion-status polling for the dashboard.
 */
import { apiFetch, extractErrorDetail } from '../../utils/api';

export interface IngestionStatus {
  task_id: number;
  status: 'pending_upload' | 'pending' | 'processing' | 'completed' | 'failed' | string;
  chunks_count: number;
  error_message?: string | null;
}

export async function readError(resp: Response): Promise<string> {
  try {
    return extractErrorDetail(await resp.json(), resp.status);
  } catch {
    return resp.statusText || `Request failed with status ${resp.status}`;
  }
}

async function ensureOk(resp: Response): Promise<Response> {
  if (!resp.ok) throw new Error(`${resp.status}: ${await readError(resp)}`);
  return resp;
}

/** Multipart upload to the backend. Returns the ingestion task id. */
export async function uploadDirect(file: File, userId: number, chatId: number): Promise<number> {
  const formData = new FormData();
  formData.append('files', file);
  const resp = await ensureOk(
    await apiFetch(`/documents/ingest/direct?user_id=${userId}&chat_id=${chatId}`, {
      method: 'POST',
      body: formData,
      timeoutMs: 300_000,
    }),
  );
  return (await resp.json()).task_id;
}

/** Upload straight to Supabase Storage through a presigned URL, then confirm. */
export async function uploadViaPresign(file: File, userId: number, chatId: number): Promise<number> {
  const presign = await ensureOk(
    await apiFetch(`/documents/ingest/presign?user_id=${userId}&chat_id=${chatId}`, {
      method: 'POST',
      body: JSON.stringify({ filename: file.name }),
    }),
  );
  const { task_id, upload_url } = await presign.json();

  const uploadResp = await fetch(upload_url, { method: 'PUT', body: file });
  if (!uploadResp.ok) throw new Error(`Storage upload failed: ${uploadResp.status}`);

  await ensureOk(await apiFetch(`/documents/ingest/${task_id}/confirm?user_id=${userId}`, { method: 'POST' }));
  return task_id;
}

export interface PollOptions {
  intervalMs?: number;
  maxAttempts?: number;
  onProgress?: (elapsedSeconds: number) => void;
  sleep?: (ms: number) => Promise<void>;
}

/** Poll until the task completes (resolves with its status) or fails (throws). */
export async function pollIngestionTask(taskId: number, userId: number, options: PollOptions = {}): Promise<IngestionStatus> {
  const intervalMs = options.intervalMs ?? 2000;
  const maxAttempts = options.maxAttempts ?? 300;
  const sleep = options.sleep ?? ((ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms)));

  for (let i = 0; i < maxAttempts; i++) {
    await sleep(intervalMs);
    const resp = await ensureOk(await apiFetch(`/documents/ingest/status/${taskId}?user_id=${userId}`, { timeoutMs: 10_000 }));
    const data: IngestionStatus = await resp.json();
    if (data.status === 'completed') return data;
    if (data.status === 'failed') throw new Error(data.error_message || 'Processing failed');
    if (i > 0 && i % 10 === 0) options.onProgress?.(Math.round((i * intervalMs) / 1000));
  }
  throw new Error(`Processing timed out after ${Math.round((maxAttempts * intervalMs) / 60000)} minutes`);
}
