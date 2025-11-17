import React, { useEffect, useState } from 'react';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { ChartWithMetrics } from '../components/ChartWithMetrics';

interface RunResult {
  id: number;
  patient_id: number;
  created_at: string;
  started_at: string;
  finished_at: string;
  result_metrics: string; // JSON string
  chart_path?: string | null;
}

function parseMetrics(m: string): Record<string, any> { try { return JSON.parse(m); } catch { return {}; } }

export const SimulationRunsPage: React.FC = () => {
  const { get } = useApi();
  const { role } = useAuth();
  const [runs, setRuns] = useState<RunResult[]>([]);
  const [filtered, setFiltered] = useState<RunResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [modeFilter, setModeFilter] = useState<string>('all');
  const [selectedRun, setSelectedRun] = useState<RunResult | null>(null);
  const [showModal, setShowModal] = useState(false);

  async function loadRuns() {
    setLoading(true); setError(null);
    try {
      const data = await get<RunResult[]>('/simulation/runs');
      setRuns(data);
    } catch (e: any) {
      if (e.message && e.message.includes('Not a patient user')) {
        // Doctor szerep esetén inkább csendben ignoráljuk; oldal maga jelzi hogy csak beteg futások.
        setError(null);
      } else {
        setError(e.message);
      }
    } finally { setLoading(false); }
  }

  useEffect(() => { loadRuns(); }, []);

  useEffect(() => {
    let list = [...runs];
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(r => r.id.toString().includes(q) || r.created_at.toLowerCase().includes(q));
    }
    if (modeFilter !== 'all') {
      list = list.filter(r => {
        const mets = parseMetrics(r.result_metrics); return (mets.mode || '').includes(modeFilter);
      });
    }
    setFiltered(list);
  }, [runs, query, modeFilter]);

  function openRun(r: RunResult) { setSelectedRun(r); setShowModal(true); }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 60px)', background: '#141a22', color: '#dde3ea' }}>
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #202a35', display: 'flex', alignItems: 'center', gap: 18 }}>
        <h2 style={{ margin: 0, fontSize: 20 }}>Korábbi szimulációk</h2>
        <div style={{ flex: 1, display: 'flex', gap: 12 }}>
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Keresés (ID vagy dátum)" style={{ flex: 1, background: '#1f2731', border: '1px solid #2f3a46', color: '#fff', padding: '8px 10px', borderRadius: 8, fontSize: 13 }} />
          <select value={modeFilter} onChange={e => setModeFilter(e.target.value)} style={{ width: 140, background: '#1f2731', border: '1px solid #2f3a46', color: '#fff', padding: '8px 10px', borderRadius: 8, fontSize: 13 }}>
            <option value="all">Mindkettő</option>
            <option value="simple">Egyszerű</option>
            <option value="physio">Fiziológiai</option>
          </select>
          <button onClick={loadRuns} disabled={loading} style={{ background: '#3478f6', border: 'none', color: '#fff', padding: '8px 14px', borderRadius: 8, fontSize: 13, cursor: 'pointer' }}>{loading ? 'Betölt…' : 'Frissít'}</button>
        </div>
        {role !== 'patient' && <div style={{ fontSize: 11, background: '#3a2f00', color: '#ffd666', padding: '4px 8px', borderRadius: 6 }}>Csak beteg futások láthatók.</div>}
        {error && <div style={{ fontSize: 11, background: '#5a1f25', color: '#ffb3bc', padding: '4px 8px', borderRadius: 6 }}>{error}</div>}
      </div>
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {filtered.length === 0 && !loading && <div style={{ padding: 32, fontSize: 13, opacity: 0.6 }}>Nincs futás a szűrésnek megfelelően.</div>}
          {filtered.map(r => {
            const m = parseMetrics(r.result_metrics);
            return (
              <div key={r.id} onClick={() => openRun(r)} style={{ padding: '16px 22px', borderBottom: '1px solid #202a35', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 10, transition: 'background .15s' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>Run #{r.id}</div>
                  <div style={{ fontSize: 11, opacity: 0.5 }}>{new Date(r.created_at).toLocaleString()}</div>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, fontSize: 11 }}>
                  {m.mode && <span style={{ background: '#273341', padding: '4px 8px', borderRadius: 6 }}>Mód: {m.mode}</span>}
                  {m.Peak_BG && <span style={{ background: '#273341', padding: '4px 8px', borderRadius: 6 }}>Peak {Math.round(m.Peak_BG)}</span>}
                  {m.Avg_BG && <span style={{ background: '#273341', padding: '4px 8px', borderRadius: 6 }}>Átlag {Math.round(m.Avg_BG)}</span>}
                  {m.StdDev_BG && <span style={{ background: '#273341', padding: '4px 8px', borderRadius: 6 }}>Szórás {Math.round(m.StdDev_BG*10)/10}</span>}
                  {m.TIR_percent && <span style={{ background: '#273341', padding: '4px 8px', borderRadius: 6 }}>TIR {Math.round(m.TIR_percent)}%</span>}
                  {m.Hypo_events && <span style={{ background: '#402a2a', padding: '4px 8px', borderRadius: 6 }}>Hypo {m.Hypo_events}</span>}
                  {m.Hyper_events && <span style={{ background: '#402a2a', padding: '4px 8px', borderRadius: 6 }}>Hyper {m.Hyper_events}</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {selectedRun && showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: '#1f2530', padding: 26, borderRadius: 14, width: 'min(1100px, 94vw)', maxHeight: '92vh', overflowY: 'auto', boxShadow: '0 4px 22px rgba(0,0,0,0.55)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: 18 }}>Run #{selectedRun.id} részletek</h3>
              <button onClick={() => setShowModal(false)} style={{ background: '#444c54', color: '#fff', border: 'none', padding: '8px 12px', borderRadius: 8, cursor: 'pointer', fontSize: 12 }}>Bezár</button>
            </div>
            <div style={{ fontSize: 12, marginBottom: 14, display: 'flex', flexWrap: 'wrap', gap: 18 }}>
              <div><strong>Kezdés:</strong> {selectedRun.started_at}</div>
              <div><strong>Befejezés:</strong> {selectedRun.finished_at}</div>
              <div><strong>Készítés:</strong> {selectedRun.created_at}</div>
            </div>
            <ChartWithMetrics runId={selectedRun.id} chartPath={selectedRun.chart_path} metricsJson={selectedRun.result_metrics} />
          </div>
        </div>
      )}
    </div>
  );
};
