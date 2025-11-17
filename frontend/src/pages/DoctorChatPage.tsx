import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useApi } from '../api/client';

interface ChatMessage {
  id?: number;
  content: string;
  created_at: string;
  sender_user_id: number;
}

export const DoctorChatPage: React.FC = () => {
  const { role, userId, token } = useAuth();
  const { get } = useApi();
  const [patientId, setPatientId] = useState<number>(0);
  const [doctorId, setDoctorId] = useState<number>(0);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  async function loadHistory(pid: number, did: number) {
    try {
      const data = await get<ChatMessage[]>(`/chat/history?patient_id=${pid}&doctor_id=${did}`);
      setMessages(data);
    } catch (e: any) {
      setError(e.message);
    }
  }

  function connect() {
    if (!patientId || !doctorId) { setError('Adj meg patient_id és doctor_id'); return; }
    setError(null);
    loadHistory(patientId, doctorId);
    const room = `patient_${patientId}_doctor_${doctorId}`;
    const wsUrl = `ws://localhost:8000/chat/ws/${room}?token=${encodeURIComponent(token || '')}`;
    const socket = new WebSocket(wsUrl);
    socket.onmessage = evt => {
      try {
        const parsed = JSON.parse(evt.data);
        const msg: ChatMessage = { id: parsed.id, content: parsed.content, created_at: parsed.created_at, sender_user_id: parsed.sender_user_id };
        setMessages(m => [...m, msg]);
      } catch {
        const fallback: ChatMessage = { content: evt.data, created_at: new Date().toISOString(), sender_user_id: 0 };
        setMessages(m => [...m, fallback]);
      }
    };
    socket.onerror = () => setError('WebSocket hiba');
    socket.onclose = () => setWs(null);
    setWs(socket);
  }

  function sendMessage() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const txt = input.trim();
    if (!txt) return;
    ws.send(txt);
    setInput('');
  }

  return (
    <div style={{ padding: 24 }}>
      <h2>Orvos - Chat</h2>
      {role !== 'doctor' && <div style={{ color: 'orange' }}>Csak doctor szerep számára releváns.</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <div style={{ display: 'flex', gap: 32 }}>
        <div style={{ flex: 1 }}>
          <div style={{ marginBottom: 8 }}>
            <label>Patient ID</label><br />
            <input type="number" value={patientId} onChange={e => setPatientId(parseInt(e.target.value, 10) || 0)} />
          </div>
          <div style={{ marginBottom: 8 }}>
            <label>Doctor ID</label><br />
            <input type="number" value={doctorId} onChange={e => setDoctorId(parseInt(e.target.value, 10) || 0)} />
          </div>
          <button onClick={connect} disabled={!!ws} style={{ padding: '6px 12px' }}>Kapcsolódás</button>
          <button onClick={() => ws?.close()} disabled={!ws} style={{ padding: '6px 12px', marginLeft: 8 }}>Bontás</button>
          <div style={{ marginTop: 16, height: 320, overflowY: 'auto', border: '1px solid #2f3a46', padding: 12, background: '#1b222c', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {messages.map((m, idx) => {
              const mine = m.sender_user_id === userId;
              const senderLabel = mine ? 'Én (Doktor)' : (m.sender_user_id === patientId ? 'Beteg' : m.sender_user_id === 0 ? 'Ismeretlen' : `User ${m.sender_user_id}`);
              return (
                <div key={m.id || idx} style={{ display: 'flex', justifyContent: mine ? 'flex-end' : 'flex-start' }}>
                  <div style={{ maxWidth: '65%', background: mine ? '#3478f6' : '#2b3440', padding: '8px 12px', borderRadius: mine ? '16px 16px 4px 16px' : '16px 16px 16px 4px', fontSize: 12, boxShadow: '0 2px 6px rgba(0,0,0,.35)' }}>
                    <div style={{ fontSize: 9, opacity: .65, marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
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
          <div style={{ marginTop: 10, display: 'flex', gap: 10 }}>
            <input value={input} onChange={e => setInput(e.target.value)} placeholder={ws ? 'Írj üzenetet...' : 'Kapcsolódj előbb'} style={{ flex: 1, background: '#242e3a', border: '1px solid #3a4654', color: '#fff', padding: '8px 10px', borderRadius: 8, fontSize: 13 }} />
            <button onClick={sendMessage} disabled={!ws} style={{ background: '#3478f6', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>Küld</button>
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <h4>Megjegyzések</h4>
          <ul style={{ fontSize: 13, lineHeight: 1.4 }}>
            <li>MVP: WebSocket autentikáció még nincs.</li>
            <li>Később: orvoshoz rendelt beteg lista, jogosultság ellenőrzés.</li>
            <li>Különböző szobák kezelésének UI-ja.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
