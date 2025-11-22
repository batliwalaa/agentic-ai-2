from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime, timezone
from .email_database import Base

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, default="default@demo.com")
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    is_read = Column(Boolean, default=False)
    