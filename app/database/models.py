
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.id",
        index=True
    )
    title: str = Field(default="New Chat")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(
        foreign_key="conversations.id",
        index=True
    )
    role: str
    content: str
    sources: str = Field(default="[]")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UploadedDocument(SQLModel, table=True):
    __tablename__ = "uploaded_documents"

    id: Optional[int] = Field(default=None, primary_key=True)

    document_id: str = Field(
        index=True,
        unique=True
    )

    user_id: int = Field(
        foreign_key="users.id",
        index=True
    )

    filename: str

    storage_path: str

    pages_processed: int

    chunks_created: int

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
