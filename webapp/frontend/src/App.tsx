/**
 * Main App Component
 * Handles routing and authentication
 */

import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';

// Lazy load all page components for code splitting
const Login = lazy(() => import('./pages/Login'));
const MultiTabDashboard = lazy(() => import('./pages/MultiTabDashboard'));
const ProjectsOverview = lazy(() => import('./pages/ProjectsOverview'));
const JobsHistory = lazy(() => import('./pages/JobsHistory'));
const NotFound = lazy(() => import('./pages/NotFound'));

// Loading fallback component
const LoadingFallback: React.FC = () => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    backgroundColor: '#F9FAFB',
  }}>
    <div style={{
      textAlign: 'center',
    }}>
      <div style={{
        width: '48px',
        height: '48px',
        border: '4px solid #E5E7EB',
        borderTopColor: '#3B82F6',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
        margin: '0 auto 16px',
      }} />
      <p style={{
        fontSize: '16px',
        color: '#6B7280',
      }}>
        Lädt...
      </p>
    </div>
  </div>
);

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<ProtectedRoute><MultiTabDashboard /></ProtectedRoute>} />
            <Route path="/projects" element={<ProtectedRoute><ProjectsOverview /></ProtectedRoute>} />
            <Route path="/jobs" element={<ProtectedRoute><JobsHistory /></ProtectedRoute>} />
            <Route path="/" element={<Navigate to="/projects" replace />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  );
};

// Protected Route Component
interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const token = localStorage.getItem('auth_token');

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default App;
