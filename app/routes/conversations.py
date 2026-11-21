
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database.database import get_session
from app.database.models import Conversation, Message, User
from app.schemas import (
    ConversationResponse,
    ConversationDetailResponse,
    MessageHistoryResponse,
)
from app.services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)


@router.get(
    "",
    response_model=list[ConversationResponse]
)
def get_conversations(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )

    return session.exec(statement).all()


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse
)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    )

    conversation = session.exec(statement).first()

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    message_statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )

    messages = session.exec(message_statement).all()

    message_history = []

    for message in messages:
        try:
            sources = json.loads(message.sources or "[]")
        except (json.JSONDecodeError, TypeError):
            sources = []

        message_history.append(
            MessageHistoryResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                sources=sources,
                created_at=message.created_at
            )
        )

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=message_history
    )


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    )

    conversation = session.exec(statement).first()

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    message_statement = select(Message).where(
        Message.conversation_id == conversation_id
    )

    messages = session.exec(message_statement).all()

    for message in messages:
        session.delete(message)

    session.delete(conversation)
    session.commit()

    return {
        "message": "Conversation deleted successfully.",
        "conversation_id": conversation_id
    }
