
import json
import os
import tempfile
import uuid
from pathlib import Path

import lancedb
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import text
from sqlmodel import Session
from supabase import create_client

from app.database.models import UploadedDocument


load_dotenv()

DATA_FOLDER = Path("data")
VECTOR_STORE_PATH = "./.rag_cache/db/lancedb"
TABLE_NAME = "pdf_documents_v2"
BUCKET_NAME = "pdf-documents"


def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        return None

    return create_client(url, key)


def ingest_pdf(
    filename: str,
    content: bytes,
    user_id: int,
    session: Session
):
    if not content.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF.")

    safe_filename = Path(filename).name

    if not safe_filename:
        raise ValueError("Invalid PDF filename.")

    if len(content) > 20 * 1024 * 1024:
        raise ValueError("PDF size cannot exceed 20 MB.")

    document_id = uuid.uuid4().hex
    supabase = get_supabase_client()
    cloud_storage = supabase is not None

    storage_path = (
        f"user_{user_id}/{document_id}/{safe_filename}"
        if cloud_storage else None
    )

    pdf_path = None
    uploaded_to_storage = False

    try:
        if cloud_storage:
            supabase.storage.from_(BUCKET_NAME).upload(
                storage_path,
                content,
                file_options={
                    "content-type": "application/pdf",
                    "upsert": "false"
                }
            )
            uploaded_to_storage = True

            with tempfile.NamedTemporaryFile(
                suffix=".pdf",
                delete=False
            ) as temporary_file:
                temporary_file.write(content)
                pdf_path = Path(temporary_file.name)

        else:
            user_folder = DATA_FOLDER / f"user_{user_id}"
            user_folder.mkdir(parents=True, exist_ok=True)

            pdf_path = user_folder / f"{document_id}_{safe_filename}"
            pdf_path.write_bytes(content)
            storage_path = str(pdf_path)

        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()

        if not documents:
            raise ValueError("The PDF contains no readable pages.")

        for document in documents:
            document.metadata.pop("source", None)
            document.metadata["user_id"] = user_id
            document.metadata["document_id"] = document_id
            document.metadata["pdf_name"] = safe_filename
            document.metadata["page_number"] = (
                document.metadata.get("page", 0) + 1
            )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        chunks = splitter.split_documents(documents)

        if not chunks:
            raise ValueError("No readable text found in the PDF.")

        embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001"
        )

        texts = [chunk.page_content for chunk in chunks]
        vectors = embeddings.embed_documents(texts)

        if cloud_storage:
            for chunk, vector in zip(chunks, vectors):
                metadata = json.dumps(chunk.metadata)
                vector_value = (
                    "[" + ",".join(str(value) for value in vector) + "]"
                )

                session.execute(
                    text("""
                        INSERT INTO public.pdf_chunks
                        (user_id, document_id, content, metadata, embedding)
                        VALUES (
                            :user_id,
                            :document_id,
                            :content,
                            CAST(:metadata AS jsonb),
                            CAST(:embedding AS vector)
                        )
                    """),
                    {
                        "user_id": user_id,
                        "document_id": document_id,
                        "content": chunk.page_content,
                        "metadata": metadata,
                        "embedding": vector_value
                    }
                )

        else:
            rows = []

            for chunk, vector in zip(chunks, vectors):
                rows.append({
                    "id": uuid.uuid4().hex,
                    "vector": vector,
                    "text": chunk.page_content,
                    "metadata": json.dumps(chunk.metadata),
                    "user_id": user_id
                })

            db = lancedb.connect(VECTOR_STORE_PATH)

            try:
                table = db.open_table(TABLE_NAME)
                table.add(rows)
            except Exception:
                db.create_table(TABLE_NAME, data=rows)

        uploaded_document = UploadedDocument(
            document_id=document_id,
            user_id=user_id,
            filename=safe_filename,
            storage_path=storage_path,
            pages_processed=len(documents),
            chunks_created=len(chunks)
        )

        session.add(uploaded_document)
        session.commit()

        return {
            "document_id": document_id,
            "filename": safe_filename,
            "pages_processed": len(documents),
            "chunks_created": len(chunks),
            "message": "PDF processed and stored successfully."
        }

    except Exception:
        session.rollback()

        if cloud_storage and uploaded_to_storage:
            try:
                supabase.storage.from_(BUCKET_NAME).remove(
                    [storage_path]
                )
            except Exception:
                pass

        if not cloud_storage and pdf_path and pdf_path.exists():
            pdf_path.unlink()

        raise

    finally:
        if cloud_storage and pdf_path and pdf_path.exists():
            pdf_path.unlink()
