import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthService } from '../utils/auth';

export default function AuthWrapper({ children, redirectTo = '/login' }) {
  const navigate = useNavigate();

  useEffect(() => {
    if (!AuthService.isAuthenticated()) {
      navigate(redirectTo, { replace: true });
    }
  }, [navigate, redirectTo]);

  if (!AuthService.isAuthenticated()) {
    return null; // Don't render children until we confirm auth status
  }

  return <>{children}</>;
}
