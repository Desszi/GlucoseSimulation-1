import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { MealsPage } from './pages/MealsPage';
import { ProfilePage } from './pages/ProfilePage';
import { SimulationRunnerPage } from './pages/SimulationRunnerPage';
import { SimulationRunsPage } from './pages/SimulationRunsPage';
import { ChatPage } from './pages/ChatPage';
import { DoctorPatientsPage } from './pages/DoctorPatientsPage';
import { DoctorChatPage } from './pages/DoctorChatPage';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import heroSvg from './assets/diabetes_hero.svg';

const Dashboard: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
        <img src={heroSvg} alt="Glükóz szimulátor" style={{ width: 90, height: 90, flexShrink: 0 }} />
        <div>
          <h1 style={{ margin: 0, fontSize: 34, letterSpacing: '.5px', background: 'linear-gradient(90deg,#10b981,#0d946a)', WebkitBackgroundClip: 'text', color: 'transparent' }}>Glükóz szimulátor</h1>
          <p style={{ color: '#94a3b8', fontSize: 14, marginTop: 6 }}>Üdvözlünk! Válassz funkciót a bal oldali menüből a kezdéshez.</p>
        </div>
      </div>
      <div style={{ marginTop: 40, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 20 }}>
        {([ 'Ételek', 'Szimuláció', 'Futások', 'Chat'] as const).map(card => {
          const href = `/${card === 'Ételek' ? 'meals' : card === 'Szimuláció' ? 'simulate' : card === 'Futások' ? 'runs' : 'chat'}`;
          const desc = card === 'Ételek'
            ? 'Étkezések rögzítése és szerkesztése a modellhez.'
            : card === 'Szimuláció'
              ? 'Napi glükóz lefutás generálása különböző módokkal.'
              : card === 'Futások'
                ? 'Korábbi szimulációs eredmények és metrikák áttekintése.'
                : 'Gyors üzenetváltás orvos és beteg között.';
          return (
            <div key={card} style={{ background: '#1e293b', padding: 20, borderRadius: 10, border: '1px solid #24324a', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 140 }}>
              <div>
                <h3 style={{ margin: '0 0 8px', fontSize: 18 }}>{card}</h3>
                <p style={{ margin: 0, fontSize: 12, color: '#94a3b8' }}>{desc}</p>
              </div>
              <div style={{ marginTop: 12 }}>
                <a href={href} style={{ fontSize: 12, textDecoration: 'none', color: '#10b981' }}>Megnyitás →</a>
              </div>
            </div>
          );
        })}
        {/* Profile card only for non-doctor */}
        {useAuth().role !== 'doctor' && (
          <div style={{ background: '#1e293b', padding: 20, borderRadius: 10, border: '1px solid #24324a', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 140 }}>
            <div>
              <h3 style={{ margin: '0 0 8px', fontSize: 18 }}>Profil</h3>
              <p style={{ margin: 0, fontSize: 12, color: '#94a3b8' }}>Személyes és terápiás adatok karbantartása.</p>
            </div>
            <div style={{ marginTop: 12 }}>
              <a href="/profile" style={{ fontSize: 12, textDecoration: 'none', color: '#10b981' }}>Megnyitás →</a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const AppInner: React.FC = () => {
  const { token } = useAuth();
  const path = window.location.pathname;
  if (!token && path !== '/login') {
    window.history.replaceState({}, '', '/login');
    return <LoginPage />;
  }
  if (path === '/login') {
    return token ? <Dashboard /> : <LoginPage />;
  }
  if (path === '/meals') {
    return (
      <ProtectedRoute>
        <Layout><MealsPage /></Layout>
      </ProtectedRoute>
    );
  }
  if (path === '/profile') {
    if (useAuth().role === 'doctor') {
      window.history.replaceState({}, '', '/');
      return <Dashboard />;
    }
    return (
      <ProtectedRoute>
        <Layout><ProfilePage /></Layout>
      </ProtectedRoute>
    );
  }
  if (path === '/simulate') {
    return (
      <ProtectedRoute>
        <Layout><SimulationRunnerPage /></Layout>
      </ProtectedRoute>
    );
  }
  if (path === '/runs') {
    return (
      <ProtectedRoute>
        <Layout><SimulationRunsPage /></Layout>
      </ProtectedRoute>
    );
  }
  if (path === '/chat') {
    return (
      <ProtectedRoute>
        <Layout><ChatPage /></Layout>
      </ProtectedRoute>
    );
  }
  if (path === '/doctor/patients') {
    return (
      <ProtectedRoute>
        <Layout><DoctorPatientsPage /></Layout>
      </ProtectedRoute>
    );
  }
  if (path === '/doctor/chat') {
    return (
      <ProtectedRoute>
        <Layout><DoctorChatPage /></Layout>
      </ProtectedRoute>
    );
  }
  return (
    <ProtectedRoute>
      <Layout><Dashboard /></Layout>
    </ProtectedRoute>
  );
};

const App: React.FC = () => (
  <AuthProvider>
    <AppInner />
  </AuthProvider>
);

export default App;
