
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database.database import get_session
from app.database.models import Conversation, Message, User
from app.schemas import QuestionRequest, QuestionResponse
from app.services.auth_dependencies import get_current_user
from app.services.rag_service import answer_question


router = APIRouter(
    prefix="/questions",
    tags=["Questions"]
)


@router.post(
    "/ask",
    response_model=QuestionResponse
)
async def ask_question(
    request: QuestionRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        # Find an existing conversation owned by this user
        if request.conversation_id is not None:

            statement = select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id
            )

            conversation = session.exec(statement).first()

            if conversation is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found."
                )

        else:
            conversation = Conversation(
                user_id=current_user.id,
                title=request.question[:50]
            )

            session.add(conversation)
            session.flush()

        # Search only the authenticated user's PDF documents
        result = answer_question(
            question=request.question,
            user_id=current_user.id
        )

        sources = result.get("sources", [])

        # Save the user's question
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.question,
            sources="[]"
        )

        # Save the assistant's answer
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
            sources=json.dumps(sources)
        )

        session.add(user_message)
        session.add(assistant_message)

        conversation.updated_at = datetime.now(timezone.utc)
        session.add(conversation)

        session.commit()
        session.refresh(conversation)

        return {
            "question": request.question,
            "answer": result["answer"],
            "sources": sources,
            "conversation_id": conversation.id
        }

    except HTTPException:
        session.rollback()
        raise

    except FileNotFoundError:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LanceDB database not found. Upload a PDF first."
        )

    except Exception:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Question processing failed."
        )
