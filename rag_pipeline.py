
import os

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_lancedb import LanceDB

from generation import generate_answer

load_dotenv()

VECTOR_STORE_PATH = "./.rag_cache/db/lancedb"
TABLE_NAME = "pdf_documents"


def main():
    if not os.path.exists(VECTOR_STORE_PATH):
        raise FileNotFoundError(
            "LanceDB database not found. Run ingestion_pipeline.py first."
        )

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001"
    )

    vector_store = LanceDB(
        embedding_function=embeddings,
        uri=VECTOR_STORE_PATH,
        table_name=TABLE_NAME
    )

    print("Connected to LanceDB successfully!")

    question = input("\nAsk a question about your PDFs: ").strip()

    if not question:
        print("Please enter a valid question.")
        return

    retrieved_docs = vector_store.similarity_search(question, k=2)

    if not retrieved_docs:
        print("No relevant information found.")
        return

    context_parts = []

    print("\nRetrieved sources:\n")

    for index, document in enumerate(retrieved_docs, start=1):
        pdf_name = document.metadata.get("pdf_name", "Unknown PDF")
        page_number = document.metadata.get("page_number", "Unknown page")

        print(f"Source {index}: {pdf_name}, Page {page_number}")

        context_parts.append(
            f"Source: {pdf_name}, Page: {page_number}\n"
            f"Content: {document.page_content}"
        )

    context = "\n\n".join(context_parts)

    print("\nGenerating answer...")

    answer = generate_answer(
        context=context,
        question=question
    )

    print("\nAnswer:")
    print(answer)


if __name__ == "__main__":
    main()
