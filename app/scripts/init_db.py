from sqlmodel import SQLModel
from app import models
from app.main import engine

def init_db():
    print("Creating tables in Neon...")
    SQLModel.metadata.create_all(engine)
    print("✅ Done.")

if __name__ == "__main__":
    init_db()
