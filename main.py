import os
from dotenv import load_dotenv
from fastapi import FastAPI
from auth.routes import router as auth_router
from chatbot.routes import router as users_router
from chatbot.routes import router as chatbot_router
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(chatbot_router, prefix="/chatbot", tags=["chabot"])

