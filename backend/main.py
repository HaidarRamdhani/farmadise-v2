from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import pytz
import os
import logging
from database import SessionLocal, engine, Base
from models import Response, User
from sentiment import classify_sentiment, detect_anomalies  # Impor fungsi detect_anomalies
from jose import JWTError, jwt
from pydantic import BaseModel, constr, field_validator
from typing import Optional
import pandas as pd
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import SQLAlchemyError
import bcrypt

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)

# Secret key untuk JWT (gunakan environment variable)
SECRET_KEY = "cc8168b20805ae985206d849d0c9ddd3"
ALGORITHM = "HS256"

# Model Pydantic untuk autentikasi
class UserLogin(BaseModel):
    username: str
    password: str

class ResponseCreate(BaseModel):
    jawaban: str

class SignUpRequest(BaseModel):
    username: constr(min_length=3, max_length=50)  # Minimal 3 karakter, maksimal 50 karakter
    password: constr(min_length=8)  # Minimal 8 karakter

    @field_validator("password")
    def validate_password(cls, value):
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit.")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter.")
        return value

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

# Buat akun admin otomatis
def create_admin_account(db: Session):
    admin_username = "AdminSEC"
    admin_password = "BismillahJuara"
    admin = db.query(User).filter(User.username == admin_username).first()
    if not admin:
        # Pastikan password hash dibuat dengan benar
        password_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt())
        admin_user = User(username=admin_username, password_hash=password_hash.decode(), role="admin")
        db.add(admin_user)
        db.commit()
        logging.info("Akun admin berhasil dibuat!")
    else:
        logging.info("Akun admin sudah ada.")

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

# Endpoint login
@app.post("/api/login/")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and generate JWT token.
    - **username**: Username of the user.
    - **password**: Password of the user.
    Returns an access token and user role.
    """
    logging.info(f"Attempting login for user: {user.username}")
    user = authenticate_user(db, user.username, user.password)
    if not user:
        logging.warning(f"Failed login attempt for user: {user.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user.username})
    logging.info(f"Successful login for user: {user.username}")
    return {"access_token": access_token, "role": user.role}

# Endpoint untuk menyimpan respons
@app.post("/api/responses/")
async def create_response(
    response: ResponseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save a new response to the database.
    - **jawaban**: The response text.
    Returns a success message if the response is saved successfully.
    """
    try:
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
    except SQLAlchemyError as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")

# Endpoint untuk mendapatkan semua respons
@app.get("/api/responses/")
async def get_responses(db: Session = Depends(get_db)):
    """
    Retrieve all responses from the database.
    Returns a list of responses with their details.
    """
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
async def signup(request: SignUpRequest, db: Session = Depends(get_db)):
    """
    Register a new user.
    - **username**: Username of the new user.
    - **password**: Password of the new user.
    Returns a success message if the user is created successfully.
    """
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt())
    new_user = User(username=request.username, password_hash=password_hash.decode(), role="user")
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

# Endpoint daily dashboard
@app.get("/api/daily-dashboard/")
async def get_daily_dashboard(db: Session = Depends(get_db)):
    """
    Retrieve daily sentiment data with anomaly detection.
    Returns a list of daily sentiment records with anomaly flags.
    """
    responses = db.query(Response).all()
    if not responses:
        return []

    # Konversi data ke DataFrame
    data = [
        {
            "tanggal": r.tanggal.date(),
            "sentimen_negatif": r.sentimen_negatif,
        } for r in responses
    ]
    df = pd.DataFrame(data)

    if df.empty:
        return []

    # Deteksi anomali
    anomalies = detect_anomalies(df.copy())
    anomalies["anomaly"] = anomalies["anomaly"].astype(int)

    # Kembalikan hasil sebagai list dictionary
    return anomalies.to_dict(orient="records")

# Handler untuk root dan favicon
@app.get("/")
async def root():
    return {"message": "Welcome to the Farmadise API!"}

@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon available."}

# Error handling global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logging.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
