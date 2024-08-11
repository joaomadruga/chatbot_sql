import enum

from pydantic import BaseModel
from typing import List, Optional


class MessageCreate(BaseModel):
    message: str
    user_id: int
    model_name: str
    chat_id: int


class LLMModelEnum(str, enum.Enum):
    chatgpt = "chatgpt"
    groq = "groq"


class MessageSchema(BaseModel):
    id: int
    message: str
    user_id: int

    class Config:
        orm_mode = True


class ChatCreate(BaseModel):
    title: Optional[str] = None


class ChatSchema(BaseModel):
    id: int
    title: Optional[str]
    messages: List[MessageSchema] = []

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    username: str
    image_base64: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserSchema(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True
