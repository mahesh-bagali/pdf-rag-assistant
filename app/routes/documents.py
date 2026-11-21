
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.database.database import get_session
from app.database.models import User, UploadedDocument
from app.services.auth_dependencies import get_current_user
from app.services.ingestion_service import ingest_pdf

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed."
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded PDF is empty."
        )

    try:
        return ingest_pdf(
            filename=file.filename,
            content=content,
            user_id=current_user.id,
            session=session
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF processing failed."
        )
    finally:
        await file.close()


@router.get("")
def get_uploaded_documents(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = (
        select(UploadedDocument)
        .where(UploadedDocument.user_id == current_user.id)
        .order_by(UploadedDocument.created_at.desc())
    )

    documents = session.exec(statement).all()

    return [
        {
            "document_id": document.document_id,
            "filename": document.filename,
            "pages_processed": document.pages_processed,
            "chunks_created": document.chunks_created,
            "created_at": document.created_at
        }
        for document in documents
    ]
