import React, { useEffect, useRef, useState, KeyboardEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { useApi } from '../api/client';

interface ChatMessage {
  id?: number;
  content: string;
  created_at: string;
  sender_user_id: number;
}

// MVP: manuális patient_id és doctor_id megadás (később dinamikusan orvos választásból)
export const ChatPage: React.FC = () => {
  const { userId, role, token } = useAuth();
  const { get } = useApi();
  const [patientId, setPatientId] = useState<number>(0);
  const [doctorId, setDoctorId] = useState<number>(0);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function loadHistory(pid: number, did: number) {
    try {
      const data = await get<ChatMessage[]>(`/chat/history?patient_id=${pid}&doctor_id=${did}`);
      setMessages(data);
    } catch (e: any) {
      setError(e.message);
    }
  }

  function connect() {
    if (!patientId || !doctorId) {
      setError('Adj meg patient_id és doctor_id értékeket');
      return;
    }
    setError(null);
    loadHistory(patientId, doctorId);
    const room = `patient_${patientId}_doctor_${doctorId}`;
    const wsUrl = `ws://localhost:8000/chat/ws/${room}?token=${encodeURIComponent(token || '')}`;
    const socket = new WebSocket(wsUrl);
    socket.onmessage = (evt) => {
      try {
        const parsed = JSON.parse(evt.data);
        const msg: ChatMessage = {
          id: parsed.id,
          content: parsed.content,
          created_at: parsed.created_at,
          sender_user_id: parsed.sender_user_id
        };
        setMessages(m => [...m, msg]);
      } catch {
        // fallback plain text
        const msg: ChatMessage = { content: evt.data, created_at: new Date().toISOString(), sender_user_id: 0 };
        setMessages(m => [...m, msg]);
      }
    };
    socket.onerror = () => setError('WebSocket hiba');
    socket.onclose = () => setWs(null);
    setWs(socket);
  }

  function sendMessage() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const text = input.trim();
    if (!text) return;
    ws.send(text);
    setInput('');
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage();
    }
  }

  // Auto-init IDs for common pairing (demo): if role === patient and we have doctor assigned later fetch; for now manual.
  useEffect(() => {
    // Simple heuristic: if patient set patientId=userId; if doctor set doctorId=userId
    if (role === 'patient' && userId) setPatientId(prev => prev || userId);
    if (role === 'doctor' && userId) setDoctorId(prev => prev || userId);
  }, [role, userId]);

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 60px)', background: '#1b222c', color: '#e6e9ed' }}>
      {/* Sidebar */}
      <div style={{ width: 260, borderRight: '1px solid #2d3642', padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <h2 style={{ margin: 0, fontSize: 20 }}>Chat</h2>
        <div style={{ fontSize: 12, opacity: 0.8 }}>Szerep: {role} • User ID: {userId}</div>
        {error && <div style={{ background: '#662c2c', padding: '6px 8px', borderRadius: 6, fontSize: 12 }}>{error}</div>}
        <label style={{ fontSize: 13, display: 'flex', flexDirection: 'column', gap: 4 }}>Patient ID
          <input disabled={role === 'patient'} type="number" value={patientId} onChange={e => setPatientId(parseInt(e.target.value, 10) || 0)} style={{ background: '#242e3a', border: '1px solid #3a4654', color: '#fff', padding: '6px 8px', borderRadius: 6, opacity: role === 'patient' ? .6 : 1 }} />
        </label>
        <label style={{ fontSize: 13, display: 'flex', flexDirection: 'column', gap: 4 }}>Doctor ID
          <input disabled={role === 'doctor'} type="number" value={doctorId} onChange={e => setDoctorId(parseInt(e.target.value, 10) || 0)} style={{ background: '#242e3a', border: '1px solid #3a4654', color: '#fff', padding: '6px 8px', borderRadius: 6, opacity: role === 'doctor' ? .6 : 1 }} />
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={connect} disabled={!!ws} style={{ flex: 1, background: '#3478f6', border: 'none', color: '#fff', padding: '8px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>Kapcsolódás</button>
          <button onClick={() => ws?.close()} disabled={!ws} style={{ flex: 1, background: '#49525d', border: 'none', color: '#fff', padding: '8px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>Bontás</button>
        </div>
        <div style={{ fontSize: 12, lineHeight: 1.4, opacity: 0.7 }}>
          <p style={{ margin: 0 }}>WS token param használatával azonosítja a küldőt.</p>
          <p style={{ margin: '6px 0 0' }}>A buborék színe jelzi: kék = saját, szürke = másik fél.</p>
        </div>
      </div>
      {/* Main chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {messages.map((m, idx) => {
            const mine = m.sender_user_id === userId;
            const senderLabel = mine ? (role === 'doctor' ? 'Én (Doktor)' : 'Én') : (m.sender_user_id === 0 ? 'Ismeretlen' : m.sender_user_id === doctorId ? 'Doktor' : 'Beteg');
            return (
              <div key={m.id || idx} style={{ display: 'flex', justifyContent: mine ? 'flex-end' : 'flex-start' }}>
                <div style={{ maxWidth: '62%', background: mine ? '#3478f6' : '#2b3440', padding: '10px 14px', borderRadius: mine ? '16px 16px 4px 16px' : '16px 16px 16px 4px', fontSize: 13, boxShadow: '0 2px 6px rgba(0,0,0,0.35)', position: 'relative' }}>
                  <div style={{ fontSize: 10, opacity: 0.65, marginBottom: 4, display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <span>{senderLabel}</span>
                    <span>{new Date(m.created_at).toLocaleTimeString()}</span>
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
                </div>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
        <div style={{ padding: '14px 24px', borderTop: '1px solid #2d3642', display: 'flex', gap: 12, background: '#202a35' }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder={ws ? 'Írj egy üzenetet...' : 'Csatlakozz a szobához előbb'}
            style={{ flex: 1, background: '#242e3a', border: '1px solid #3a4654', color: '#fff', padding: '10px 12px', borderRadius: 8, fontSize: 13 }}
          />
          <button onClick={sendMessage} disabled={!ws} style={{ background: '#3478f6', border: 'none', color: '#fff', padding: '10px 18px', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>Küld</button>
        </div>
      </div>
    </div>
  );
};
