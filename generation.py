
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# Use the compatible HTTP transport
os.environ.setdefault("GOOGLE_GENAI_HTTP_CLIENT", "httpx")

# Initialize Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite"
)

# Create prompt template
prompt = ChatPromptTemplate.from_template("""
Answer the question using only the provided context.

If the answer is not available in the context,
say that you don't know based on the provided document.

Context:
{context}

Question:
{question}

Answer:
""")


def generate_answer(context, question):
    formatted_prompt = prompt.invoke({
        "context": context,
        "question": question
    })

    response = llm.invoke(formatted_prompt)

    # Handle both string and content-block responses
    if isinstance(response.content, str):
        return response.content

    return "\n".join(
        block["text"]
        for block in response.content
        if isinstance(block, dict) and block.get("type") == "text"
    )
