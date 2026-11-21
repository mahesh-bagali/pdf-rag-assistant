
import pytest

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.database import get_session
from app.database.models import UploadedDocument


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    SQLModel.metadata.create_all(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    test_engine.dispose()


@pytest.fixture
def user_token(client):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "user1@example.com",
            "password": "TestPassword123"
        }
    )

    assert register_response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": "user1@example.com",
            "password": "TestPassword123"
        }
    )

    assert response.status_code == 200

    return response.json()["access_token"]


@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


def create_user_and_token(client, email):
    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123"
        }
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPassword123"
        }
    )

    assert login_response.status_code == 200

    return login_response.json()["access_token"]


# -------------------------
# Basic API Tests
# -------------------------

def test_home(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# -------------------------
# Authentication Tests
# -------------------------

def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "TestPassword123"
        }
    )

    assert response.status_code == 201
    assert response.json()["email"] == "newuser@example.com"
    assert "password_hash" not in response.json()


def test_duplicate_registration(client):
    create_user_and_token(client, "duplicate@example.com")

    response = client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "TestPassword123"
        }
    )

    assert response.status_code == 409


def test_login_user(client):
    create_user_and_token(client, "login@example.com")

    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "TestPassword123"
        }
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_invalid_password(client):
    create_user_and_token(client, "wrongpass@example.com")

    response = client.post(
        "/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPassword123"
        }
    )

    assert response.status_code == 401


def test_get_current_user(client, auth_headers):
    response = client.get(
        "/auth/me",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user1@example.com"


def test_protected_endpoint_without_token(client):
    response = client.get("/conversations")

    assert response.status_code == 401


def test_invalid_token(client):
    response = client.get(
        "/conversations",
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401


# -------------------------
# Document Upload Tests
# -------------------------

def test_upload_valid_pdf(client, auth_headers, monkeypatch):

    def fake_ingest_pdf(filename, content, user_id, session):
        return {
            "document_id": "test-document-id",
            "filename": filename,
            "pages_processed": 1,
            "chunks_created": 1,
            "message": "PDF processed and added to the vector database."
        }

    monkeypatch.setattr(
        "app.routes.documents.ingest_pdf",
        fake_ingest_pdf
    )

    response = client.post(
        "/documents/upload",
        headers=auth_headers,
        files={
            "file": (
                "sample.pdf",
                b"%PDF-fake-content",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "sample.pdf"


def test_upload_invalid_file(client, auth_headers):
    response = client.post(
        "/documents/upload",
        headers=auth_headers,
        files={
            "file": (
                "notes.txt",
                b"This is a text file",
                "text/plain"
            )
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are allowed."


def test_get_uploaded_documents(client, auth_headers):
    response = client.get(
        "/documents",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# -------------------------
# Document Ownership Tests
# -------------------------

def test_document_ownership(client, monkeypatch):
    user1_token = create_user_and_token(
        client,
        "document-owner@example.com"
    )

    user2_token = create_user_and_token(
        client,
        "document-other@example.com"
    )

    user1_headers = {
        "Authorization": f"Bearer {user1_token}"
    }

    user2_headers = {
        "Authorization": f"Bearer {user2_token}"
    }

    def fake_ingest_pdf(filename, content, user_id, session):
        document = UploadedDocument(
            document_id="user1-document-id",
            user_id=user_id,
            filename=filename,
            storage_path="test/sample.pdf",
            pages_processed=2,
            chunks_created=5
        )

        session.add(document)
        session.commit()

        return {
            "document_id": document.document_id,
            "filename": document.filename,
            "pages_processed": document.pages_processed,
            "chunks_created": document.chunks_created,
            "message": "PDF processed and added to the vector database."
        }

    monkeypatch.setattr(
        "app.routes.documents.ingest_pdf",
        fake_ingest_pdf
    )

    upload_response = client.post(
        "/documents/upload",
        headers=user1_headers,
        files={
            "file": (
                "private.pdf",
                b"%PDF-test-content",
                "application/pdf"
            )
        }
    )

    assert upload_response.status_code == 200

    user1_documents = client.get(
        "/documents",
        headers=user1_headers
    )

    assert user1_documents.status_code == 200
    assert len(user1_documents.json()) == 1
    assert user1_documents.json()[0]["filename"] == "private.pdf"

    user2_documents = client.get(
        "/documents",
        headers=user2_headers
    )

    assert user2_documents.status_code == 200
    assert user2_documents.json() == []


# -------------------------
# RAG Retrieval Security Test
# -------------------------

def test_retrieval_uses_user_filter(monkeypatch):

    captured_filters = []

    class FakeEmbeddings:

        def __init__(self, model):
            self.model = model

        def embed_query(self, question):
            return [0.1, 0.2, 0.3]

    class FakeSearch:

        def where(self, condition, prefilter=True):
            captured_filters.append(condition)
            return self

        def limit(self, count):
            return self

        def to_list(self):
            return []

    class FakeTable:

        def search(self, query_embedding):
            return FakeSearch()

    class FakeDatabase:

        def open_table(self, table_name):
            return FakeTable()

    monkeypatch.setattr(
        "app.services.rag_service.GoogleGenerativeAIEmbeddings",
        FakeEmbeddings
    )

    monkeypatch.setattr(
        "app.services.rag_service.lancedb.connect",
        lambda path: FakeDatabase()
    )

    from app.services.rag_service import answer_question

    result = answer_question(
        question="What is database?",
        user_id=2
    )

    assert captured_filters == ["user_id = 2"]
    assert result["sources"] == []
    assert "No relevant information" in result["answer"]


# -------------------------
# Question Answering Tests
# -------------------------

def test_ask_question(client, auth_headers, monkeypatch):

    def fake_answer_question(question, user_id):
        return {
            "question": question,
            "answer": "FastAPI is a Python framework.",
            "sources": [
                {
                    "pdf_name": "sample.pdf",
                    "page_number": 1
                }
            ]
        }

    monkeypatch.setattr(
        "app.routes.questions.answer_question",
        fake_answer_question
    )

    response = client.post(
        "/questions/ask",
        headers=auth_headers,
        json={"question": "What is FastAPI?"}
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "FastAPI is a Python framework."
    assert len(response.json()["sources"]) == 1
    assert response.json()["conversation_id"] is not None


def test_empty_question(client, auth_headers):
    response = client.post(
        "/questions/ask",
        headers=auth_headers,
        json={"question": ""}
    )

    assert response.status_code == 422


# -------------------------
# Conversation Tests
# -------------------------

def test_conversation_history(client, auth_headers, monkeypatch):

    def fake_answer_question(question, user_id):
        return {
            "question": question,
            "answer": "Test answer",
            "sources": []
        }

    monkeypatch.setattr(
        "app.routes.questions.answer_question",
        fake_answer_question
    )

    ask_response = client.post(
        "/questions/ask",
        headers=auth_headers,
        json={"question": "Test question"}
    )

    conversation_id = ask_response.json()["conversation_id"]

    response = client.get(
        f"/conversations/{conversation_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert len(response.json()["messages"]) == 2


def test_conversation_ownership(client, monkeypatch):

    def fake_answer_question(question, user_id):
        return {
            "question": question,
            "answer": "Test answer",
            "sources": []
        }

    monkeypatch.setattr(
        "app.routes.questions.answer_question",
        fake_answer_question
    )

    user1_token = create_user_and_token(
        client,
        "owner@example.com"
    )

    user2_token = create_user_and_token(
        client,
        "other@example.com"
    )

    user1_headers = {
        "Authorization": f"Bearer {user1_token}"
    }

    user2_headers = {
        "Authorization": f"Bearer {user2_token}"
    }

    ask_response = client.post(
        "/questions/ask",
        headers=user1_headers,
        json={"question": "Private question"}
    )

    conversation_id = ask_response.json()["conversation_id"]

    response = client.get(
        f"/conversations/{conversation_id}",
        headers=user2_headers
    )

    assert response.status_code == 404

    user2_conversations = client.get(
        "/conversations",
        headers=user2_headers
    )

    assert user2_conversations.status_code == 200

    assert all(
        conversation["id"] != conversation_id
        for conversation in user2_conversations.json()
    )


def test_delete_conversation(client, auth_headers, monkeypatch):

    def fake_answer_question(question, user_id):
        return {
            "question": question,
            "answer": "Test answer",
            "sources": []
        }

    monkeypatch.setattr(
        "app.routes.questions.answer_question",
        fake_answer_question
    )

    ask_response = client.post(
        "/questions/ask",
        headers=auth_headers,
        json={"question": "Delete this conversation"}
    )

    conversation_id = ask_response.json()["conversation_id"]

    delete_response = client.delete(
        f"/conversations/{conversation_id}",
        headers=auth_headers
    )

    assert delete_response.status_code == 200

    history_response = client.get(
        f"/conversations/{conversation_id}",
        headers=auth_headers
    )

    assert history_response.status_code == 404
