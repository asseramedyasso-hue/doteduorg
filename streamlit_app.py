import os
import tempfile
import streamlit as st

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.tools import Tool
from langchain.tools.retriever import create_retriever_tool

# -------------------------
# CONFIG (SAFE)
# -------------------------
GOOGLE_API_KEY = os.getenv(AIzaSyAXsx1GaJB7fp4n3oIXNZW7Wch_OunJAYI)

if not AIzaSyAXsx1GaJB7fp4n3oIXNZW7Wch_OunJAYI:
    st.error("❌ API key not found. Set it in environment variables.")
    st.stop()

os.environ[AIzaSyAXsx1GaJB7fp4n3oIXNZW7Wch_OunJAYI] = AIzaSyAXsx1GaJB7fp4n3oIXNZW7Wch_OunJAYI

# -------------------------
# INIT
# -------------------------
def init_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0.3
    )

def init_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

# -------------------------
# PDF PROCESSING
# -------------------------
def build_retriever_tool(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            path = tmp.name

        loader = PyPDFLoader(path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=400
        )
        splits = splitter.split_documents(docs)

        vectorstore = FAISS.from_documents(
            splits,
            init_embeddings()
        )

        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        os.remove(path)

        return create_retriever_tool(
            retriever,
            name="curriculum_retriever",
            description="Use for course-related science questions"
        )

    except Exception as e:
        st.error(f"PDF Error: {e}")
        return None

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="Socratic Tutor", layout="centered")
st.title("🔬 Socratic Science Tutor")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=5,
        return_messages=True
    )

# Sidebar
with st.sidebar:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")

    if uploaded_file and "retriever_tool" not in st.session_state:
        with st.spinner("Processing PDF..."):
            tool = build_retriever_tool(uploaded_file)
            if tool:
                st.session_state.retriever_tool = tool
                st.success("Ready!")

# -------------------------
# TOOLS
# -------------------------
search = DuckDuckGoSearchRun()

tools = [
    Tool(
        name="web_search",
        func=search.run,
        description="Search internet"
    )
]

if "retriever_tool" in st.session_state:
    tools.append(st.session_state.retriever_tool)

# -------------------------
# PROMPT
# -------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a Socratic tutor.

ALWAYS respond in 3 sections:

### 📚 From Course
### 🌐 Real World
### 💡 Analogy
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# -------------------------
# AGENT
# -------------------------
llm = init_llm()

agent = create_tool_calling_agent(llm, tools, prompt)

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=st.session_state.memory,
    verbose=True
)

# -------------------------
# CHAT
# -------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_input := st.chat_input("Ask..."):
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                res = executor.invoke({"input": user_input})
                output = res["output"]

                st.write(output)
                st.session_state.messages.append({"role": "assistant", "content": output})

            except Exception as e:
                st.error(e)
