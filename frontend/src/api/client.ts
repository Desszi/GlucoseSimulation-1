import { useAuth } from '../context/AuthContext';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// Hook alapú egyszerű API kliens wrapper; komponensekben használható.
export function useApi() {
  const { token } = useAuth();
  const baseHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) baseHeaders['Authorization'] = `Bearer ${token}`;

  async function get<T>(url: string): Promise<T> {
    const resp = await fetch(url.startsWith('http') ? url : `${API_BASE}${url}`, { headers: baseHeaders });
    if (!resp.ok) {
      let detail = `${resp.status}`;
      try { const j = await resp.json(); detail = j.detail || JSON.stringify(j); } catch {}
      throw new Error(`GET ${url} - ${detail}`);
    }
    return resp.json();
  }

  async function post<T>(url: string, body: any): Promise<T> {
    const resp = await fetch(url.startsWith('http') ? url : `${API_BASE}${url}`, { method: 'POST', headers: baseHeaders, body: JSON.stringify(body) });
    if (!resp.ok) {
      let detail = `${resp.status}`;
      try { const j = await resp.json(); detail = j.detail || JSON.stringify(j); } catch {}
      throw new Error(`POST ${url} - ${detail}`);
    }
    return resp.json();
  }

  async function patch<T>(url: string, body: any): Promise<T> {
    const resp = await fetch(url.startsWith('http') ? url : `${API_BASE}${url}`, { method: 'PATCH', headers: baseHeaders, body: JSON.stringify(body) });
    if (!resp.ok) {
      let detail = `${resp.status}`;
      try { const j = await resp.json(); detail = j.detail || JSON.stringify(j); } catch {}
      throw new Error(`PATCH ${url} - ${detail}`);
    }
    return resp.json();
  }

  async function del<T = any>(url: string): Promise<T> {
    const resp = await fetch(url.startsWith('http') ? url : `${API_BASE}${url}`, { method: 'DELETE', headers: baseHeaders });
    if (!resp.ok) {
      let detail = `${resp.status}`;
      try { const j = await resp.json(); detail = j.detail || JSON.stringify(j); } catch {}
      throw new Error(`DELETE ${url} - ${detail}`);
    }
    return resp.json();
  }

  return { get, post, patch, del };
}

export interface Meal {
  id: number;
  timestamp: string;
  carbs_g: number;
  meal_type: string;
  notes?: string | null;
}

export interface MealCreateDto {
  timestamp: string;
  carbs_g: number;
  meal_type: string;
  notes?: string | null;
}
