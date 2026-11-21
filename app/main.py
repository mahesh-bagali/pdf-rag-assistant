
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import documents, questions, conversations, auth
from app.database.database import create_db_and_tables
from app.database.models import (
    User,
    Conversation,
    Message,
    UploadedDocument,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables when the application starts
    create_db_and_tables()
    yield


app = FastAPI(
    title="PDF RAG Assistant",
    description="Ask questions and get answers from uploaded PDF documents using RAG.",
    version="1.0.0",
    lifespan=lifespan
)


# Register API routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(questions.router)
app.include_router(conversations.router)


@app.get("/")
def home():
    return {
        "message": "Welcome to PDF RAG Assistant",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
