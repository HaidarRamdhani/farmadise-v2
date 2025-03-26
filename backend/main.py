from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import pytz
from database import SessionLocal, engine
from models import Response, User
from sentiment import classify_sentiment
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# Secret key untuk JWT (ganti dengan nilai random)
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

# Model Pydantic untuk autentikasi
class UserLogin(BaseModel):
    username: str
    password: str

class ResponseCreate(BaseModel):
    jawaban: str

# Koneksi database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Autentikasi
def verify_password(plain_password: str, password_hash: str):
    return bcrypt.checkpw(plain_password.encode(), password_hash.encode())

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return False
    return user

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

# Endpoints
@app.post("/api/login/")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user.username, user.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "role": user.role}

@app.post("/api/responses/")
async def create_response(
    response: ResponseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sentimen_negatif = classify_sentiment(response.jawaban)
    
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    db_response = Response(
        tanggal=datetime.now(jakarta_tz),
        jawaban=response.jawaban,
        sentimen_negatif=sentimen_negatif,
        username=current_user.username
    )
    db.add(db_response)
    db.commit()
    return {"status": "success"}

@app.get("/api/responses/")
async def get_responses(db: Session = Depends(get_db)):
    responses = db.query(Response).all()
    return [
        {
            "id": r.id,
            "tanggal": r.tanggal.isoformat(),
            "jawaban": r.jawaban,
            "sentimen_negatif": r.sentimen_negatif,
            "username": r.username
        } for r in responses
    ]