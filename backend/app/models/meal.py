from typing import Optional
from sqlmodel import SQLModel, Field

class Meal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    timestamp: str  # ISO datetime
    carbs_g: int
    meal_type: str
    notes: str | None = None
