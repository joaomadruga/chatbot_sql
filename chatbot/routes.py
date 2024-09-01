import os
import sqlite3
from datetime import datetime
from typing import List

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from langchain_community.callbacks import get_openai_callback
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user
from auth.utils import decrypt_api_key, get_secret_key_from_env
from chatbot.helpers import (
    get_llm_instance, merge_db_files,
    natural_language_to_sql,
    process_csv_to_db,
)
from chatbot.schemas import GPTModelEnum, GroqModelEnum, UserSchema
from chatbot.models import User
from chatbot.schemas import (
    MessageCreate,
    ChatCreate,
    ChatSchema,
    MessageSchema,
)
from chatbot.models import Chat, Message
from auth.dependencies import get_db

router = APIRouter()


def create_default_bot(db: Session) -> User:
    bot_user = db.query(User).filter(User.username == "nino").first()
    if not bot_user:
        bot_user = User(username="nino", image_base64=None)
        db.add(bot_user)
        db.commit()
        db.refresh(bot_user)

    return bot_user


@router.post("/create_chat/", response_model=ChatSchema)
def create_chat(
    chat: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    create_default_bot(db)  # Ensure the bot user exists

    new_chat = Chat(user_id=current_user.id, title=chat.title)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat


@router.post("/generate_bot_answer/", response_model=MessageSchema)
def generate_bot_answer(
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bot_user = create_default_bot(db)

    chat = db.query(Chat).filter(Chat.id == message.chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat history not found")

    new_user_message = Message(
        chat_id=message.chat_id,
        message=message.message,
        user_id=message.user_id,
        cost=0
    )

    db.add(new_user_message)
    db.commit()
    db.refresh(new_user_message)

    secret_key = get_secret_key_from_env()
    fernet = Fernet(secret_key)
    answer = Message(
        chat_id=message.chat_id,
        message="You should add an API key.",
        user_id=bot_user.id,
        cost=0
    )

    if current_user.hashed_api_key:
        api_key = decrypt_api_key(encrypted_key=current_user.hashed_api_key,
                                  fernet=fernet)
        os.environ.update({"GROQ_API_KEY": api_key, "OPENAI_API_KEY": api_key})
        llm = get_llm_instance(model_name=message.model_name)

        query, output, cost = natural_language_to_sql(
            question=message.message,
            llm=llm,
            db_name=current_user.user_database_path
        )
        answer = Message(
            chat_id=message.chat_id,
            cost=cost,
            db_query=query,
            message=output,
            user_id=bot_user.id
        )

    db.add(answer)
    db.commit()
    db.refresh(answer)

    return answer


@router.get("/list_chat_histories/", response_model=List[ChatSchema])
def list_chat_histories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    create_default_bot(db)  # Ensure the bot user exists

    chat_histories = db.query(Chat).filter(Chat.user_id == current_user.id).all()
    return chat_histories


@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/models")
def list_models():
    gpt_models = [v.value for k, v in GPTModelEnum.__members__.items()]
    groq_models = [v.value for k, v in GroqModelEnum.__members__.items()]

    return {
        "gpt": gpt_models,
        "groq": groq_models
    }


@router.post("/uploadfiles/")
async def upload_files(current_user: User = Depends(get_current_user),
                       files: List[UploadFile] = File(...),
                       db: Session = Depends(get_db)):
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    max_upload_size = int(os.getenv("MAX_UPLOAD_SIZE", "50")) * 1024 * 1024

    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    total_size = sum([file.size for file in files])
    if total_size > max_upload_size:
        raise HTTPException(status_code=413,
                            detail="Total file size exceeds 50 MB limit.")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    db_name = f"{current_user.username}_{timestamp}.db"
    db_path = os.path.join(upload_dir, db_name)
    conn = sqlite3.connect(db_path)

    try:
        processed_files = []

        # Processar todos os arquivos CSV primeiro
        for file in files:
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, 'wb') as f:
                f.write(await file.read())
            processed_files.append(file_path)

            if file.filename.endswith('.csv'):
                process_csv_to_db(conn, file_path)

        # Agora, combinar todos os arquivos .db no banco de dados
        for file in files:
            file_path = os.path.join(upload_dir, file.filename)

            if file.filename.endswith('.db'):
                merge_db_files(conn, file_path)

        # Atualiza o atributo user_database_path do usuário no banco de dados
        user = db.query(User).filter(
            User.username == current_user.username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Deleta o antigo banco de dados se existir
        if user.user_database_path:
            old_db_path = os.path.join(upload_dir, user.user_database_path)
            if os.path.exists(old_db_path):
                os.remove(old_db_path)
                print(f"Deleted old database: {old_db_path}")

        user.user_database_path = db_path
        db.commit()

    finally:
        conn.close()

        for file_path in processed_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted processed file: {file_path}")

    return {"status": "Files processed and combined into a single database"}
