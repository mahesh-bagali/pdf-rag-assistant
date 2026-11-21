
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr


# -------------------------
# Authentication Schemas
# -------------------------

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128
    )


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime


# -------------------------
# Question Schemas
# -------------------------

class QuestionRequest(BaseModel):
    question: str = Field(
        min_length=1,
        description="Question to ask about the uploaded PDFs"
    )

    conversation_id: int | None = Field(
        default=None,
        description="Existing conversation ID, if continuing a chat"
    )


class SourceResponse(BaseModel):
    pdf_name: str
    page_number: int


class QuestionResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceResponse]
    conversation_id: int


# -------------------------
# Conversation Schemas
# -------------------------

class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class MessageHistoryResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: list[SourceResponse]
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageHistoryResponse]
