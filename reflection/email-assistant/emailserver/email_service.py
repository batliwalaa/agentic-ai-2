import os
import random
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from .email_database import SessionLocal, engine
from .email_models import Base, Email
from .email_schema import EmailCreate, EmailOut

# ---------------------------------------
# Lifespan
# ---------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App is starting…")
    preload_emails()
    yield
    print("App is shutting down…")

app = FastAPI(title="Email Service Simulation API", version="1.0.0", lifespan=lifespan)

# ---------------------------------------
# Middleware
# ---------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------
# Templates & Static
# ---------------------------------------
_THIS_DIR = Path(__file__).parent.resolve()
_TEMPLATES_DIR = _THIS_DIR / "templates"
_REPO_ROOT = _THIS_DIR.parent
_STATIC_CANDIDATES = [_REPO_ROOT / "static", _THIS_DIR / "static"]

for static_dir in _STATIC_CANDIDATES:
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        break

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
def serve_ui(request: Request):
    ui_email_server = os.getenv("UI_EMAIL_SERVER", "http://127.0.0.1:5000")
    ui_llm_server = os.getenv("UI_LLM_SERVER", "http://127.0.0.1:5001")
    return templates.TemplateResponse("ui_all.html", {
        "request": request,
        "UI_EMAIL_SERVER": ui_email_server,
        "UI_LLM_RESPONSE": ui_llm_server
    })

# ---------------------------------------
# Database
# ---------------------------------------
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def preload_emails():
    db = SessionLocal()
    try:
        db.execute(delete(Email))
        db.commit()
        now = datetime.now(timezone.utc)
        samples = [
            Email(sender="boss@email.com", recipient="you@email.com",
                  subject="Quarterly Report", body="Please finalize the report ASAP.",
                  timestamp=now, is_read=False),
            Email(sender="alice@work.com", recipient="you@email.com",
                  subject="Lunch?", body="Free for lunch today?",
                  timestamp=now, is_read=False),
            Email(sender="bob@work.com", recipient="you@email.com",
                  subject="Code Review", body="I left some comments on your PR.",
                  timestamp=now, is_read=False),
            Email(sender="charlie@work.com", recipient="you@email.com",
                  subject="Meeting", body="Can we reschedule?",
                  timestamp=now, is_read=False),
            Email(sender="eric@work.com", recipient="you@email.com",
                  subject="Happy Hour", body="We're planning drinks this Friday!",
                  timestamp=now, is_read=False),
            Email(sender="you@mail.com", recipient="boss@email.com",
                  subject="Days off", body="Can I get some days off next week?",
                  timestamp=now, is_read=False),
        ]
        random.shuffle(samples)
        db.add_all(samples)
        db.commit()
    finally:
        db.close()

# ---------------------------------------
# Email Endpoints
# ---------------------------------------

@app.post("/send/", response_model=EmailOut)
def send_email(email: EmailCreate, db: Session = Depends(get_db)):
    db_email = Email(
        recipient=email.recipient,
        subject=email.subject,
        body=email.body,
        timestamp=datetime.now(timezone.utc),
        sender="you@email.com"
    )
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email

@app.get("/emails/filter/", response_model=List[EmailOut])
def filter_emails(
    recipient: Optional[str] = Query(None, description="Filter by recipient email address (optional)"),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD (optional)"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD (optional)"),
    db: Session = Depends(get_db)
):
    query = db.query(Email)
    if recipient:
        query = query.filter(Email.recipient == recipient)
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Email.timestamp >= date_from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Email.timestamp <= date_to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
    emails = query.order_by(Email.timestamp.desc()).all()
    return emails

@app.get("/emails/unread/", response_model=List[EmailOut])
def get_unread_email(db: Session = Depends(get_db)):
    return db.query(Email).filter(Email.is_read == False).order_by(Email.timestamp.desc()).all()

@app.get("/emails/search/", response_model=List[EmailOut])
def search_emails(
    query: str = Query(..., description="Keyword to search in subject/body/sender"),
    db: Session = Depends(get_db)
):
    emails = db.query(Email).filter(
        (Email.subject.ilike(f"%{query}%")) |
        (Email.body.ilike(f"%{query}%")) |
        (Email.sender.ilike(f"%{query}%"))
    ).order_by(Email.timestamp.desc()).all()
    return emails

@app.get("/emails/", response_model=List[EmailOut])
def get_emails(db: Session = Depends(get_db)):
    return db.query(Email).order_by(Email.timestamp.desc()).all()

@app.get("/emails/{email_id}/", response_model=EmailOut)
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email

@app.patch("/emails/{email_id}/read/", response_model=EmailOut)
def mark_email_as_read(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    email.is_read = True
    db.commit()
    db.refresh(email)
    return email

@app.patch("/emails/{email_id}/unread/", response_model=EmailOut)
def mark_email_as_unread(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    email.is_read = False
    db.commit()
    db.refresh(email)
    return email

@app.delete("/emails/{email_id}/", response_model=dict)
def delete_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    db.delete(email)
    db.commit()
    return {"message": "Email deleted successfully"}

# ---------------------------------------
# Utility Endpoints
# ---------------------------------------
@app.get("/health/", response_model=dict)
def health_check():
    return {"status": "ok"}

@app.get("/reset/", response_model=dict)
def reset_database(db: Session = Depends(get_db)):
    preload_emails()
    return {"message": "Database reset successfully"}
