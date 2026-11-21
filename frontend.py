
import requests
import streamlit as st


# --------------------------------------------------
# Configuration
# --------------------------------------------------

API_URL = "https://pdf-rag-assistant-4a95.onrender.com"

st.set_page_config(
    page_title="PDF RAG Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# Session State
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "backend_connected" not in st.session_state:
    st.session_state.backend_connected = False

if "conversations" not in st.session_state:
    st.session_state.conversations = []


# --------------------------------------------------
# API Functions
# --------------------------------------------------

def check_backend():
    try:
        response = requests.get(
            f"{API_URL}/health",
            timeout=5
        )
        return response.status_code == 200

    except requests.RequestException:
        return False


def get_conversations():
    try:
        response = requests.get(
            f"{API_URL}/conversations",
            timeout=10
        )

        if response.status_code == 200:
            return response.json()

        return []

    except requests.RequestException:
        return []


def load_conversation(conversation_id):
    try:
        response = requests.get(
            f"{API_URL}/conversations/{conversation_id}",
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()

            st.session_state.conversation_id = result["id"]

            st.session_state.messages = [
                {
                    "role": message["role"],
                    "content": message["content"],
                    "sources": message.get("sources", [])
                }
                for message in result["messages"]
            ]

    except requests.RequestException as error:
        st.session_state.api_error = str(error)


def start_new_chat():
    st.session_state.conversation_id = None
    st.session_state.messages = []


def delete_current_conversation():
    conversation_id = st.session_state.conversation_id

    if conversation_id is None:
        return

    try:
        response = requests.delete(
            f"{API_URL}/conversations/{conversation_id}",
            timeout=10
        )

        if response.status_code == 200:
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.session_state.delete_message = (
                "Conversation deleted successfully."
            )
        else:
            st.session_state.api_error = response.text

    except requests.RequestException as error:
        st.session_state.api_error = str(error)


# --------------------------------------------------
# Custom Styling
# --------------------------------------------------

st.markdown("""
<style>
    .main .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(128,128,128,0.2);
    }

    .main-title {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 0;
    }

    .subtitle {
        color: #999;
        font-size: 1.05rem;
        margin-top: 8px;
        margin-bottom: 25px;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid rgba(128,128,128,0.15);
    }

    div.stButton > button {
        border-radius: 10px;
        min-height: 42px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    div.stButton > button:hover {
        border-color: #7c83ff;
    }

    div[data-testid="stFileUploader"] {
        border-radius: 12px;
    }

    div[data-testid="stChatInput"] {
        border-radius: 14px;
    }

    div[data-testid="stExpander"] {
        border-radius: 10px;
        border: 1px solid rgba(128,128,128,0.25);
    }

    .section-label {
        font-size: 0.85rem;
        font-weight: 700;
        color: #999;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 12px;
    }

    .welcome-box {
        padding: 30px;
        border-radius: 16px;
        border: 1px solid rgba(128,128,128,0.2);
        text-align: center;
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:

    st.title("📚 PDF Assistant")

    st.caption("Your personal document Q&A assistant")

    st.divider()

    # New Chat
    st.button(
        "＋ New Chat",
        use_container_width=True,
        type="primary",
        key="new_chat_button",
        on_click=start_new_chat
    )

    st.divider()

    # Previous Conversations
    st.markdown(
        '<p class="section-label">Chat History</p>',
        unsafe_allow_html=True
    )

    st.session_state.conversations = get_conversations()

    if st.session_state.conversations:

        for conversation in st.session_state.conversations:

            conversation_id = conversation["id"]

            title = conversation["title"]

            if len(title) > 30:
                title = title[:30] + "..."

            is_current = (
                st.session_state.conversation_id == conversation_id
            )

            button_label = (
                f"📂 {title}"
                if is_current
                else f"💬 {title}"
            )

            st.button(
                button_label,
                key=f"conversation_{conversation_id}",
                use_container_width=True,
                type="secondary" if not is_current else "primary",
                on_click=load_conversation,
                args=(conversation_id,)
            )

    else:
        st.caption("No previous conversations yet.")

    if st.session_state.conversation_id is not None:

        st.button(
            "🗑️ Delete Current Chat",
            use_container_width=True,
            key="delete_current_chat",
            on_click=delete_current_conversation
        )

    st.divider()

    # Documents
    st.markdown(
        '<p class="section-label">Documents</p>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF document",
        type=["pdf"],
        help="Upload a PDF to add it to your knowledge base."
    )

    if st.button(
        "Upload PDF",
        use_container_width=True,
        key="upload_pdf_button"
    ):

        if uploaded_file is None:
            st.warning("Please select a PDF first.")

        else:
            try:
                with st.spinner("Processing your PDF..."):

                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/pdf"
                        )
                    }

                    response = requests.post(
                        f"{API_URL}/documents/upload",
                        files=files,
                        timeout=180
                    )

                if response.status_code == 200:

                    result = response.json()

                    if uploaded_file.name not in st.session_state.uploaded_files:
                        st.session_state.uploaded_files.append(
                            uploaded_file.name
                        )

                    st.success("PDF uploaded successfully!")

                    st.write(
                        f"**Pages:** {result.get('pages_processed', 0)}"
                    )

                    st.write(
                        f"**Chunks:** {result.get('chunks_created', 0)}"
                    )

                else:
                    st.error(f"Upload failed: {response.text}")

            except requests.RequestException as error:
                st.error(f"Connection error: {error}")

    st.divider()

    # Uploaded Documents
    st.markdown(
        '<p class="section-label">Uploaded documents</p>',
        unsafe_allow_html=True
    )

    if st.session_state.uploaded_files:

        for filename in st.session_state.uploaded_files:
            st.write(f"📄 {filename}")

    else:
        st.caption("No documents uploaded in this session.")

    st.divider()

    # Backend Status
    st.markdown(
        '<p class="section-label">System status</p>',
        unsafe_allow_html=True
    )

    if check_backend():
        st.success("Backend connected")
    else:
        st.error("Backend disconnected")

    st.caption("PDF RAG Assistant · Powered by FastAPI and Gemini")


# --------------------------------------------------
# Display Notifications
# --------------------------------------------------

if "delete_message" in st.session_state:
    st.success(st.session_state.delete_message)
    del st.session_state.delete_message

if "api_error" in st.session_state:
    st.error(st.session_state.api_error)
    del st.session_state.api_error


# --------------------------------------------------
# Main Header
# --------------------------------------------------

st.markdown(
    '<p class="main-title">PDF RAG Assistant</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="subtitle">'
    'Upload your documents and get intelligent answers from their content.'
    '</p>',
    unsafe_allow_html=True
)

st.divider()

st.subheader("💬 Ask your documents")


# --------------------------------------------------
# Welcome Screen
# --------------------------------------------------

if not st.session_state.messages:

    st.markdown("""
    <div class="welcome-box">
        <h2>👋 Welcome!</h2>
        <p>Ask questions about your uploaded PDF documents.</p>
        <p style="color: #999;">
            Upload a PDF from the sidebar and start a conversation.
        </p>
    </div>
    """, unsafe_allow_html=True)


# --------------------------------------------------
# Display Chat History
# --------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        sources = message.get("sources", [])

        if sources:

            with st.expander("📚 View sources"):

                for source in sources:

                    st.write(
                        f"📄 **{source['pdf_name']}** "
                        f"— Page {source['page_number']}"
                    )


# --------------------------------------------------
# Chat Input and Question Processing
# --------------------------------------------------

question = st.chat_input(
    "Ask something about your PDFs..."
)

if question:

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        try:

            with st.spinner(
                "Searching documents and generating your answer..."
            ):

                request_data = {
                    "question": question,
                    "conversation_id": st.session_state.conversation_id
                }

                response = requests.post(
                    f"{API_URL}/questions/ask",
                    json=request_data,
                    timeout=180
                )

            if response.status_code == 200:

                result = response.json()

                answer = result["answer"]
                sources = result.get("sources", [])

                st.session_state.conversation_id = (
                    result["conversation_id"]
                )

                st.markdown(answer)

                if sources:

                    with st.expander("📚 View sources"):

                        for source in sources:

                            st.write(
                                f"📄 **{source['pdf_name']}** "
                                f"— Page {source['page_number']}"
                            )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })

            else:

                error_message = (
                    f"API error ({response.status_code}): "
                    f"{response.text}"
                )

                st.error(error_message)

                st.session_state.messages.pop()

        except requests.RequestException as error:

            st.error(
                f"Could not connect to the backend: {error}"
            )

            st.session_state.messages.pop()
