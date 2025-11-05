/**
 * Main App Component
 * Handles routing and authentication
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import MultiTabDashboard from './pages/MultiTabDashboard';
import ProjectsOverview from './pages/ProjectsOverview';
import JobsHistory from './pages/JobsHistory';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<ProtectedRoute><MultiTabDashboard /></ProtectedRoute>} />
        <Route path="/projects" element={<ProtectedRoute><ProjectsOverview /></ProtectedRoute>} />
        <Route path="/jobs" element={<ProtectedRoute><JobsHistory /></ProtectedRoute>} />
        <Route path="/" element={<Navigate to="/projects" replace />} />
      </Routes>
    </BrowserRouter>
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
