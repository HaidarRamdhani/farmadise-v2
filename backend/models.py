from sqlalchemy import Column, Integer, String, DateTime
from database import Base  # Import Base dari database.py

class Response(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True, index=True)
    tanggal = Column(DateTime, nullable=False)
    jawaban = Column(String(255), nullable=False)
    sentimen_negatif = Column(Integer, nullable=False)
    username = Column(String(50), nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
