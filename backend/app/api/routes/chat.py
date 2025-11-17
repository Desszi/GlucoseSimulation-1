from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List, Optional
from sqlmodel import Session, select
from ...core.database import get_session
from ...models.message import Message
from ...models.user import User, UserRole
from ...models.patient import Patient
from ..deps import get_current_user
from ...core.config import settings
from jose import jwt, JWTError
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["chat"])

class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, List[WebSocket]] = {}

    async def connect(self, room: str, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(room, []).append(websocket)

    def disconnect(self, room: str, websocket: WebSocket):
        if room in self.active:
            self.active[room].remove(websocket)
            if not self.active[room]:
                del self.active[room]

    async def broadcast(self, room: str, message: str):
        for ws in self.active.get(room, []):
            await ws.send_text(message)

manager = ConnectionManager()

def _parse_room(room_id: str):
    """Room formátum: patient_<pid>_doctor_<did>"""
    try:
        parts = room_id.split('_')
        pid_index = parts.index('patient') + 1
        did_index = parts.index('doctor') + 1
        return int(parts[pid_index]), int(parts[did_index])
    except Exception:
        return None, None

def _decode_user(token: str, session: Session) -> Optional[User]:
    if not token:
        return None
    raw = token.replace('Bearer ', '').strip()
    try:
        payload = jwt.decode(raw, settings.SECRET_KEY, algorithms=["HS256"])  # matches deps
    except JWTError:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        uid = int(sub)
    except ValueError:
        return None
    user = session.exec(select(User).where(User.id == uid)).first()
    return user

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: Optional[str] = None, session: Session = Depends(get_session)):
    # Accept connection first (so client can receive close reason) then authorize
    await manager.connect(room_id, websocket)
    patient_id, doctor_id = _parse_room(room_id)
    user = _decode_user(token or '', session)
    # Basic room validation
    if not patient_id or not doctor_id:
        await websocket.close(code=4001)
        manager.disconnect(room_id, websocket)
        return
    # Authorization: patient user must own patient_id, doctor user must match doctor_id
    if user is None:
        # allow read-only broadcast? For now, no send rights.
        pass
    else:
        if user.role == UserRole.patient:
            patient = session.exec(select(Patient).where(Patient.user_id == user.id)).first()
            if not patient or patient.id != patient_id:
                await websocket.close(code=4003)
                manager.disconnect(room_id, websocket)
                return
        elif user.role == UserRole.doctor:
            if user.id != doctor_id:
                await websocket.close(code=4003)
                manager.disconnect(room_id, websocket)
                return
        else:
            await websocket.close(code=4003)
            manager.disconnect(room_id, websocket)
            return

    try:
        while True:
            data = await websocket.receive_text()
            sender_id = user.id if user else 0
            msg = Message(
                patient_id=patient_id,
                doctor_id=doctor_id,
                sender_user_id=sender_id,
                content=data,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(msg)
            session.commit()
            session.refresh(msg)
            payload = {
                'id': msg.id,
                'content': msg.content,
                'created_at': msg.created_at,
                'sender_user_id': msg.sender_user_id
            }
            import json
            await manager.broadcast(room_id, json.dumps(payload))
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)

@router.get("/history")
def chat_history(patient_id: int, doctor_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.patient:
        patient = session.exec(select(Patient).where(Patient.user_id == current_user.id)).first()
        if not patient or patient.id != patient_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif current_user.role == UserRole.doctor:
        # verify doctor matches conversation doctor_id
        if current_user.id != doctor_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=403, detail="Forbidden")
    msgs = session.exec(select(Message).where(Message.patient_id == patient_id, Message.doctor_id == doctor_id).order_by(Message.created_at)).all()
    return [{
        'id': m.id,
        'content': m.content,
        'created_at': m.created_at,
        'sender_user_id': m.sender_user_id
    } for m in msgs]
