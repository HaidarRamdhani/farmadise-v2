from sqlalchemy import Column, Integer, String, DateTime
from database import Base  # Import Base dari database.py

class Response(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True)
    tanggal = Column(DateTime)
    jawaban = Column(String)
    sentimen_negatif = Column(Integer)
    username = Column(String)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(String)
