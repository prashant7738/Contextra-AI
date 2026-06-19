import { AuthService } from './auth';

const API_BASE_URL = import.meta.env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
export const API_BASE = API_BASE_URL;

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

/**
 * Attempts to refresh the access token using the stored refresh token.
 * Returns true on success and updates stored tokens; returns false and clears tokens on failure.
 */
async function refreshTokens(): Promise<boolean> {
  const refreshToken = AuthService.getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      AuthService.clearTokens();
      return false;
    }

    const data = await response.json();
    AuthService.setTokens(data);
    return true;
  } catch {
    AuthService.clearTokens();
    return false;
  }
}

async function makeRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  retry: boolean = true
): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...AuthService.getAuthHeader(),
    ...options.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // On 401, attempt a silent token refresh and retry once (only for authenticated requests)
    if (response.status === 401 && retry && AuthService.getAccessToken()) {
      const refreshed = await refreshTokens();
      if (refreshed) {
        return makeRequest<T>(endpoint, options, false);
      }
      // Refresh failed — clear session and redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      return { error: 'Session expired. Please log in again.', status: 401 };
    }

    const data = await response.json();

    if (!response.ok) {
      return {
        error: data.detail || 'An error occurred',
        status: response.status,
      };
    }

    return {
      data: data as T,
      status: response.status,
    };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : 'Network error',
      status: 0,
    };
  }
}

export const apiClient = {
  register: async (name: string, email: string, password: string) => {
    return makeRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    });
  },

  login: async (email: string, password: string) => {
    return makeRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  refreshToken: async (refreshToken: string) => {
    return makeRequest('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  getMe: async () => {
    return makeRequest('/auth/me', {
      method: 'GET',
    });
  },

  getUsers: async (skip: number = 0, limit: number = 100) => {
    return makeRequest(`/users/?skip=${skip}&limit=${limit}`, {
      method: 'GET',
    });
  },

  get: async <T,>(endpoint: string) => {
    return makeRequest<T>(endpoint, {
      method: 'GET',
    });
  },

  post: async <T,>(endpoint: string, body: any) => {
    return makeRequest<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  put: async <T,>(endpoint: string, body: any) => {
    return makeRequest<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  },

  delete: async <T,>(endpoint: string) => {
    return makeRequest<T>(endpoint, {
      method: 'DELETE',
    });
  },
};
