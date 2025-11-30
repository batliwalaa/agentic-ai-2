from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime

class EmailCreate(BaseModel):
    recipient: EmailStr
    subject: str
    body: str

class EmailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender: EmailStr
    recipient: EmailStr
    subject: str
    body: str
    timestamp: datetime
    read: bool = Field(alias="is_read")
