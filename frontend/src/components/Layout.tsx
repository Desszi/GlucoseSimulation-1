import React from 'react';
import { useAuth } from '../context/AuthContext';
import { theme } from '../theme';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { logout, role } = useAuth();
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: theme.colors.bg, color: theme.colors.text, fontFamily: 'system-ui, sans-serif' }}>
      <aside style={{ width: 220, background: theme.colors.panel, padding: '24px 16px', display: 'flex', flexDirection: 'column', borderRight: `1px solid ${theme.colors.border}` }}>
        <h2 style={{ margin: 0, fontSize: 20, letterSpacing: '.5px' }}>GlucoseSim</h2>
        <div style={{ marginTop: 8, fontSize: 12, color: theme.colors.textDim }}>Role: {role}</div>
        <nav style={{ marginTop: 24, flex: 1 }}>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <li><a style={linkStyle} href="/">Dashboard</a></li>
            {role !== 'doctor' && <li><a style={linkStyle} href="/profile">Profil</a></li>}
            <li><a style={linkStyle} href="/meals">Ételek</a></li>
            <li><a style={linkStyle} href="/simulate">Szimuláció</a></li>
            <li><a style={linkStyle} href="/runs">Futások</a></li>
            <li><a style={linkStyle} href="/chat">Chat</a></li>
            {role === 'doctor' && <li><a style={linkStyle} href="/doctor/patients">Páciensek</a></li>}
          </ul>
        </nav>
        <button onClick={logout} style={logoutBtnStyle}>Kijelentkezés</button>
      </aside>
      <main style={{ flex: 1, padding: '32px 40px' }}>
        {children}
      </main>
    </div>
  );
};

const linkStyle: React.CSSProperties = {
  color: theme.colors.textDim,
  textDecoration: 'none',
  fontSize: 14,
  padding: '8px 10px',
  borderRadius: theme.radius.sm,
  transition: 'background .15s, color .15s',
  display: 'block'
};

const logoutBtnStyle: React.CSSProperties = {
  background: theme.colors.panelAlt,
  color: theme.colors.text,
  border: 'none',
  padding: '10px 12px',
  borderRadius: theme.radius.sm,
  cursor: 'pointer',
  fontSize: 13,
  marginTop: 'auto'
};
