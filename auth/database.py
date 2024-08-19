import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL

from auth.utils import create_all_tables, drop_all_tables
from chatbot.models import User
from chatbot.models import Chat, Message

load_dotenv()

connection_args = {
    "drivername": os.getenv("DRIVER_NAME"),
    "username": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME")
}
SQLALCHEMY_DATABASE_URL = URL.create(**connection_args)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

all_models = [User, Chat, Message, Base]

if os.getenv("DROP_ALL_TABLES", False) == "True":
    drop_all_tables(all_models, engine)

create_all_tables(all_models, engine)
