import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  fallback?: ReactNode;
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  message?: string;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Component-island errors are logged but not reported externally.
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div role="alert" style={{ padding: '24px', textAlign: 'center' }}>
            <h2>Something went wrong.</h2>
            <p>{this.state.message ?? 'An unexpected error occurred.'}</p>
            <button type="button" onClick={() => window.location.reload()}>
              Reload page
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
