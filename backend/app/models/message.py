from typing import Optional
from sqlmodel import SQLModel, Field

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    doctor_id: int = Field(foreign_key="user.id")
    sender_user_id: int = Field(foreign_key="user.id")
    content: str
    created_at: str
