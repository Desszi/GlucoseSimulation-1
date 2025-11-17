from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ...core.database import get_session
from ...models.meal import Meal
from ...models.patient import Patient
from ...models.user import User, UserRole
from ...schemas.meal import MealCreate, MealRead
from datetime import datetime, date
import re
from typing import List
from ..deps import get_current_user

router = APIRouter(prefix="/meals", tags=["meals"])

def get_patient_for_user(user: User, session: Session) -> Patient | None:
    return session.exec(select(Patient).where(Patient.user_id == user.id)).first()

@router.get("/", response_model=List[MealRead])
def list_meals(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    patient = get_patient_for_user(current_user, session)
    if not patient:
        return []
    meals = session.exec(select(Meal).where(Meal.patient_id == patient.id)).all()
    return meals

@router.post("/", response_model=MealRead)
def create_meal(data: MealCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    patient = get_patient_for_user(current_user, session)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile missing")
    # Timestamp normalizálás: ha csak HH:MM formátum jön, egészítsük ki mai dátummal
    ts = data.timestamp.strip()
    # Elfogadott teljes ISO kezdés: YYYY-MM-DDT...
    iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$")
    hm_pattern = re.compile(r"^\d{2}:\d{2}$")
    hms_pattern = re.compile(r"^\d{2}:\d{2}:\d{2}$")
    if hm_pattern.match(ts) or hms_pattern.match(ts):
        today = date.today().strftime('%Y-%m-%d')
        if hm_pattern.match(ts):
            ts = f"{today}T{ts}:00"
        else:  # HH:MM:SS
            ts = f"{today}T{ts}"
    elif not iso_pattern.match(ts):
        raise HTTPException(status_code=400, detail="Invalid timestamp format. Use HH:MM or YYYY-MM-DDTHH:MM[:SS]")
    meal = Meal(patient_id=patient.id, timestamp=ts, carbs_g=data.carbs_g, meal_type=data.meal_type, notes=data.notes)
    session.add(meal)
    session.commit()
    session.refresh(meal)
    return meal

@router.get("/{meal_id}", response_model=MealRead)
def get_meal(meal_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    meal = session.get(Meal, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    # ownership check
    patient = get_patient_for_user(current_user, session)
    if meal.patient_id != patient.id:
        raise HTTPException(status_code=403, detail="Not owner")
    return meal

@router.patch("/{meal_id}", response_model=MealRead)
def update_meal(meal_id: int, data: MealCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    meal = session.get(Meal, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    patient = get_patient_for_user(current_user, session)
    if meal.patient_id != patient.id:
        raise HTTPException(status_code=403, detail="Not owner")
    # apply updates (idempotent - same schema as create for simplicity)
    ts = data.timestamp.strip()
    iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$")
    hm_pattern = re.compile(r"^\d{2}:\d{2}$")
    hms_pattern = re.compile(r"^\d{2}:\d{2}:\d{2}$")
    if hm_pattern.match(ts) or hms_pattern.match(ts):
        today = date.today().strftime('%Y-%m-%d')
        if hm_pattern.match(ts):
            ts = f"{today}T{ts}:00"
        else:
            ts = f"{today}T{ts}"
    elif not iso_pattern.match(ts):
        raise HTTPException(status_code=400, detail="Invalid timestamp format. Use HH:MM or YYYY-MM-DDTHH:MM[:SS]")
    meal.timestamp = ts
    meal.carbs_g = data.carbs_g
    meal.meal_type = data.meal_type
    meal.notes = data.notes
    session.add(meal)
    session.commit()
    session.refresh(meal)
    return meal

@router.delete("/{meal_id}")
def delete_meal(meal_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    meal = session.get(Meal, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    patient = get_patient_for_user(current_user, session)
    if meal.patient_id != patient.id:
        raise HTTPException(status_code=403, detail="Not owner")
    session.delete(meal)
    session.commit()
    return {"deleted": meal_id}
