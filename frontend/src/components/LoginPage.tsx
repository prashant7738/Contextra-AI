import { useId, useState, type FormEvent } from 'react';
import { apiClient } from '../utils/api';
import { AuthService, type AuthTokens, type User } from '../utils/auth';
import './AuthPages.css';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const errorId = useId();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await apiClient.login(email, password);
      if (response.error) {
        setError(response.error);
        return;
      }
      if (response.data) {
        AuthService.setTokens(response.data as AuthTokens);
        const userResponse = await apiClient.getMe();
        if (userResponse.data) {
          AuthService.setCurrentUser(userResponse.data as User);
        }
        window.location.href = '/dashboard';
      }
    } catch {
      setError('An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  const isInvalid = Boolean(error);

  return (
    <div className="auth-container">
      <main className="auth-card" aria-labelledby="login-title">
        <h1 id="login-title">Login</h1>
        <form onSubmit={handleSubmit} noValidate>
          {error && (
            <div className="error-message" role="alert" id={errorId}>
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              disabled={loading}
              aria-invalid={isInvalid || undefined}
              aria-describedby={isInvalid ? errorId : undefined}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
              aria-invalid={isInvalid || undefined}
              aria-describedby={isInvalid ? errorId : undefined}
            />
          </div>

          <button type="submit" className="submit-button" disabled={loading} aria-busy={loading}>
            {loading ? 'Logging in…' : 'Login'}
          </button>
        </form>

        <p className="auth-link">
          Don't have an account? <a href="/register">Register here</a>
        </p>
      </main>
    </div>
  );
}
