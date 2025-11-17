import React from 'react';
import { useAuth } from '../context/AuthContext';

interface Props {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<Props> = ({ children }) => {
  const { token } = useAuth();
  if (!token) {
    return <div>Nem vagy bejelentkezve. Kérlek jelentkezz be.<br/><a href="/login">Login</a></div>;
  }
  return <>{children}</>;
};
