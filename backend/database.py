import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Ambil DATABASE_URL dari environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

print(f"Using DATABASE_URL: {DATABASE_URL}")

# Inisialisasi engine
engine = create_engine(DATABASE_URL)

# Inisialisasi SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Inisialisasi Base
Base = declarative_base()
