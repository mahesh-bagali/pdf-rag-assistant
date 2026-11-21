
import os
from pathlib import Path

import lancedb
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_lancedb import LanceDB

load_dotenv()

DATA_FOLDER = Path("data")
VECTOR_STORE_PATH = "./.rag_cache/db/lancedb"
TABLE_NAME = "pdf_documents"


def create_vector_store():
    pdf_files = sorted(DATA_FOLDER.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError("No PDF files found inside the data folder.")

    all_chunks = []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    for pdf_path in pdf_files:
        print(f"\nLoading: {pdf_path.name}")

        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()

        if not documents:
            print(f"No readable content in {pdf_path.name}. Skipping.")
            continue

        for document in documents:
            document.metadata["pdf_name"] = pdf_path.name
            document.metadata["page_number"] = (
                document.metadata.get("page", 0) + 1
            )

        chunks = text_splitter.split_documents(documents)
        all_chunks.extend(chunks)

        print(f"Loaded {len(documents)} pages.")
        print(f"Created {len(chunks)} chunks.")

    if not all_chunks:
        raise ValueError("No readable PDF content found.")

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001"
    )

    # Rebuild only the vector database table.
    db = lancedb.connect(VECTOR_STORE_PATH)
    db.drop_table(TABLE_NAME, ignore_missing=True)

    vector_store = LanceDB(
        embedding_function=embeddings,
        uri=VECTOR_STORE_PATH,
        table_name=TABLE_NAME
    )

    vector_store.add_documents(all_chunks)

    print("\nAll PDF embeddings added successfully!")
    print(f"Total chunks: {len(all_chunks)}")


if __name__ == "__main__":
    create_vector_store()
