from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from auth.dependencies import (
    get_current_user, get_db,
    authenticate_user,
    create_access_token,
    get_user,
)
from auth.models import Token
from auth.schemas import UpdateAPIToken, UserBase, UserCreate, UserResponse
from chatbot.models import User
from auth.utils import (
    encrypt_api_key,
    get_password_hash,
    get_secret_key_from_env,
)

router = APIRouter()


@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "id": db_user.id, "username": db_user.username}


@router.post("/update_api_token")
def update_api_token(received_user: UpdateAPIToken,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):

    secret_key = get_secret_key_from_env()
    fernet = Fernet(secret_key)
    encrypted_token = encrypt_api_key(received_user.api_token, fernet)

    current_user.hashed_api_key = encrypted_token

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {"status": "API Token updated."}
