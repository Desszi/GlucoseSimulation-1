import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { theme } from '../theme';
import heroSvg from '../assets/diabetes_hero.svg';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
  const ok = await login(username, password);
    setLoading(false);
    if (!ok) {
      setError('Sikertelen bejelentkezés');
    } else {
      window.location.href = '/';
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'radial-gradient(circle at 30% 20%, #164e63 0, #0f172a 60%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 400, background: theme.colors.panel, padding: 32, borderRadius: theme.radius.lg, boxShadow: theme.shadow }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 20 }}>
          <img src={heroSvg} alt="Glükóz szimulátor" style={{ width: 120, height: 120, marginBottom: 12 }} />
          <h1 style={{ margin: 0, fontSize: 30, letterSpacing: '.5px', background: 'linear-gradient(90deg,#10b981,#0d946a)', WebkitBackgroundClip: 'text', color: 'transparent' }}>Glükóz szimulátor</h1>
          <div style={{ fontSize: 13, color: theme.colors.textDim, marginTop: 4 }}>Lépj be a személyre szabott modellezéshez</div>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={labelStyle}>Felhasználónév</label>
            <input value={username} onChange={e => setUsername(e.target.value)} required style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Jelszó</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required style={inputStyle} />
          </div>
          {error && <div style={{ color: theme.colors.danger, fontSize: 13 }}>{error}</div>}
          <button type="submit" disabled={loading} style={buttonStyle}>{loading ? 'Belépés...' : 'Belépés'}</button>
          <div style={{ marginTop: 4, fontSize: 11, textAlign: 'center', color: theme.colors.textDim }}>
            Nincs még fiókod? API regisztráció:<br/>
            <code style={{ fontSize: 10 }}>POST /auth/register {`{"username":"ujbeteg","password":"jelszo","role":"patient"}`}</code>
          </div>
        </form>
      </div>
    </div>
  );
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  background: theme.colors.panelAlt,
  border: `1px solid ${theme.colors.border}`,
  color: theme.colors.text,
  borderRadius: theme.radius.sm,
  fontSize: 14
};
const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: 6,
  fontSize: 12,
  letterSpacing: '.5px',
  textTransform: 'uppercase',
  color: theme.colors.textDim
};
const buttonStyle: React.CSSProperties = {
  background: theme.colors.primary,
  border: 'none',
  color: theme.colors.text,
  padding: '12px 16px',
  fontSize: 15,
  borderRadius: theme.radius.sm,
  cursor: 'pointer',
  fontWeight: 600,
  letterSpacing: '.5px'
};

