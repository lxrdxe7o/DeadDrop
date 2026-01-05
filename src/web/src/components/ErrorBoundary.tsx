/**
 * Error Boundary Component
 *
 * Catches React errors and displays a styled fallback UI.
 * Prevents the entire app from crashing when a component throws an error.
 */

import { Component, ErrorInfo, ReactNode } from 'react';
import { EncryptionMesh } from './EncryptionMesh';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Error Boundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <>
          <EncryptionMesh />
          <div className="page-container">
            <div className="glass-card">
              {/* Error Icon */}
              <div className="text-center mb-6">
                <svg 
                  width="64" 
                  height="64" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="var(--error)" 
                  strokeWidth="1.5"
                  style={{ 
                    margin: '0 auto',
                    filter: 'drop-shadow(0 0 20px rgba(239, 68, 68, 0.5))'
                  }}
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>

              {/* Error Title */}
              <h2 className="text-center" style={{ color: 'var(--error)' }}>
                Something Went Wrong
              </h2>
              <p className="text-center text-secondary mt-2">
                We're sorry, but something unexpected happened.
              </p>

              {/* Error Details (Development Only) */}
              {import.meta.env.DEV && this.state.error && (
                <details className="mt-6">
                  <summary 
                    className="text-sm text-muted"
                    style={{ cursor: 'pointer', marginBottom: 'var(--space-2)' }}
                  >
                    Error Details (Development Only)
                  </summary>
                  <pre
                    style={{
                      padding: 'var(--space-4)',
                      background: 'var(--surface-dark)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: 'var(--text-xs)',
                      overflow: 'auto',
                      color: 'var(--error)',
                      border: '1px solid var(--glass-border)',
                    }}
                  >
                    {this.state.error.toString()}
                    {this.state.errorInfo && this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}

              {/* Action Buttons */}
              <div className="flex gap-4 mt-6">
                <button
                  onClick={this.handleReset}
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="1 4 1 10 7 10" />
                    <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
                  </svg>
                  <span>Try Again</span>
                </button>
                <button
                  onClick={() => window.location.reload()}
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="23 4 23 10 17 10" />
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                  </svg>
                  <span>Refresh Page</span>
                </button>
              </div>
            </div>
          </div>
        </>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
