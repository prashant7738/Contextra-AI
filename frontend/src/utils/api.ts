import { AuthService } from './auth';

const API_BASE_URL = import.meta.env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

async function makeRequest<T>(
  endpoint: string,
  options: RequestInit = {}
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
