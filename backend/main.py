from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import pytz
from database import SessionLocal, engine, Base
from models import Response, User
from sentiment import classify_sentiment
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordBearer
import bcrypt
import os

# Buat akun admin otomatis
def create_admin_account(db: Session):
    admin_username = "AdminSEC"
    admin_password = "BismillahJuara"
    admin = db.query(User).filter(User.username == admin_username).first()
    if not admin:
        password_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt())
        admin_user = User(username=admin_username, password_hash=password_hash, role="admin")
        db.add(admin_user)
        db.commit()
        print("Akun admin berhasil dibuat!")
    else:
        print("Akun admin sudah ada.")

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_admin_account(db)  # Pastikan akun admin dibuat
        yield
    finally:
        db.close()

# Initialize FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

if __name__ == "__main__":
    import uvicorn
    # Baca port dari environment variable atau gunakan default 8080
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

# Secret key untuk JWT (ganti dengan nilai random)
SECRET_KEY = "cc8168b20805ae985206d849d0c9ddd3"
ALGORITHM = "HS256"

# Model Pydantic untuk autentikasi
class UserLogin(BaseModel):
    username: str
    password: str

class ResponseCreate(BaseModel):
    jawaban: str

# Dependency database
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login/")

# Mendapatkan pengguna saat ini dari token
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Endpoint login
@app.post("/api/login/")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user.username, user.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "role": user.role}

# Endpoint untuk menyimpan respons
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

# Endpoint untuk mendapatkan semua respons
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

# Endpoint signup
@app.post("/api/signup/")
async def signup(username: str, password: str, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    new_user = User(username=username, password_hash=password_hash, role="user")
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}
