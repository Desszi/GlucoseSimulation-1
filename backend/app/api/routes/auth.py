from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ...core.database import get_session
from ...core.security import create_access_token, hash_password, verify_password
from ...models.user import User, UserRole
from ...models.patient import Patient
from ...schemas.auth import LoginRequest, RegisterRequest, Token
import logging

logger = logging.getLogger(__name__)
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
def login(data: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == data.username)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token, user_id=user.id, role=user.role.value)

@router.post("/register", response_model=Token)
def register(data: RegisterRequest, session: Session = Depends(get_session)):
    try:
        logger.info(f"Register attempt username={data.username} role={data.role}")
        existing = session.exec(select(User).where(User.username == data.username)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username taken")
        user = User(username=data.username, password_hash=hash_password(data.password), role=data.role)
        session.add(user)
        session.commit()
        session.refresh(user)
        if data.role == UserRole.patient:
            patient = Patient(user_id=user.id, taj="", full_name="", birth_date="", birth_place="", address="", insulin_type="", medications="[]")
            session.add(patient)
            session.commit()
        token = create_access_token(subject=str(user.id))
        logger.info(f"Register success user_id={user.id}")
        return Token(access_token=token, user_id=user.id, role=user.role.value)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Register failed")
        raise HTTPException(status_code=500, detail=f"Register error: {type(e).__name__}: {e}")

@router.get("/me")
def auth_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role.value}
