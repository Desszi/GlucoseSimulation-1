from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ...core.database import get_session
from ...models.patient import Patient
from ...models.user import User, UserRole
from ...schemas.patient import PatientUpdate, PatientRead
from ..deps import get_current_user

router = APIRouter(prefix="/patients", tags=["patients"])

def ensure_patient_profile(user: User, session: Session) -> Patient:
    patient = session.exec(select(Patient).where(Patient.user_id == user.id)).first()
    if not patient:
        # lazán létrehozunk üres profilt ha hiányzik
        patient = Patient(user_id=user.id, taj="", full_name="", birth_date="", birth_place="", address="", insulin_type="", medications="[]")
        session.add(patient)
        session.commit()
        session.refresh(patient)
    return patient

@router.get("/me", response_model=PatientRead)
def read_me(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    patient = ensure_patient_profile(current_user, session)
    return patient

@router.patch("/me", response_model=PatientRead)
def update_me(data: PatientUpdate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    patient = ensure_patient_profile(current_user, session)
    update_data = data.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(patient, k, v)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient

@router.post("/assign/{patient_id}", response_model=PatientRead)
def assign_doctor(patient_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Doktor hozzárendelése egy beteghez. Csak doctor szerep hívhatja."""
    if current_user.role != UserRole.doctor:
        raise HTTPException(status_code=403, detail="Not a doctor user")
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    # Ha már másik doktorhoz rendelve, egyszerűen felülírjuk (később audit log)
    patient.doctor_id = current_user.id
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient

@router.get("/", response_model=list[PatientRead])
def list_patients(session: Session = Depends(get_session), current_user: User = Depends(get_current_user), only_assigned: bool = False):
    """Listázza a betegeket. Doctor szerep: minden beteg, vagy csak hozzárendelt (only_assigned). Patient: csak saját profil."""
    if current_user.role == UserRole.patient:
        patient = session.exec(select(Patient).where(Patient.user_id == current_user.id)).first()
        return [patient] if patient else []
    if current_user.role == UserRole.doctor:
        stmt = select(Patient)
        if only_assigned:
            stmt = stmt.where(Patient.doctor_id == current_user.id)
        return session.exec(stmt).all()
    raise HTTPException(status_code=403, detail="Forbidden")

@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    # Patient saját magát, doctor bárkit (MVP – később korlátozás) 
    if current_user.role == UserRole.patient:
        own = session.exec(select(Patient).where(Patient.user_id == current_user.id)).first()
        if not own or own.id != patient.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif current_user.role != UserRole.doctor:
        raise HTTPException(status_code=403, detail="Forbidden")
    return patient

@router.get("/doctor/patients", response_model=list[PatientRead])
def doctor_patients(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.doctor:
        raise HTTPException(status_code=403, detail="Not a doctor user")
    pts = session.exec(select(Patient).where(Patient.doctor_id == current_user.id)).all()
    return pts

@router.post("/unassign/{patient_id}", response_model=PatientRead)
def unassign_doctor(patient_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.doctor:
        raise HTTPException(status_code=403, detail="Not a doctor user")
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this doctor")
    patient.doctor_id = None
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient
