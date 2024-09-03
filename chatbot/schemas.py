import enum

from pydantic import BaseModel
from typing import List, Optional


class MessageCreate(BaseModel):
    message: str
    user_id: int
    model_name: str
    chat_id: int


class GPTModelEnum(str, enum.Enum):
    gpt4o = "gpt-4o"
    gpt4o_mini = "gpt-4o-mini"
    gpt4_turbo = "gpt-4-turbo"
    gpt3_5_turbo = "gpt-3.5-turbo"


class GroqModelEnum(str, enum.Enum):
    gemma_2_9b = "gemma2-9b-it"
    gemma_7b = "gemma-7b-it"
    llama_3_groq_70b_tool_use_preview = "llama3-groq-70b-8192-tool-use-preview"
    llama_3_groq_8b_tool_use_preview = "llama3-groq-8b-8192-tool-use-preview"
    llama_guard_3_8b = "llama-guard-3-8b"
    meta_llama_3_70b = "llama3-70b-8192"
    meta_llama_3_8b = "llama3-8b-8192"
    mixtral_8x7b = "mixtral-8x7b-32768"


class MessageSchema(BaseModel):
    id: int
    message: str
    db_query: Optional[str]
    cost: Optional[float]
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
    preferred_model: str = "groq"
    user_database_path: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserSchema(UserBase):
    id: int
    is_active: bool
    user_database_path: Optional[str] = None

    class Config:
        orm_mode = True
