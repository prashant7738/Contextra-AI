from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List

from .database import get_db, engine, Base
from . import models, schemas, crud

# Create tables (for dev only - use Alembic for prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Second Brain AI Workspace")

@app.get('/')
def root():
    return {"message": "Hello from Second Brain AI", "step": 2}

# GET all users
@app.get("/users/", response_model=List[schemas.UserResponse])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)

# GET single user
@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return crud.get_user_by_id(db, user_id)

# POST create user
@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db, user)

# DELETE user
@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    return crud.delete_user(db, user_id)