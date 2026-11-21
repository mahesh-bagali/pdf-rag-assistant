
import os

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_lancedb import LanceDB

load_dotenv()

VECTOR_STORE_PATH = "./.rag_cache/db/lancedb"
TABLE_NAME = "pdf_documents"


def retrieve_documents(vector_store, question):
    results = vector_store.similarity_search(question, k=2)

    if not results:
        print("No relevant information found.")
        return

    print("\nRelevant PDF information:\n")

    for index, document in enumerate(results, start=1):
        print(f"Result {index}:")
        print(document.page_content)
        print(f"Metadata: {document.metadata}")
        print("-" * 50)


def main():
    if not os.path.exists(VECTOR_STORE_PATH):
        raise FileNotFoundError("LanceDB database not found. Run ingestion_pipeline.py first.")

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001"
    )

    vector_store = LanceDB(
        embedding_function=embeddings,
        uri=VECTOR_STORE_PATH,
        table_name=TABLE_NAME
    )

    print("Connected to LanceDB successfully!")

    question = input("\nAsk a question about your PDF: ")

    retrieve_documents(vector_store, question)


if __name__ == "__main__":
    main()
