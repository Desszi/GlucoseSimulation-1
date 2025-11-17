from pydantic import BaseModel
from typing import Optional

class PatientUpdate(BaseModel):
    taj: Optional[str]
    full_name: Optional[str]
    birth_date: Optional[str]
    birth_place: Optional[str]
    address: Optional[str]
    insulin_type: Optional[str]
    medications: Optional[str]

class PatientRead(BaseModel):
    id: int
    taj: str
    full_name: str
    birth_date: str
    birth_place: str
    address: str
    insulin_type: str
    medications: str
    doctor_id: Optional[int] = None
    class Config:
        from_attributes = True
