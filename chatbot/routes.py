from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user
from chatbot.helpers import natural_language_to_sql
from chatbot.schemas import UserSchema
from chatbot.models import User
from chatbot.schemas import (
    LLMModelEnum,
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
        user_id=message.user_id
    )

    db.add(new_user_message)
    db.commit()
    db.refresh(new_user_message)

    llm = ChatGroq(model_name="llama3-70b-8192")
    if message.model_name == LLMModelEnum.chatgpt:
        llm = ChatOpenAI(model="gpt-4o")

    answer = Message(
            chat_id=message.chat_id,
            message=natural_language_to_sql(question=message.message, llm=llm),
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
