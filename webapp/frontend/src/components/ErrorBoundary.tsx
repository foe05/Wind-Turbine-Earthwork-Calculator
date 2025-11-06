/**
 * Error Boundary - Catches React errors and displays fallback UI
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
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

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to console (in production, send to error tracking service)
    console.error('Error Boundary caught an error:', error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/projects';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={styles.container}>
          <div style={styles.content}>
            <div style={styles.errorIcon}>⚠️</div>
            <h1 style={styles.title}>Ein Fehler ist aufgetreten</h1>
            <p style={styles.message}>
              Entschuldigung, etwas ist schief gelaufen. Bitte versuchen Sie es erneut.
            </p>

            <div style={styles.buttonGroup}>
              <button onClick={this.handleReload} style={styles.primaryButton}>
                Seite neu laden
              </button>
              <button onClick={this.handleGoHome} style={styles.secondaryButton}>
                Zur Startseite
              </button>
            </div>

            {/* Show error details in development */}
            {import.meta.env.DEV && this.state.error && (
              <details style={styles.details}>
                <summary style={styles.summary}>Fehlerdetails (nur in Entwicklung sichtbar)</summary>
                <div style={styles.errorDetails}>
                  <h3 style={styles.errorTitle}>Fehlermeldung:</h3>
                  <pre style={styles.errorMessage}>{this.state.error.toString()}</pre>

                  {this.state.errorInfo && (
                    <>
                      <h3 style={styles.errorTitle}>Stack Trace:</h3>
                      <pre style={styles.stackTrace}>{this.state.errorInfo.componentStack}</pre>
                    </>
                  )}
                </div>
              </details>
            )}

            {/* Helpful information */}
            <div style={styles.helpBox}>
              <h3 style={styles.helpTitle}>Was können Sie tun?</h3>
              <ul style={styles.helpList}>
                <li>Laden Sie die Seite neu</li>
                <li>Löschen Sie Ihren Browser-Cache</li>
                <li>Versuchen Sie es mit einem anderen Browser</li>
                <li>
                  Wenn das Problem weiterhin besteht, kontaktieren Sie bitte den Support
                </li>
              </ul>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    backgroundColor: '#F9FAFB',
    padding: '24px',
  },
  content: {
    textAlign: 'center' as const,
    maxWidth: '800px',
    width: '100%',
  },
  errorIcon: {
    fontSize: '80px',
    marginBottom: '24px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: '16px',
  },
  message: {
    fontSize: '18px',
    color: '#6B7280',
    marginBottom: '32px',
    lineHeight: '1.6',
  },
  buttonGroup: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    marginBottom: '32px',
  },
  primaryButton: {
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    color: 'white',
    backgroundColor: '#EF4444',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  secondaryButton: {
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    color: '#3B82F6',
    backgroundColor: 'white',
    border: '2px solid #3B82F6',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  details: {
    marginTop: '32px',
    textAlign: 'left' as const,
    backgroundColor: '#FEE2E2',
    padding: '16px',
    borderRadius: '8px',
    border: '1px solid #FCA5A5',
  },
  summary: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#991B1B',
    cursor: 'pointer',
    marginBottom: '12px',
  },
  errorDetails: {
    marginTop: '12px',
  },
  errorTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#991B1B',
    marginTop: '12px',
    marginBottom: '8px',
  },
  errorMessage: {
    fontSize: '13px',
    color: '#7F1D1D',
    backgroundColor: '#FEF2F2',
    padding: '12px',
    borderRadius: '4px',
    overflow: 'auto',
    maxHeight: '150px',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
  },
  stackTrace: {
    fontSize: '12px',
    color: '#7F1D1D',
    backgroundColor: '#FEF2F2',
    padding: '12px',
    borderRadius: '4px',
    overflow: 'auto',
    maxHeight: '300px',
    whiteSpace: 'pre' as const,
    fontFamily: 'monospace',
  },
  helpBox: {
    marginTop: '48px',
    textAlign: 'left' as const,
    backgroundColor: 'white',
    padding: '24px',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  helpTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: '16px',
  },
  helpList: {
    fontSize: '16px',
    color: '#4B5563',
    lineHeight: '1.8',
    paddingLeft: '24px',
  },
};

export default ErrorBoundary;
