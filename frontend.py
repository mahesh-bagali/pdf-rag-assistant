
import requests
import streamlit as st

API_URL = "https://pdf-rag-assistant-4a95.onrender.com"

st.set_page_config(
    page_title="PDF RAG Assistant",
    page_icon="📚",
    layout="wide"
)

# ---------------- SESSION STATE ----------------

defaults = {
    "access_token": None,
    "user_email": None,
    "messages": [],
    "conversation_id": None,
    "uploaded_files": [],
    "conversations": []
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def auth_headers():
    return {
        "Authorization": f"Bearer {st.session_state.access_token}"
    }


def api_request(method, endpoint, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update(auth_headers())

    return requests.request(
        method,
        f"{API_URL}{endpoint}",
        headers=headers,
        timeout=180,
        **kwargs
    )


def logout():
    for key in defaults:
        st.session_state[key] = defaults[key]
    st.rerun()


# ---------------- BACKEND STATUS ----------------

def check_backend():
    try:
        response = requests.get(
            f"{API_URL}/health",
            timeout=10
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


# ---------------- AUTHENTICATION ----------------

if not st.session_state.access_token:

    st.title("📚 PDF RAG Assistant")
    st.caption("Your personal document question-answering assistant")

    login_tab, register_tab = st.tabs(["Login", "Create Account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if submitted:
            try:
                response = requests.post(
                    f"{API_URL}/auth/login",
                    json={
                        "email": email,
                        "password": password
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    st.session_state.access_token = (
                        response.json()["access_token"]
                    )
                    st.session_state.user_email = email
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Login failed."))

            except requests.RequestException as error:
                st.error(f"Backend connection failed: {error}")

    with register_tab:
        with st.form("register_form"):
            new_email = st.text_input("Email address")
            new_password = st.text_input(
                "Password (minimum 8 characters)",
                type="password"
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password"
            )
            register = st.form_submit_button(
                "Create Account",
                use_container_width=True
            )

        if register:
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 8:
                st.error("Password must contain at least 8 characters.")
            else:
                try:
                    response = requests.post(
                        f"{API_URL}/auth/register",
                        json={
                            "email": new_email,
                            "password": new_password
                        },
                        timeout=30
                    )

                    if response.status_code == 201:
                        st.success("Account created! Please log in.")
                    else:
                        st.error(
                            response.json().get(
                                "detail",
                                "Registration failed."
                            )
                        )

                except requests.RequestException as error:
                    st.error(f"Backend connection failed: {error}")

    st.stop()


# ---------------- VERIFY TOKEN ----------------

try:
    profile_response = api_request("GET", "/auth/me")

    if profile_response.status_code != 200:
        logout()

except requests.RequestException:
    st.error("Cannot connect to the backend.")
    st.stop()


# ---------------- API FUNCTIONS ----------------

def get_conversations():
    try:
        response = api_request("GET", "/conversations")
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return []


def load_conversation(conversation_id):
    try:
        response = api_request(
            "GET",
            f"/conversations/{conversation_id}"
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
            st.rerun()
        else:
            st.error(response.text)

    except requests.RequestException as error:
        st.error(str(error))


def delete_conversation():
    conversation_id = st.session_state.conversation_id

    if conversation_id is None:
        return

    try:
        response = api_request(
            "DELETE",
            f"/conversations/{conversation_id}"
        )

        if response.status_code == 200:
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.success("Conversation deleted.")
            st.rerun()
        else:
            st.error(response.text)

    except requests.RequestException as error:
        st.error(str(error))


# ---------------- SIDEBAR ----------------

with st.sidebar:

    st.title("📚 PDF Assistant")
    st.caption(f"Logged in as {st.session_state.user_email}")

    if st.button("Logout", use_container_width=True):
        logout()

    st.divider()

    if st.button("＋ New Chat", use_container_width=True):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("Chat History")

    conversations = get_conversations()

    for conversation in conversations:
        if st.button(
            conversation["title"][:35],
            key=f"conversation_{conversation['id']}",
            use_container_width=True
        ):
            load_conversation(conversation["id"])

    if st.session_state.conversation_id is not None:
        if st.button("🗑️ Delete Current Chat"):
            delete_conversation()

    st.divider()
    st.subheader("Upload PDF")

    uploaded_file = st.file_uploader(
        "Choose a PDF document",
        type=["pdf"]
    )

    if st.button("Upload PDF", use_container_width=True):

        if uploaded_file is None:
            st.warning("Please select a PDF first.")

        else:
            try:
                with st.spinner("Processing PDF..."):
                    response = api_request(
                        "POST",
                        "/documents/upload",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                "application/pdf"
                            )
                        }
                    )

                if response.status_code == 200:
                    result = response.json()
                    st.success("PDF uploaded successfully!")
                    st.write(f"Pages: {result['pages_processed']}")
                    st.write(f"Chunks: {result['chunks_created']}")

                    if uploaded_file.name not in st.session_state.uploaded_files:
                        st.session_state.uploaded_files.append(
                            uploaded_file.name
                        )
                else:
                    st.error(f"Upload failed: {response.text}")

            except requests.RequestException as error:
                st.error(f"Upload error: {error}")

    st.divider()
    st.subheader("System Status")

    if check_backend():
        st.success("Backend connected")
    else:
        st.error("Backend disconnected")


# ---------------- MAIN INTERFACE ----------------

st.title("PDF RAG Assistant")
st.caption("Upload documents and ask questions about their content.")

st.divider()
st.subheader("💬 Ask your documents")

if not st.session_state.messages:
    st.info(
        "Welcome! Upload a PDF from the sidebar and start asking questions."
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        for source in message.get("sources", []):
            st.caption(
                f"📄 {source['pdf_name']} — Page {source['page_number']}"
            )


# ---------------- QUESTION ANSWERING ----------------

question = st.chat_input("Ask something about your PDFs...")

if question:

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        try:
            with st.spinner("Searching documents..."):

                response = api_request(
                    "POST",
                    "/questions/ask",
                    json={
                        "question": question,
                        "conversation_id": st.session_state.conversation_id
                    }
                )

            if response.status_code == 200:

                result = response.json()

                st.session_state.conversation_id = result["conversation_id"]

                st.markdown(result["answer"])

                sources = result.get("sources", [])

                for source in sources:
                    st.caption(
                        f"📄 {source['pdf_name']} — Page {source['page_number']}"
                    )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": sources
                })

            else:
                st.error(f"API error: {response.text}")
                st.session_state.messages.pop()

        except requests.RequestException as error:
            st.error(f"Backend connection error: {error}")
            st.session_state.messages.pop()
