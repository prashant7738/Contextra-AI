// Token storage and management.
// NOTE: tokens currently live in localStorage. Migration to httpOnly cookies
// requires backend changes and is tracked as a follow-up (see refactor notes).
import { safeJsonParse } from './safe-json';

const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'current_user';

export interface User {
  id: number;
  name: string;
  email: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type AuthEvent = 'login' | 'logout' | 'user-updated';
type AuthListener = (event: AuthEvent) => void;

const listeners = new Set<AuthListener>();

function emit(event: AuthEvent): void {
  listeners.forEach((fn) => {
    try {
      fn(event);
    } catch {
      /* listener errors must not break other listeners */
    }
  });
}

// Cross-tab sync: react to localStorage changes from sibling tabs.
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e) => {
    if (e.key === TOKEN_KEY) {
      emit(e.newValue ? 'login' : 'logout');
    } else if (e.key === USER_KEY) {
      emit('user-updated');
    }
  });
}

export const AuthService = {
  getAccessToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(TOKEN_KEY);
  },

  getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setTokens(tokens: AuthTokens): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem(TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    emit('login');
  },

  clearTokens(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    emit('logout');
  },

  getCurrentUser(): User | null {
    if (typeof window === 'undefined') return null;
    const user = safeJsonParse<User | null>(localStorage.getItem(USER_KEY), null);
    // Light shape check so we don't trust completely arbitrary stored payloads.
    if (user && typeof user.id === 'number' && typeof user.email === 'string') {
      return user;
    }
    return null;
  },

  setCurrentUser(user: User): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    emit('user-updated');
  },

  isAuthenticated(): boolean {
    if (typeof window === 'undefined') return false;
    return !!localStorage.getItem(TOKEN_KEY);
  },

  getAuthHeader(): Record<string, string> {
    const token = AuthService.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },

  subscribe(listener: AuthListener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};

