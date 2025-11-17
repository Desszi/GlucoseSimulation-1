from pydantic import BaseModel

class MessageCreate(BaseModel):
    patient_id: int
    doctor_id: int
    content: str

class MessageRead(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    sender_user_id: int
    content: str
    created_at: str
    class Config:
        from_attributes = True
