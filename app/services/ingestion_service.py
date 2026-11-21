
import json
import uuid
from pathlib import Path

import lancedb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlmodel import Session

from app.database.models import UploadedDocument


DATA_FOLDER = Path("data")
VECTOR_STORE_PATH = "./.rag_cache/db/lancedb"
TABLE_NAME = "pdf_documents_v2"


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

    document_id = uuid.uuid4().hex

    user_folder = DATA_FOLDER / f"user_{user_id}"
    user_folder.mkdir(parents=True, exist_ok=True)

    pdf_path = user_folder / f"{document_id}_{safe_filename}"

    try:
        pdf_path.write_bytes(content)

        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()

        if not documents:
            raise ValueError("The PDF contains no readable pages.")

        for document in documents:
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
            model="models/gemini-embedding-001"
        )

        texts = [chunk.page_content for chunk in chunks]
        vectors = embeddings.embed_documents(texts)

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
            table = db.create_table(TABLE_NAME, data=rows)

        uploaded_document = UploadedDocument(
            document_id=document_id,
            user_id=user_id,
            filename=safe_filename,
            storage_path=str(pdf_path),
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
            "message": "PDF processed and added to the vector database."
        }

    except Exception:
        session.rollback()

        if pdf_path.exists():
            pdf_path.unlink()

        raise
