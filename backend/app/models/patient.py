from typing import Optional
from sqlmodel import SQLModel, Field

class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    doctor_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    taj: str = Field(index=True)
    full_name: str
    birth_date: str
    birth_place: str
    address: str
    insulin_type: str
    medications: str  # JSON string serialized
