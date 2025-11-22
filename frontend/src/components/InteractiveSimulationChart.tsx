import React from 'react';
import { ComposedChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Scatter, Bar, Legend, ReferenceLine } from 'recharts';

export interface SimulationPoint {
  time: string; // HH:MM
  bg: number;
  dose: number;
  meal: number;
}

interface Props {
  data: SimulationPoint[];
}

// Split dose and meal markers for layered charts
export const InteractiveSimulationChart: React.FC<Props> = ({ data }) => {
  // Enrich data with numeric hour for uniform 0-24 axis
  const enriched = data.map(d => {
    // Expect HH:MM string; fallback to 00:00 if malformed
    let hour = 0;
    let minute = 0;
    if (/^\d{2}:\d{2}$/.test(d.time)) {
      const [h, m] = d.time.split(':');
      hour = parseInt(h, 10) || 0;
      minute = parseInt(m, 10) || 0;
    }
    const hourFloat = hour + minute/60;
    return { ...d, hourFloat };
  });
  // Derived arrays for markers
  const mealPoints = enriched.filter(d => d.meal > 0).map(d => ({ ...d, mealSize: d.meal }));
  const dosePoints = enriched.filter(d => d.dose > 0).map(d => ({ ...d }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;
    const point = payload[0].payload as SimulationPoint;
    return (
      <div style={{ background: '#1f2a33', border: '1px solid #2e3d4a', padding: '8px 10px', borderRadius: 8, fontSize: 12, minWidth: 140 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Idő {point.time}</div>
        <div>BG: <strong style={{ color: '#4aa3ff' }}>{point.bg.toFixed(1)}</strong> mg/dL</div>
        {point.dose > 0 && <div>Inzulin: <strong style={{ color: '#7dffc7' }}>{point.dose.toFixed(2)}</strong> U</div>}
        {point.meal > 0 && <div>Étkezés: <strong style={{ color: '#ff9f2a' }}>{point.meal}g</strong> CH</div>}
      </div>
    );
  };

  return (
    <div style={{ width: '100%', height: 420 }}>
      <ResponsiveContainer>
        <ComposedChart data={enriched} margin={{ top: 25, right: 30, left: 10, bottom: 25 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#23313e" />
          <XAxis
            dataKey="hourFloat"
            type="number"
            domain={[0, 24]}
            ticks={[0,2,4,6,8,10,12,14,16,18,20,22,24]}
            tickFormatter={(v) => {
              const h = Math.floor(v);
              const m = Math.round((v - h) * 60);
              return `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}`;
            }}
            tick={{ fill: '#b9c4cf', fontSize: 11 }}
            label={{ value: 'Idő (óra)', position: 'insideBottom', offset: -10, fill: '#b9c4cf', fontSize: 12 }}
          />
          <YAxis yAxisId="bg" domain={[40, 'dataMax + 30']} tick={{ fill: '#b9c4cf', fontSize: 11 }} label={{ value: 'BG (mg/dL)', angle: -90, position: 'insideLeft', fill: '#b9c4cf' }} />
            <YAxis yAxisId="dose" orientation="right" tick={{ fill: '#b9c4cf', fontSize: 11 }} label={{ value: 'Insulin (U)', angle: -90, position: 'insideRight', fill: '#b9c4cf' }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {/* Reference horizontal lines for target range (pl. 70-180 mg/dL) */}
          <ReferenceLine yAxisId="bg" y={70} stroke="#2e8b57" strokeDasharray="4 4" label={{ value: '70', fill: '#2e8b57', fontSize: 10 }} />
          <ReferenceLine yAxisId="bg" y={180} stroke="#ff6363" strokeDasharray="4 4" label={{ value: '180', fill: '#ff6363', fontSize: 10 }} />
          {/* Hourly faint vertical lines */}
          {Array.from({ length: 25 }).map((_, i) => (
            <ReferenceLine key={i} x={i} stroke="#1f2b36" strokeDasharray="1 6" ifOverflow="extendDomain" />
          ))}
          {/* Meal event markers as scatter */}
          <Line yAxisId="bg" type="monotone" dataKey="bg" stroke="#4aa3ff" strokeWidth={2} dot={false} name="BG" />
          <Bar yAxisId="dose" dataKey="dose" fill="#7dffc7" name="Inzulin" />
          <Scatter yAxisId="bg" data={mealPoints} fill="#ff9f2a" name="Étkezések" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};
