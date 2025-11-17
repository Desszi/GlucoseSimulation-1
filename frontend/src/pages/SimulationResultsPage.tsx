import React, { useEffect, useState } from 'react';
import { useApi } from '../api/client';
import { ChartWithMetrics } from '../components/ChartWithMetrics';

interface RunRec {
  id: number;
  patient_id: number;
  created_at: string;
  started_at: string;
  finished_at: string;
  result_metrics: string;
  chart_path?: string | null;
}

export const SimulationResultsPage: React.FC = () => {
  const { get } = useApi();
  const [runs, setRuns] = useState<RunRec[]>([]);
  const [selected, setSelected] = useState<RunRec | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadRuns() {
    setLoading(true);
    setError(null);
    try {
      const data = await get<RunRec[]>('/simulation/runs');
      setRuns(data);
      if (data.length && !selected) setSelected(data[0]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadRuns(); }, []);

  return (
    <div style={{ padding: 24 }}>
      <h2>Korábbi szimulációk</h2>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {loading && <div>Betöltés...</div>}
      <div style={{ display: 'flex', gap: 32, alignItems: 'flex-start' }}>
        <div style={{ flex: 2 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>ID</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>Létrehozva</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>Kezdés</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>Befejezés</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(r => (
                <tr key={r.id} style={{ cursor: 'pointer', background: selected?.id === r.id ? '#f5f5f5' : undefined }} onClick={() => setSelected(r)}>
                  <td>{r.id}</td>
                  <td>{r.created_at}</td>
                  <td>{r.started_at}</td>
                  <td>{r.finished_at}</td>
                </tr>
              ))}
              {!runs.length && !loading && (
                <tr><td colSpan={4}>Nincs futás.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div style={{ flex: 1 }}>
          {selected ? (
            <ChartWithMetrics runId={selected.id} chartPath={selected.chart_path} metricsJson={selected.result_metrics} />
          ) : (
            <div>Nincs kiválasztott futás.</div>
          )}
        </div>
      </div>
    </div>
  );
};
