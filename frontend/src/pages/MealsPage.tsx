import React, { useEffect, useState } from 'react';
import { useApi, Meal, MealCreateDto } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { theme } from '../theme';

export const MealsPage: React.FC = () => {
  const { get, post, patch, del } = useApi();
  const { role } = useAuth();
  const [meals, setMeals] = useState<Meal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<MealCreateDto>({ timestamp: '', carbs_g: 0, meal_type: '', notes: '' });
  const [editingId, setEditingId] = useState<number | null>(null);

  async function loadMeals() {
    setLoading(true);
    setError(null);
    try {
      const data = await get<Meal[]>('/meals/');
      setMeals(data);
    } catch (e: any) {
      if (e.message?.includes('Not a patient user')) {
        // Ne jelenítsünk meg piros hibát, csak hagyjuk üres listán.
        setError(null);
        setMeals([]);
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadMeals(); }, []);

  function updateForm<K extends keyof MealCreateDto>(key: K, value: MealCreateDto[K]) {
    setForm(f => ({ ...f, [key]: value }));
  }

  function normalizeTimestamp(raw: string): string {
    const v = raw.trim();
    if (!v) return '';
    // Accept HH:MM -> today
    if (/^\d{1,2}:\d{2}$/.test(v)) {
      const now = new Date();
      const [h, m] = v.split(':');
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      return `${yyyy}-${mm}-${dd}T${h.padStart(2,'0')}:${m}:00`;
    }
    // Accept YYYY-MM-DD HH:MM -> convert to ISO (space separated)
    if (/^\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}$/.test(v)) {
      const [d, hm] = v.split(' ');
      const [h, m] = hm.split(':');
      return `${d}T${h.padStart(2,'0')}:${m}:00`;
    }
    // Accept YYYY.MM.DD HH:MM (localized placeholder) -> convert
    if (/^\d{4}\.\d{2}\.\d{2} \d{1,2}:\d{2}$/.test(v)) {
      const [d, hm] = v.split(' ');
      const [yyyy, mo, da] = d.split('.');
      const [h, m] = hm.split(':');
      return `${yyyy}-${mo}-${da}T${h.padStart(2,'0')}:${m}:00`;
    }
    // Accept YYYY-MM-DDTHH:MM (without seconds)
    if (/^\d{4}-\d{2}-\d{2}T\d{1,2}:\d{2}$/.test(v)) {
      return v + ':00';
    }
    // If already looks like ISO with seconds just return
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(v)) return v;
    return v; // fallback
  }

  function formatDisplay(ts: string): string {
    try {
      const d = new Date(ts);
      if (isNaN(d.getTime())) return ts;
      return d.toLocaleString('hu-HU', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit'
      });
    } catch { return ts; }
  }

  async function submitNew(e: React.FormEvent) {
    e.preventDefault();
    try {
      const payload = { ...form, timestamp: normalizeTimestamp(form.timestamp) };
      const created = await post<Meal>('/meals/', payload);
      setMeals(m => [...m, created]);
      setForm({ timestamp: '', carbs_g: 0, meal_type: '', notes: '' });
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function submitEdit(e: React.FormEvent) {
    e.preventDefault();
    if (editingId == null) return;
    try {
      const payload = { ...form, timestamp: normalizeTimestamp(form.timestamp) };
      const updated = await patch<Meal>(`/meals/${editingId}`, payload);
      setMeals(m => m.map(x => x.id === editingId ? updated : x));
      setEditingId(null);
      setForm({ timestamp: '', carbs_g: 0, meal_type: '', notes: '' });
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function removeMeal(id: number) {
    if (!confirm('Törlöd ezt az étkezést?')) return;
    try {
      await del(`/meals/${id}`);
      setMeals(m => m.filter(x => x.id !== id));
    } catch (e: any) {
      setError(e.message);
    }
  }

  function startEdit(meal: Meal) {
    setEditingId(meal.id);
    setForm({ timestamp: meal.timestamp, carbs_g: meal.carbs_g, meal_type: meal.meal_type, notes: meal.notes || '' });
  }

  return (
    <div style={{ padding: 8 }}>
      <h2 style={{ marginTop: 0, fontSize: 26, letterSpacing: '.5px', color: theme.colors.text }}>Étkezések</h2>
      {role !== 'patient' && <div style={{ color: 'orange' }}>Csak beteg szerep módosíthatja az étkezéseket.</div>}
  {error && <div style={{ background: theme.colors.panelAlt, color: theme.colors.danger, padding: '8px 12px', borderRadius: theme.radius.sm }}>{error}</div>}
      <div style={{ display: 'flex', gap: 32, alignItems: 'flex-start', marginTop: 16 }}>
        <div style={{ flex: 2, background: theme.colors.panel, padding: 20, borderRadius: theme.radius.md, boxShadow: theme.shadow }}>
          {loading ? <div style={{ color: theme.colors.textDim }}>Betöltés...</div> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={thStyle}>Időpont</th>
                  <th style={thStyle}>CH (g)</th>
                  <th style={thStyle}>Típus</th>
                  <th style={thStyle}>Megjegyzés</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {meals.map(m => (
                  <tr key={m.id}>
                    <td style={tdStyle}>{formatDisplay(m.timestamp)}</td>
                    <td style={tdStyle}>{m.carbs_g}</td>
                    <td style={tdStyle}>{m.meal_type}</td>
                    <td style={tdStyle}>{m.notes}</td>
                    <td>
                      {role === 'patient' && (
                        <>
                          <button onClick={() => startEdit(m)} style={smallBtn}>Szerk</button>
                          <button onClick={() => removeMeal(m.id)} style={smallBtn}>Törlés</button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div style={{ flex: 1, background: theme.colors.panel, padding: 20, borderRadius: theme.radius.md, boxShadow: theme.shadow }}>
          <h3 style={{ marginTop: 0 }}>{editingId ? 'Étel szerkesztése' : 'Új étel'}</h3>
          <form onSubmit={editingId ? submitEdit : submitNew} style={{ fontSize: 13 }}>
            <div style={{ marginBottom: 8 }}>
              <label>Időpont</label><br />
              <input
                value={form.timestamp}
                onChange={e => updateForm('timestamp', e.target.value)}
                required
                style={inputStyle}
                placeholder={new Date().toLocaleString('hu-HU', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(',', '')}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label>CH (g)</label><br />
              <input type="number" value={form.carbs_g} onChange={e => updateForm('carbs_g', parseInt(e.target.value, 10) || 0)} required style={inputStyle} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label>Típus</label><br />
              <input value={form.meal_type} onChange={e => updateForm('meal_type', e.target.value)} required style={inputStyle} placeholder="reggeli" />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label>Megjegyzés</label><br />
              <textarea value={form.notes} onChange={e => updateForm('notes', e.target.value)} style={{ ...inputStyle, minHeight: 60 }} />
            </div>
            <button type="submit" style={submitBtn}>{editingId ? 'Mentés' : 'Hozzáadás'}</button>
            {editingId && <button type="button" onClick={() => { setEditingId(null); setForm({ timestamp: '', carbs_g: 0, meal_type: '', notes: '' }); }} style={cancelBtn}>Mégse</button>}
          </form>
        </div>
      </div>
    </div>
  );
};

const thStyle: React.CSSProperties = { borderBottom: '1px solid #24324a', textAlign: 'left', padding: '6px 6px', color: theme.colors.textDim, fontWeight: 500 };
const tdStyle: React.CSSProperties = { borderBottom: '1px solid #24324a', padding: '6px 6px', color: theme.colors.text };
const smallBtn: React.CSSProperties = { background: theme.colors.panelAlt, color: theme.colors.text, border: 'none', padding: '4px 8px', borderRadius: theme.radius.sm, cursor: 'pointer', fontSize: 11, marginRight: 4 };
const submitBtn: React.CSSProperties = { width: '100%', background: theme.colors.primary, color: theme.colors.text, border: 'none', padding: '10px 14px', borderRadius: theme.radius.sm, cursor: 'pointer', fontWeight: 600, letterSpacing: '.5px' };
const cancelBtn: React.CSSProperties = { width: '100%', background: theme.colors.panelAlt, color: theme.colors.textDim, border: 'none', padding: '8px 12px', borderRadius: theme.radius.sm, cursor: 'pointer', marginTop: 8 };
const inputStyle: React.CSSProperties = { width: '100%', padding: '8px 10px', background: theme.colors.panelAlt, border: `1px solid ${theme.colors.border}`, color: theme.colors.text, borderRadius: theme.radius.sm };
