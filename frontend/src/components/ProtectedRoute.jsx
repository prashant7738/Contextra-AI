import React from 'react';
import { Navigate } from 'react-router-dom';
import { AuthService } from '../utils/auth';

export default function ProtectedRoute({ children }) {
  const isAuthenticated = AuthService.isAuthenticated();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
