from sqlalchemy import (
    Column,
    Float,
    Integer,
    LargeBinary,
    String,
    ForeignKey,
    Text,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True)
    hashed_password = Column(Text)
    hashed_api_key = Column(LargeBinary, nullable=True)
    is_active = Column(Boolean, default=True)
    image_base64 = Column(Text, nullable=True)
    user_database_path = Column(String(255), nullable=True, default="dbs/olimpic_medals.db")

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=True)

    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    db_query = Column(Text, nullable=True)
    cost = Column(Float, nullable=False)
    message = Column(Text, nullable=False)

    # A message belongs to one chat and one user
    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", back_populates="messages")
