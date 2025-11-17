import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useApi } from '../api/client';

interface PatientLite {
  id: number;
  full_name: string;
  taj: string;
  birth_date: string;
  birth_place: string;
  address: string;
  insulin_type: string;
  medications: string;
  doctor_id?: number | null;
}

export const DoctorPatientsPage: React.FC = () => {
  const { role } = useAuth();
  const { get, post } = useApi();
  const [patients, setPatients] = useState<PatientLite[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(null);
  const [manualPatientId, setManualPatientId] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [assigning, setAssigning] = useState<boolean>(false);
  const [showAll, setShowAll] = useState<boolean>(false);

  async function loadPatients() {
    if (role !== 'doctor') return;
    setLoading(true); setError(null);
    try {
      if (showAll) {
        // list all patients
        const data = await get<PatientLite[]>('/patients/');
        setPatients(data);
      } else {
        const data = await get<PatientLite[]>('/patients/doctor/patients');
        setPatients(data);
      }
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  }

  useEffect(() => { loadPatients(); }, [showAll, role]);

  async function assignPatient() {
    if (!manualPatientId) return;
    setAssigning(true); setError(null);
    try {
      await post<PatientLite>(`/patients/assign/${manualPatientId}`, {});
      await loadPatients();
      setManualPatientId(0);
    } catch (e: any) { setError(e.message); } finally { setAssigning(false); }
  }

  async function unassignPatient(id: number) {
    setAssigning(true); setError(null);
    try {
      await post<PatientLite>(`/patients/unassign/${id}`, {});
      await loadPatients();
      if (selectedPatientId === id) setSelectedPatientId(null);
    } catch (e: any) { setError(e.message); } finally { setAssigning(false); }
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 60px)', background: '#141a22', color: '#dde3ea', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ width: 320, borderRight: '1px solid #202a35', padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 18, background: '#1b222c' }}>
        <h2 style={{ margin: 0, fontSize: 20 }}>Betegek</h2>
        {role !== 'doctor' && <div style={{ background: '#3a2f00', color: '#ffd666', padding: '6px 10px', borderRadius: 6, fontSize: 12 }}>Csak doctor szerep.</div>}
        {error && <div style={{ background: '#5a1f25', color: '#ffb3bc', padding: '8px 10px', borderRadius: 8, fontSize: 12 }}>{error}</div>}
        <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" checked={showAll} onChange={e => setShowAll(e.target.checked)} /> Összes beteg
        </label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <label style={{ fontSize: 13 }}>Manuális beteg ID
            <input type="number" value={manualPatientId} onChange={e => setManualPatientId(parseInt(e.target.value, 10) || 0)} style={{ width: '100%', marginTop: 4, background: '#242e3a', border: '1px solid #364451', color: '#fff', padding: '6px 8px', borderRadius: 8 }} />
          </label>
          <button disabled={assigning || role !== 'doctor'} onClick={assignPatient} style={{ background: '#3478f6', border: 'none', color: '#fff', padding: '10px 14px', borderRadius: 10, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>{assigning ? 'Folyamatban…' : 'Hozzárendelés'}</button>
          <button disabled={loading} onClick={loadPatients} style={{ background: '#273341', border: '1px solid #364451', color: '#aad1ff', padding: '8px 12px', borderRadius: 8, cursor: 'pointer', fontSize: 12 }}>{loading ? 'Betölt…' : 'Frissít lista'}</button>
        </div>
        <div style={{ fontSize: 11, opacity: 0.5, marginTop: 'auto' }}>v0.1 • Doctor panel</div>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '14px 24px', borderBottom: '1px solid #202a35', fontSize: 14, fontWeight: 600 }}>Hozzárendelt betegek</div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {patients.length === 0 && !loading && <div style={{ padding: 32, fontSize: 13, opacity: 0.6 }}>Nincs beteg.</div>}
          {patients.map(p => {
            const incomplete = !p.full_name;
            return (
              <div key={p.id} style={{ padding: '16px 22px', borderBottom: '1px solid #202a35', display: 'flex', flexDirection: 'column', gap: 10, background: selectedPatientId === p.id ? '#1f2731' : undefined }} onClick={() => setSelectedPatientId(p.id)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: 15, fontWeight: 600 }}>#{p.id} {p.full_name || 'Név hiányzik'}</div>
                  {p.doctor_id && (
                    <button onClick={(e) => { e.stopPropagation(); unassignPatient(p.id); }} style={{ background: '#402a2a', border: 'none', color: '#ffb3bc', padding: '6px 10px', borderRadius: 8, cursor: 'pointer', fontSize: 11 }}>Leválasztás</button>
                  )}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, fontSize: 11 }}>
                  <span style={{ background: '#273341', padding: '4px 8px', borderRadius: 6 }}>TAJ: {p.taj || '—'}</span>
                  <span style={{ background: '#273341', padding: '4px 8px', borderRadius: 6 }}>Születés: {p.birth_date || '—'}</span>
                  <span style={{ background: '#273341', padding: '4px 8px', borderRadius: 6 }}>Inzulin: {p.insulin_type || '—'}</span>
                  {incomplete && <span style={{ background: '#473c12', padding: '4px 8px', borderRadius: 6 }}>Hiányos profil</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
