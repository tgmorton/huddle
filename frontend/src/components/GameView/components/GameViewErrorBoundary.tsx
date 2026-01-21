/**
 * GameViewErrorBoundary - Error boundary for GameView
 *
 * Prevents rendering errors from crashing the entire game.
 * Provides recovery options and error details for debugging.
 */

import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  children: ReactNode;
  /** Optional name for identifying which section crashed */
  section?: string;
  /** Fallback UI to render instead of children on error */
  fallback?: ReactNode;
  /** Callback when error occurs */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Whether to show a minimal error UI (for nested boundaries) */
  minimal?: boolean;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class GameViewErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log error details
    console.error('[GameViewErrorBoundary] Caught error:', error);
    console.error('[GameViewErrorBoundary] Component stack:', errorInfo.componentStack);

    // Call optional callback
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    });
  };

  toggleDetails = (): void => {
    this.setState(prev => ({ showDetails: !prev.showDetails }));
  };

  render(): ReactNode {
    const { hasError, error, errorInfo, showDetails } = this.state;
    const { children, section, fallback, minimal } = this.props;

    if (!hasError) {
      return children;
    }

    // Use custom fallback if provided
    if (fallback) {
      return fallback;
    }

    // Minimal error UI for nested boundaries
    if (minimal) {
      return (
        <div className="game-view-error-boundary game-view-error-boundary--minimal">
          <div className="game-view-error-boundary__mini-content">
            <AlertTriangle size={16} />
            <span>{section || 'Component'} failed to load</span>
            <button
              className="game-view-error-boundary__retry-btn game-view-error-boundary__retry-btn--small"
              onClick={this.handleRetry}
              title="Retry"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
      );
    }

    // Full error UI
    return (
      <div className="game-view-error-boundary">
        <div className="game-view-error-boundary__content">
          <div className="game-view-error-boundary__icon">
            <AlertTriangle size={32} />
          </div>

          <h2 className="game-view-error-boundary__title">
            {section ? `${section} Error` : 'Something went wrong'}
          </h2>

          <p className="game-view-error-boundary__message">
            {error?.message || 'An unexpected error occurred while rendering this component.'}
          </p>

          <div className="game-view-error-boundary__actions">
            <button
              className="game-view-error-boundary__retry-btn"
              onClick={this.handleRetry}
            >
              <RefreshCw size={16} />
              <span>Try Again</span>
            </button>

            <button
              className="game-view-error-boundary__details-toggle"
              onClick={this.toggleDetails}
            >
              {showDetails ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              <span>{showDetails ? 'Hide Details' : 'Show Details'}</span>
            </button>
          </div>

          {showDetails && (
            <div className="game-view-error-boundary__details">
              <div className="game-view-error-boundary__detail-section">
                <h4>Error</h4>
                <pre>{error?.toString()}</pre>
              </div>

              {error?.stack && (
                <div className="game-view-error-boundary__detail-section">
                  <h4>Stack Trace</h4>
                  <pre>{error.stack}</pre>
                </div>
              )}

              {errorInfo?.componentStack && (
                <div className="game-view-error-boundary__detail-section">
                  <h4>Component Stack</h4>
                  <pre>{errorInfo.componentStack}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }
}

export default GameViewErrorBoundary;
