import { useId, useState, type FormEvent } from 'react';
import { apiClient } from '../utils/api';
import { AuthService, type AuthTokens, type User } from '../utils/auth';
import './AuthPages.css';

export default function RegisterPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const errorId = useId();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.register(name, email, password);
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
      <main className="auth-card" aria-labelledby="register-title">
        <h1 id="register-title">Register</h1>
        <form onSubmit={handleSubmit} noValidate>
          {error && (
            <div className="error-message" role="alert" id={errorId}>
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="name">Name</label>
            <input
              id="name"
              name="name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your Name"
              required
              disabled={loading}
              aria-invalid={isInvalid || undefined}
              aria-describedby={isInvalid ? errorId : undefined}
            />
          </div>

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
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              required
              minLength={6}
              disabled={loading}
              aria-invalid={isInvalid || undefined}
              aria-describedby={isInvalid ? errorId : undefined}
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter your password"
              required
              minLength={6}
              disabled={loading}
              aria-invalid={isInvalid || undefined}
              aria-describedby={isInvalid ? errorId : undefined}
            />
          </div>

          <button type="submit" className="submit-button" disabled={loading} aria-busy={loading}>
            {loading ? 'Registering…' : 'Register'}
          </button>
        </form>

        <p className="auth-link">
          Already have an account? <a href="/login">Login here</a>
        </p>
      </main>
    </div>
  );
}
