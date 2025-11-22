import React, { useEffect, useState } from 'react';
import { useApi, Meal } from '../api/client';
import { InteractiveSimulationChart, SimulationPoint } from '../components/InteractiveSimulationChart';
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
  const [series, setSeries] = useState<SimulationPoint[] | null>(null);
  const [history, setHistory] = useState<RunResult[]>([]);
  // RL mód fix: 24 órás futás, nincs timesteps / mode választás
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

  // Custom meal builder state
  const [customMeals, setCustomMeals] = useState<{ id: string; time: string; carbs: number }[]>([]);
  const [newMealTime, setNewMealTime] = useState('08:00');
  const [newMealCarbs, setNewMealCarbs] = useState(30);

  function addCustomMeal() {
    if (!/^\d{2}:\d{2}$/.test(newMealTime)) { setError('Idő formátum HH:MM'); return; }
    setCustomMeals(prev => [...prev, { id: Math.random().toString(36).slice(2), time: newMealTime, carbs: newMealCarbs }]);
  }
  function removeCustomMeal(id: string) { setCustomMeals(prev => prev.filter(m => m.id !== id)); }
  function clearMeals() { setCustomMeals([]); }

  async function startRun() {
    setError(null);
    setRunning(true);
    setRun(null);
    try {
      let chosenMeals: any[];
      if (customMeals.length > 0) {
        chosenMeals = customMeals.map(m => ({ timestamp: m.time, carbs_g: m.carbs }));
      } else {
        chosenMeals = meals.filter(m => selected.has(m.id)).map(m => ({ timestamp: m.timestamp.split('T').pop() || m.timestamp, carbs_g: m.carbs_g }));
      }
      if (chosenMeals.length === 0) { setError('Adj hozzá vagy válassz ki legalább egy étkezést'); setRunning(false); return; }
      // RL endpoint hívása
  const rlData = await post<any>('/simulation/rl', chosenMeals);
      setSeries(rlData.series || null);
      // Fake a RunResult szerkezetet részleges kompatibilitáshoz (nincs DB mentés)
      const fakeRun: RunResult = {
        id: Date.now(),
        patient_id: 0,
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString(),
        finished_at: new Date().toISOString(),
        result_metrics: JSON.stringify(rlData.metrics),
        chart_path: null
      };
      setRun(fakeRun);
      setShowModal(true);
      // History nem frissül, mert RL futások nem kerülnek DB-be
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
  const simMode = 'RL-24h';

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 60px)', background: '#141a22', color: '#dde3ea', fontFamily: 'system-ui, sans-serif' }}>
      {/* Left control panel */}
      <div style={{ width: 320, borderRight: '1px solid #202a35', padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 18, background: '#1b222c' }}>
        <h2 style={{ margin: 0, fontSize: 20 }}>Szimuláció</h2>
        {role !== 'patient' && <div style={{ background: '#3a2f00', color: '#ffd666', padding: '6px 10px', borderRadius: 6, fontSize: 12 }}>Csak beteg szerep indíthat futást.</div>}
  {error && <div style={{ background: '#5a1f25', color: '#ffb3bc', padding: '8px 10px', borderRadius: 8, fontSize: 12 }}>{error}</div>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 13, fontWeight: 600 }}>Adatbázis étkezések</label>
            <div style={{ maxHeight: 150, overflowY: 'auto', border: '1px solid #2a343f', borderRadius: 10 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                <tbody>
                  {meals.map(m => (
                    <tr key={m.id} style={{ borderBottom: '1px solid #232c36' }}>
                      <td style={{ padding: '4px 6px' }}><input type="checkbox" checked={selected.has(m.id)} onChange={() => toggle(m.id)} /></td>
                      <td style={{ padding: '4px 4px', opacity: 0.65 }}>{m.timestamp.split('T').pop()}</td>
                      <td style={{ padding: '4px 4px', color: '#7db1ff' }}>{m.carbs_g}g</td>
                      <td style={{ padding: '4px 4px', opacity: 0.5 }}>{m.meal_type}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 13, fontWeight: 600 }}>Egyedi étkezések (ha van, ezek felülírják a kiválasztottakat)</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input value={newMealTime} onChange={e => setNewMealTime(e.target.value)} placeholder="HH:MM" style={{ flex: 1, background: '#242e3a', border: '1px solid #364451', color: '#fff', padding: '6px 8px', borderRadius: 8, fontSize: 12 }} />
              <input type="number" min={5} max={300} value={newMealCarbs} onChange={e => setNewMealCarbs(parseInt(e.target.value)||30)} style={{ width: 80, background: '#242e3a', border: '1px solid #364451', color: '#fff', padding: '6px 8px', borderRadius: 8, fontSize: 12 }} />
              <button onClick={addCustomMeal} style={{ background: '#3478f6', border: 'none', color: '#fff', padding: '8px 10px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }}>+</button>
            </div>
            <div style={{ maxHeight: 110, overflowY: 'auto', border: '1px solid #2a343f', borderRadius: 10 }}>
              {customMeals.length === 0 && <div style={{ padding: 8, fontSize: 11, opacity: 0.6 }}>Nincs egyedi étkezés.</div>}
              {customMeals.map(m => (
                <div key={m.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', borderBottom: '1px solid #232c36', fontSize: 11 }}>
                  <span style={{ color: '#ff9f2a' }}>{m.time}</span>
                  <span style={{ color: '#7db1ff' }}>{m.carbs}g</span>
                  <button onClick={() => removeCustomMeal(m.id)} style={{ background: '#3a4653', border: 'none', color: '#fff', padding: '2px 6px', borderRadius: 6, cursor: 'pointer' }}>x</button>
                </div>
              ))}
            </div>
            {customMeals.length > 0 && <button onClick={clearMeals} style={{ background: '#444c54', border: 'none', color: '#fff', padding: '6px 10px', borderRadius: 8, fontSize: 11, cursor: 'pointer' }}>Összes törlése</button>}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 12, background: '#273341', padding: '10px 12px', borderRadius: 10, lineHeight: 1.4 }}>
              A szimuláció mindig 24 órás RL futás (3 perces lépések), a kiválasztott vagy egyedileg megadott étkezések alapján.
            </div>
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
        <div style={{ marginTop: 'auto', fontSize: 11, opacity: 0.45 }}>v0.2 • RL engine</div>
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
          {/* Active view with interactive chart */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '20px 26px', borderBottom: '1px solid #202a35', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 15, fontWeight: 600 }}>Aktív futás</div>
              {run && <button onClick={() => setShowModal(true)} style={{ background: '#273341', border: '1px solid #364451', color: '#fff', fontSize: 12, padding: '6px 10px', borderRadius: 8, cursor: 'pointer' }}>Megnyit</button>}
            </div>
            <div style={{ flex: 1, padding: 20, display: 'flex', flexDirection: 'column', gap: 24 }}>
              {!series && <div style={{ fontSize: 13, opacity: 0.6, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>Még nincs futás – adj hozzá vagy válassz étkezéseket.</div>}
              {series && (
                <>
                  <InteractiveSimulationChart data={series} />
                  <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                    <div style={{ background: '#1f2530', padding: '12px 16px', borderRadius: 10, minWidth: 160, border: '1px solid #2a343f' }}>
                      <div style={{ fontSize: 11, opacity: 0.6 }}>Max BG</div>
                      <div style={{ fontSize: 18, fontWeight: 600, color: '#4aa3ff' }}>{(() => { const m = JSON.parse(run!.result_metrics); return Math.round(m.Max_BG); })()}</div>
                    </div>
                    <div style={{ background: '#1f2530', padding: '12px 16px', borderRadius: 10, minWidth: 160, border: '1px solid #2a343f' }}>
                      <div style={{ fontSize: 11, opacity: 0.6 }}>Min BG</div>
                      <div style={{ fontSize: 18, fontWeight: 600, color: '#ff9f2a' }}>{(() => { const m = JSON.parse(run!.result_metrics); return Math.round(m.Min_BG); })()}</div>
                    </div>
                    <div style={{ background: '#1f2530', padding: '12px 16px', borderRadius: 10, minWidth: 160, border: '1px solid #2a343f' }}>
                      <div style={{ fontSize: 11, opacity: 0.6 }}>BG Szórás</div>
                      <div style={{ fontSize: 18, fontWeight: 600, color: '#a07dff' }}>{(() => { const m = JSON.parse(run!.result_metrics); return (m.StdDev_BG).toFixed(1); })()}</div>
                    </div>
                  </div>
                </>
              )}
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
              <div><strong>Időtartam:</strong> 24h</div>
            </div>
            {/* Summary metrics cards (modal) */}
            <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 20 }}>
              <div style={{ background: '#242d37', padding: '12px 16px', borderRadius: 12, minWidth: 160, border: '1px solid #2f3b48' }}>
                <div style={{ fontSize: 11, opacity: 0.6 }}>Max BG</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: '#4aa3ff' }}>{(() => { const m = JSON.parse(run.result_metrics); return Math.round(m.Max_BG); })()}</div>
              </div>
              <div style={{ background: '#242d37', padding: '12px 16px', borderRadius: 12, minWidth: 160, border: '1px solid #2f3b48' }}>
                <div style={{ fontSize: 11, opacity: 0.6 }}>Min BG</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: '#ff9f2a' }}>{(() => { const m = JSON.parse(run.result_metrics); return Math.round(m.Min_BG); })()}</div>
              </div>
              <div style={{ background: '#242d37', padding: '12px 16px', borderRadius: 12, minWidth: 160, border: '1px solid #2f3b48' }}>
                <div style={{ fontSize: 11, opacity: 0.6 }}>BG Szórás</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: '#a07dff' }}>{(() => { const m = JSON.parse(run.result_metrics); return (m.StdDev_BG).toFixed(1); })()}</div>
              </div>
            </div>
            {series && <div style={{ marginBottom: 24 }}><InteractiveSimulationChart data={series} /></div>}
            <ChartWithMetrics runId={run.id} chartPath={run.chart_path} metricsJson={run.result_metrics} />
          </div>
        </div>
      )}
    </div>
  );
};
