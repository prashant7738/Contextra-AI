import { API_BASE_URL } from '../utils/api';

const PING_INTERVAL_MS = 120_000;

async function ping(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/health`, { method: 'GET', cache: 'no-store' });
  } catch (error) {
    console.error('Backend health check failed', error);
  }
}

export function startKeepAlive(): () => void {
  ping();
  const intervalId = window.setInterval(ping, PING_INTERVAL_MS);
  return () => window.clearInterval(intervalId);
}
