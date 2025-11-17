import React, { useEffect, useState } from 'react';
import { useApi } from '../api/client';

interface MetricsMap { [k: string]: any }

interface Props {
  runId: number;
  chartPath?: string | null;
  metricsJson?: string; // optional pre-fetched JSON string
}

export const ChartWithMetrics: React.FC<Props> = ({ runId, chartPath, metricsJson }) => {
  const { get } = useApi();
  const [metrics, setMetrics] = useState<MetricsMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      if (metricsJson) {
        try { setMetrics(JSON.parse(metricsJson)); } catch { setMetrics(null); }
        return;
      }
      setLoading(true);
      setError(null);
      try {
        // Nincs külön metrics endpoint; a SimulationRun rekordban JSON stringként jön.
        // Ha a parent nem adta át, akkor szükség esetén újra lekérjük a run-t.
        const run = await get<any>(`/simulation/runs/${runId}`);
        try { setMetrics(JSON.parse(run.result_metrics)); } catch { setMetrics(null); }
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [runId, metricsJson]);

  return (
    <div style={{ border: '1px solid #ddd', padding: 16, borderRadius: 8 }}>
      <h4>BG Diagram & Metrikák</h4>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {loading && <div>Betöltés...</div>}
      {chartPath ? (
        <div style={{ marginBottom: 12 }}>
          <img src={`/simulation/runs/${runId}/chart`} alt="BG Chart" style={{ maxWidth: '100%' }} />
        </div>
      ) : (
        <div>Nincs chart elérhető.</div>
      )}
      {metrics && (
        <table style={{ width: '100%', fontSize: 14 }}>
          <tbody>
            {Object.entries(metrics).map(([k,v]) => (
              <tr key={k}>
                <td style={{ fontWeight: 500 }}>{k}</td>
                <td>{String(v)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
