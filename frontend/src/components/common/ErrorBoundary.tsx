import { Component, ErrorInfo, ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional custom fallback. Receives the error and a reset callback. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches uncaught render errors in its subtree and shows a branded fallback
 * instead of letting a single component crash white-screen the whole app.
 *
 * Mounted twice: once at the app root (main.tsx) as a catch-all, and once
 * around the routed <Outlet/> (AppLayout) so a page crash keeps the shell alive.
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface in dev tools / monitoring; replace with a logging service if available.
    console.error("Uncaught render error:", error, info.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    if (this.props.fallback) return this.props.fallback(error, this.reset);

    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-6 text-center">
        <div className="mx-auto w-full max-w-md">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-error-50 text-error-500 dark:bg-error-500/15">
            <svg
              className="h-8 w-8"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>

          <h1 className="mb-2 text-title-sm font-semibold text-gray-800 dark:text-white/90">
            Something went wrong
          </h1>
          <p className="mb-8 text-theme-sm text-gray-500 dark:text-gray-400">
            An unexpected error occurred while rendering this page. You can try
            again, or head back to your dashboard.
          </p>

          <div className="flex items-center justify-center gap-3">
            <button
              onClick={this.reset}
              className="inline-flex items-center justify-center rounded-lg bg-brand-500 px-5 py-3 text-sm font-medium text-white shadow-theme-xs transition hover:bg-brand-600"
            >
              Try again
            </button>
            <a
              href="/dashboard"
              className="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white px-5 py-3 text-sm font-medium text-gray-700 shadow-theme-xs transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-white/[0.03]"
            >
              Back to Dashboard
            </a>
          </div>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
