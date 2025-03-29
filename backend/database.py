from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# URL PostgreSQL (ganti dengan URL database Anda)
DATABASE_URL = os.getenv("DATABASE_URL")

# Inisialisasi engine
engine = create_engine(DATABASE_URL)

# Inisialisasi SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Inisialisasi Base
Base = declarative_base()
