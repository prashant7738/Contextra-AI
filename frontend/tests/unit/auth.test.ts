import { describe, it, expect, beforeEach } from 'vitest';
import { AuthService } from '../../src/utils/auth';

describe('AuthService', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns null when no user is stored', () => {
    expect(AuthService.getCurrentUser()).toBeNull();
  });

  it('round-trips a stored user', () => {
    AuthService.setCurrentUser({ id: 1, name: 'Ada', email: 'ada@example.com' });
    expect(AuthService.getCurrentUser()).toEqual({
      id: 1,
      name: 'Ada',
      email: 'ada@example.com',
    });
  });

  it('reports isAuthenticated based on access token', () => {
    expect(AuthService.isAuthenticated()).toBe(false);
    AuthService.setTokens({
      access_token: 'a.b.c',
      refresh_token: 'r.s.t',
      token_type: 'bearer',
    });
    expect(AuthService.isAuthenticated()).toBe(true);
  });

  it('clearTokens removes every stored auth field', () => {
    AuthService.setTokens({
      access_token: 'a',
      refresh_token: 'r',
      token_type: 'bearer',
    });
    AuthService.setCurrentUser({ id: 2, name: 'B', email: 'b@x' });

    AuthService.clearTokens();

    expect(AuthService.getAccessToken()).toBeNull();
    expect(AuthService.getRefreshToken()).toBeNull();
    expect(AuthService.getCurrentUser()).toBeNull();
  });

  it('getAuthHeader returns Bearer header when a token exists', () => {
    AuthService.setTokens({
      access_token: 'xyz',
      refresh_token: 'r',
      token_type: 'bearer',
    });
    expect(AuthService.getAuthHeader()).toEqual({ Authorization: 'Bearer xyz' });
  });

  it('getAuthHeader returns empty object when no token', () => {
    expect(AuthService.getAuthHeader()).toEqual({});
  });
});
