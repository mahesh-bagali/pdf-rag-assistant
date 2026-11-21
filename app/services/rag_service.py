
import json
import os

import lancedb
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import text

from app.database.database import engine
from generation import generate_answer


load_dotenv()

VECTOR_STORE_PATH = "./.rag_cache/db/lancedb"
TABLE_NAME = "pdf_documents_v2"


def answer_question(question: str, user_id: int):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001"
    )

    query_embedding = embeddings.embed_query(question)

    if (
        os.getenv("SUPABASE_URL")
        and os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    ):
        vector_value = (
            "[" + ",".join(str(value) for value in query_embedding) + "]"
        )

        with engine.connect() as connection:
            results = connection.execute(
                text("""
                    SELECT *
                    FROM public.match_pdf_chunks(
                        CAST(:query_embedding AS vector),
                        :match_user_id,
                        :match_count
                    )
                """),
                {
                    "query_embedding": vector_value,
                    "match_user_id": user_id,
                    "match_count": 2
                }
            ).mappings().all()

        rows = [
            {
                "text": row["content"],
                "metadata": row["metadata"]
            }
            for row in results
        ]

    else:
        if not os.path.exists(VECTOR_STORE_PATH):
            raise FileNotFoundError(
                "LanceDB database not found. Upload a PDF first."
            )

        db = lancedb.connect(VECTOR_STORE_PATH)

        try:
            table = db.open_table(TABLE_NAME)
        except Exception:
            return {
                "question": question,
                "answer": "No relevant information found in your uploaded PDFs.",
                "sources": []
            }

        results = (
            table.search(query_embedding)
            .where(f"user_id = {int(user_id)}", prefilter=True)
            .limit(2)
            .to_list()
        )

        rows = results

    if not rows:
        return {
            "question": question,
            "answer": "No relevant information found in your uploaded PDFs.",
            "sources": []
        }

    context_parts = []
    sources = []

    for row in rows:
        metadata = row.get("metadata", {})

        if isinstance(metadata, str):
            metadata = json.loads(metadata or "{}")

        pdf_name = metadata.get("pdf_name", "Unknown PDF")
        page_number = metadata.get(
            "page_number",
            metadata.get("page", 0) + 1
        )

        context_parts.append(
            f"Source: {pdf_name}, Page: {page_number}\n"
            f"Content: {row['text']}"
        )

        source = {
            "pdf_name": pdf_name,
            "page_number": page_number
        }

        if source not in sources:
            sources.append(source)

    context = "\n\n".join(context_parts)

    answer = generate_answer(
        context=context,
        question=question
    )

    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }
