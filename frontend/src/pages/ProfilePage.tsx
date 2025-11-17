import React, { useEffect, useMemo, useState } from 'react';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';

interface PatientProfile {
  id: number;
  taj: string;
  full_name: string;
  birth_date: string;
  birth_place: string;
  address: string;
  insulin_type: string;
  medications: string;
  doctor_id?: number | null;
}

interface PatientUpdateDto {
  taj?: string | null;
  full_name?: string | null;
  birth_date?: string | null;
  birth_place?: string | null;
  address?: string | null;
  insulin_type?: string | null;
  medications?: string | null;
}

export const ProfilePage: React.FC = () => {
  const { get, patch } = useApi();
  const { role } = useAuth();
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [form, setForm] = useState<PatientUpdateDto>({ taj: '', full_name: '', birth_date: '', birth_place: '', address: '', insulin_type: '', medications: '' });
  const [doctorLinkId, setDoctorLinkId] = useState<number | ''>('');
  const [linkError, setLinkError] = useState<string | null>(null);
  const [linkSuccess, setLinkSuccess] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await get<PatientProfile>('/patients/me');
      setProfile(data);
      setForm({
        taj: data.taj || '',
        full_name: data.full_name || '',
        birth_date: data.birth_date || '',
        birth_place: data.birth_place || '',
        address: data.address || '',
        insulin_type: data.insulin_type || '',
        medications: data.medications || ''
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function update<K extends keyof PatientUpdateDto>(key: K, value: PatientUpdateDto[K]) {
    setForm(f => ({ ...f, [key]: value }));
  }
  async function linkDoctor(e: React.FormEvent) {
    e.preventDefault();
    setLinkError(null); setLinkSuccess(false);
    if (!doctorLinkId) return;
    try {
      // patient initiating link: call assign endpoint with patient id (own profile id) but we need doctor user id -> backend expects patient_id in URL and uses current user (doctor) id. For patient initiated link we need new endpoint; fallback: show info.
      setLinkError('Jelenlegi backend csak doktor oldalról tud hozzárendelni. Kérd meg az orvost, hogy rendelje hozzá a profilod.');
    } catch (e: any) {
      setLinkError(e.message);
    }
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaved(false);
    try {
      const updated = await patch<PatientProfile>('/patients/me', form);
      setProfile(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      setError(e.message);
    }
  }

  const completeness = useMemo(() => {
    if (!profile) return 0;
    const keys: (keyof PatientUpdateDto)[] = ['taj','full_name','birth_date','birth_place','address','insulin_type','medications'];
    const filled = keys.filter(k => (profile as any)[k] && (profile as any)[k].toString().trim().length > 0).length;
    return Math.round((filled / keys.length) * 100);
  }, [profile]);

  const badgeColor = completeness === 100 ? '#10b981' : completeness >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div style={{ maxWidth: 1080, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 30, letterSpacing: '.5px', background: 'linear-gradient(90deg,#10b981,#0d946a)', WebkitBackgroundClip: 'text', color: 'transparent' }}>Beteg profil</h1>
          <div style={{ marginTop: 6, fontSize: 13, color: '#94a3b8' }}>Személyes és terápiás adatok kezelése. Töltsd ki a hiányzó mezőket a pontosabb szimulációhoz.</div>
        </div>
        {!loading && profile && (
          <div style={{ marginLeft: 'auto', background: '#1e293b', border: '1px solid #24324a', padding: '8px 14px', borderRadius: 8, display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
            <span style={{ fontSize: 12, letterSpacing: '.5px', color: '#94a3b8' }}>Kitöltöttség</span>
            <div style={{ fontSize: 16, fontWeight: 600, color: badgeColor }}>{completeness}%</div>
            <div style={{ marginTop: 6, width: 140, height: 6, background: '#24324a', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ width: `${completeness}%`, height: '100%', background: badgeColor, transition: 'width .3s' }} />
            </div>
          </div>
        )}
      </div>

      {loading && <div style={{ marginTop: 40 }}>Betöltés...</div>}
      {error && <div style={{ marginTop: 20, color: '#ef4444' }}>{error}</div>}

      {!loading && profile && (
        <div style={{ marginTop: 36, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 26 }}>
          {/* Személyes adatok kártya */}
          <div style={cardStyle}>
            <h3 style={cardTitleStyle}>Személyes adatok</h3>
            <form onSubmit={save} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 16 }}>
              <Field label="TAJ">
                <input style={inputStyle} value={form.taj || ''} onChange={e => update('taj', e.target.value)} />
              </Field>
              <Field label="Teljes név">
                <input style={inputStyle} value={form.full_name || ''} onChange={e => update('full_name', e.target.value)} />
              </Field>
              <Field label="Születési dátum (YYYY-MM-DD)">
                <input style={inputStyle} value={form.birth_date || ''} onChange={e => update('birth_date', e.target.value)} />
              </Field>
              <Field label="Születési hely">
                <input style={inputStyle} value={form.birth_place || ''} onChange={e => update('birth_place', e.target.value)} />
              </Field>
              <Field label="Lakcím">
                <input style={inputStyle} value={form.address || ''} onChange={e => update('address', e.target.value)} />
              </Field>
              <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {role === 'patient' ? <button type="submit" style={primaryBtnStyle}>Mentés</button> : <div style={{ color: '#f59e0b', fontSize: 13 }}>Csak beteg szerep módosíthatja.</div>}
                {saved && <span style={{ color: '#10b981', fontSize: 13 }}>Mentve.</span>}
              </div>
            </form>
          </div>

          {/* Terápia kártya */}
          <div style={cardStyle}>
            <h3 style={cardTitleStyle}>Terápia</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 16 }}>
              <Field label="Inzulin típus">
                <input style={inputStyle} value={form.insulin_type || ''} onChange={e => update('insulin_type', e.target.value)} />
              </Field>
              <Field label="Gyógyszerek / Megjegyzések">
                <textarea style={{ ...inputStyle, minHeight: 120, resize: 'vertical' }} value={form.medications || ''} onChange={e => update('medications', e.target.value)} />
              </Field>
            </div>
          </div>

          {/* Orvos kártya */}
          <div style={cardStyle}>
            <h3 style={cardTitleStyle}>Orvos kapcsolódás</h3>
            <p style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.4 }}>A jelenlegi MVP-ben az orvos rendeli hozzá a beteget. Kérd meg az orvosod, hogy vegyen fel téged a rendszerében. (Tervezett: beteg kezdeményezés.)</p>
            <form onSubmit={linkDoctor} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap', marginTop: 8 }}>
              <input type="number" placeholder="Doktor user ID" value={doctorLinkId} onChange={e => setDoctorLinkId(e.target.value ? parseInt(e.target.value, 10) : '')} style={inputStyle} />
              <button disabled={role !== 'patient'} type="submit" style={secondaryBtnStyle}>Kapcsolódás (info)</button>
              {linkError && <span style={{ color: '#f59e0b', fontSize: 12 }}>{linkError}</span>}
              {linkSuccess && <span style={{ color: '#10b981', fontSize: 12 }}>Kérés elküldve.</span>}
            </form>
            <div style={{ marginTop: 12, fontSize: 13 }}>Aktuális orvos ID: <span style={{ color: profile.doctor_id ? '#10b981' : '#94a3b8' }}>{profile.doctor_id ?? 'nincs'}</span></div>
          </div>
        </div>
      )}
    </div>
  );
};

// Reusable field wrapper
const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, letterSpacing: '.3px' }}>
    <span style={{ color: '#94a3b8', fontWeight: 500 }}>{label}</span>
    {children}
  </label>
);

const cardStyle: React.CSSProperties = {
  background: '#1e293b',
  border: '1px solid #24324a',
  padding: '22px 22px 26px',
  borderRadius: 14,
  display: 'flex',
  flexDirection: 'column',
  gap: 18,
  minHeight: 180,
  boxShadow: '0 4px 12px -2px rgba(0,0,0,0.35)'
};

const cardTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 17,
  letterSpacing: '.4px',
  fontWeight: 600
};

const inputStyle: React.CSSProperties = {
  background: '#0f172a',
  border: '1px solid #24324a',
  color: '#e2e8f0',
  padding: '10px 12px',
  borderRadius: 8,
  fontSize: 13,
  outline: 'none'
};

const primaryBtnStyle: React.CSSProperties = {
  background: 'linear-gradient(90deg,#10b981,#059669)',
  color: '#fff',
  border: 'none',
  padding: '10px 18px',
  borderRadius: 8,
  fontSize: 13,
  cursor: 'pointer',
  letterSpacing: '.4px'
};

const secondaryBtnStyle: React.CSSProperties = {
  background: '#334155',
  color: '#e2e8f0',
  border: '1px solid #475569',
  padding: '9px 14px',
  borderRadius: 8,
  fontSize: 12,
  cursor: 'pointer'
};
