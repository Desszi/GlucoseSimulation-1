import React, { useEffect, useState } from 'react';
import { useApi, Meal } from '../api/client';
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

export const SimulationRunnerPage: React.FC = () => {
  const { get, post } = useApi();
  const { role } = useAuth();
  const [meals, setMeals] = useState<Meal[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<RunResult | null>(null);
  const [history, setHistory] = useState<RunResult[]>([]);
  const [timesteps, setTimesteps] = useState<number>(500);
  const [mode, setMode] = useState<string>('simple');
  const [fullDay, setFullDay] = useState<boolean>(false);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);

  async function loadMeals() {
    try {
      const data = await get<Meal[]>('/meals/');
      setMeals(data);
    } catch (e: any) {
      if (e.message?.includes('Not a patient user')) {
        // Doctor/other role: silently ignore; no error panel.
        setMeals([]);
      } else {
        setError(e.message);
      }
    }
  }

  async function loadHistory() {
    setLoadingHistory(true);
    try {
      const data = await get<RunResult[]>('/simulation/runs');
      setHistory(data);
    } catch (e: any) {
      if (e.message?.includes('Not a patient user')) {
        // Doctor view: silently ignore run history load error.
        setHistory([]);
      } else {
        setError(e.message);
      }
    } finally {
      setLoadingHistory(false);
    }
  }

  useEffect(() => { loadMeals(); loadHistory(); }, []);

  function toggle(id: number) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  async function startRun() {
    setError(null);
    setRunning(true);
    setRun(null);
    try {
      const meal_ids = Array.from(selected);
      // Küldjük csak a kiválasztott étkezéseket; ha üres akkor hiba (backend tudna all-et, de UI itt explicit)
      if (meal_ids.length === 0) {
        setError('Válassz ki legalább egy étkezést');
        setRunning(false); return;
      }
  const payload: any = { meal_ids };
  if (!fullDay) payload.timesteps = timesteps;
  if (mode) payload.mode = mode;
  if (fullDay) payload.full_day = true;
  const data = await post<RunResult>('/simulation/run', payload);
      setRun(data);
  setShowModal(true);
      await loadHistory();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  function parseMetrics(jsonStr: string): Record<string, any> {
    try { return JSON.parse(jsonStr); } catch { return {}; }
  }

  const parsedMetrics = run ? (() => { try { return JSON.parse(run.result_metrics); } catch { return {}; } })() : {};
  const fallback = !!parsedMetrics.fallback;
  const simMode = parsedMetrics.mode || (fallback ? 'fallback' : 'unknown');

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 60px)', background: '#141a22', color: '#dde3ea', fontFamily: 'system-ui, sans-serif' }}>
      {/* Left control panel */}
      <div style={{ width: 320, borderRight: '1px solid #202a35', padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 18, background: '#1b222c' }}>
        <h2 style={{ margin: 0, fontSize: 20 }}>Szimuláció</h2>
        {role !== 'patient' && <div style={{ background: '#3a2f00', color: '#ffd666', padding: '6px 10px', borderRadius: 6, fontSize: 12 }}>Csak beteg szerep indíthat futást.</div>}
  {error && <div style={{ background: '#5a1f25', color: '#ffb3bc', padding: '8px 10px', borderRadius: 8, fontSize: 12 }}>{error}</div>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <label style={{ fontSize: 13, fontWeight: 600 }}>Étkezések kiválasztása</label>
          <div style={{ maxHeight: 220, overflowY: 'auto', border: '1px solid #2a343f', borderRadius: 10 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <tbody>
                {meals.map(m => (
                  <tr key={m.id} style={{ borderBottom: '1px solid #232c36' }}>
                    <td style={{ padding: '6px 8px' }}><input type="checkbox" checked={selected.has(m.id)} onChange={() => toggle(m.id)} /></td>
                    <td style={{ padding: '6px 4px', opacity: 0.75 }}>{m.timestamp.split('T').pop()}</td>
                    <td style={{ padding: '6px 4px', color: '#7db1ff' }}>{m.carbs_g}g</td>
                    <td style={{ padding: '6px 4px', opacity: 0.6 }}>{m.meal_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <label style={{ fontSize: 13 }}>Mód
              <select value={mode} onChange={e => setMode(e.target.value)} style={{ width: '100%', marginTop: 4, background: '#242e3a', border: '1px solid #364451', color: '#fff', padding: '6px 8px', borderRadius: 8 }}>
                <option value="simple">Egyszerű</option>
                <option value="physio">Fiziológiai</option>
              </select>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
              <input type="checkbox" checked={fullDay} onChange={e => { setFullDay(e.target.checked); if (e.target.checked) setTimesteps(1440); }} /> 24 órás futás
            </label>
            {!fullDay && (
              <label style={{ fontSize: 13 }}>Timesteps
                <input type="number" min={50} max={2000} value={timesteps} onChange={e => setTimesteps(parseInt(e.target.value)||500)} style={{ width: '100%', marginTop: 4, background: '#242e3a', border: '1px solid #364451', color: '#fff', padding: '6px 8px', borderRadius: 8 }} />
              </label>
            )}
            <button disabled={running || role !== 'patient'} onClick={startRun} style={{ background: running ? '#2d3947' : '#3478f6', transition: 'background .2s', border: 'none', color: '#fff', padding: '10px 14px', borderRadius: 10, cursor: running? 'default':'pointer', fontSize: 14, fontWeight: 600, letterSpacing: '.3px', boxShadow: '0 3px 10px rgba(0,0,0,0.4)' }}>
              {running ? 'Fut...' : 'Futtatás'}
            </button>
            {run && fallback && (
              <div style={{ marginTop: 4, padding: '8px 10px', background: '#473c12', color: '#ffe08a', borderRadius: 8, fontSize: 12 }}>
                Fallback szimuláció – demonstrációs metrikák.
              </div>
            )}
          </div>
        </div>
        <div style={{ marginTop: 'auto', fontSize: 11, opacity: 0.45 }}>v0.1 • Synthetic engine</div>
      </div>
      {/* Main workspace */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
          {/* History list */}
          <div style={{ width: 300, borderRight: '1px solid #202a35', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '16px 18px', borderBottom: '1px solid #202a35', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: 14 }}>Korábbi futások</strong>
              <button onClick={loadHistory} disabled={loadingHistory} style={{ background: '#273341', border: '1px solid #364451', color: '#aad1ff', fontSize: 11, padding: '4px 8px', borderRadius: 6, cursor: 'pointer' }}>Frissít</button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {history.length === 0 && !loadingHistory && <div style={{ padding: 16, fontSize: 12, opacity: 0.6 }}>Nincs futás.</div>}
              {loadingHistory && <div style={{ padding: 16, fontSize: 12 }}>Betöltés...</div>}
              {history.map(h => {
                const metrics = parseMetrics(h.result_metrics);
                return (
                  <div key={h.id} style={{ padding: '12px 14px', borderBottom: '1px solid #202a35', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 4 }} onClick={() => { setRun(h); setShowModal(true); }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                      <span style={{ fontWeight: 600 }}>Run #{h.id}</span>
                      <span style={{ opacity: 0.55 }}>{new Date(h.created_at).toLocaleTimeString()}</span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 11, opacity: .8 }}>
                      {metrics.Peak_BG && <span>Peak {Math.round(metrics.Peak_BG)}</span>}
                      {metrics.Avg_BG && <span>Átlag {Math.round(metrics.Avg_BG)}</span>}
                      {metrics.StdDev_BG && <span>Szórás {Math.round(metrics.StdDev_BG*10)/10}</span>}
                      {metrics.TIR_percent && <span>TIR {Math.round(metrics.TIR_percent)}%</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          {/* Active view placeholder */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '20px 26px', borderBottom: '1px solid #202a35', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 15, fontWeight: 600 }}>Aktív futás</div>
              {run && <button onClick={() => setShowModal(true)} style={{ background: '#273341', border: '1px solid #364451', color: '#fff', fontSize: 12, padding: '6px 10px', borderRadius: 8, cursor: 'pointer' }}>Megnyit</button>}
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
              {!run && <div style={{ fontSize: 13, opacity: 0.6 }}>Még nincs aktív futás – válassz étkezéseket és indítsd a szimulációt.</div>}
              {run && <div style={{ fontSize: 13, opacity: 0.7 }}>Run #{run.id} kész – részletek megnyitása.</div>}
            </div>
          </div>
        </div>
      </div>
      {/* Modal for chart & metrics */}
      {run && showModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.55)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: '#1f2530', padding: 26, borderRadius: 14, width: 'min(1100px, 94vw)', maxHeight: '92vh', overflowY: 'auto', boxShadow: '0 4px 22px rgba(0,0,0,0.55)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: 18 }}>Run #{run.id} eredmények</h3>
              <button onClick={() => setShowModal(false)} style={{ background: '#444c54', color: '#fff', border: 'none', padding: '8px 12px', borderRadius: 8, cursor: 'pointer', fontSize: 12 }}>Bezár</button>
            </div>
            <div style={{ fontSize: 12, marginBottom: 14, display: 'flex', flexWrap: 'wrap', gap: 18 }}>
              <div><strong>Kezdés:</strong> {run.started_at}</div>
              <div><strong>Befejezés:</strong> {run.finished_at}</div>
              <div><strong>Mód:</strong> {simMode}</div>
              {fullDay && <div><strong>Időtartam:</strong> 24h</div>}
            </div>
            <ChartWithMetrics runId={run.id} chartPath={run.chart_path} metricsJson={run.result_metrics} />
          </div>
        </div>
      )}
    </div>
  );
};
