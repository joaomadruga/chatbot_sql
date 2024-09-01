import os
import secrets
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_secret_key_from_env() -> bytes:
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise ValueError("SECRET_KEY não encontrada na variável de ambiente.")
    return secret_key.encode()


def encrypt_api_key(api_key: str, fernet: Fernet) -> bytes:
    return fernet.encrypt(api_key.encode())


def decrypt_api_key(encrypted_key: bytes, fernet: Fernet) -> str:
    return fernet.decrypt(encrypted_key).decode()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def drop_all_tables(all_models, engine):
    print("Dropping all tables")
    for model in all_models:
        model.metadata.drop_all(bind=engine)


def create_all_tables(all_models, engine):
    for model in all_models:
        print(f"Creating table {model}")
        model.metadata.create_all(bind=engine)
