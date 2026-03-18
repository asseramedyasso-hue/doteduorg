import os
import tempfile
import streamlit as st

# -------------------------
# Essential LangChain imports (compatible with your installed versions)
# -------------------------
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
# Configuration & Initialization
# -------------------------

# Directly set Google API key
GOOGLE_API_KEY = "AIzaSyAXsx1GaJB7fp4n3oIXNZW7Wch_OunJAYI"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

def init_llm():
    """Initialize the Gemini LLM using your API key."""
    return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.3)

def init_embeddings():
    """Use local embeddings to avoid Google embedding quota issues."""
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# -------------------------
# RAG Setup (PDF Processing)
# -------------------------

def build_retriever_tool(uploaded_file):
    """Process PDF locally and create a searchable tool."""
    try:
        # Save uploaded PDF temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name

        # Load and split PDF
        loader = PyPDFLoader(tmp_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)  # Faster indexing
        splits = text_splitter.split_documents(documents)

        # Batch embedding all chunks at once for speed
        embeddings_model = init_embeddings()
        texts = [doc.page_content for doc in splits]
        embeddings_list = embeddings_model.embed_documents(texts)  # Precompute embeddings

        # Create FAISS vector store using precomputed embeddings
        vectorstore = FAISS.from_texts(texts, embeddings_model)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        # Clean up temp file
        os.remove(tmp_path)

        # Create retriever tool for agent
        return create_retriever_tool(
            retriever,
            name="curriculum_retriever",
            description="Search this first for course-specific scientific explanations."
        )

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None

# -------------------------
# Streamlit UI Layout
# -------------------------

st.set_page_config(page_title="Socratic Science Tutor", page_icon="🔬", layout="centered")
st.title("🔬 Socratic Science Tutor")
st.markdown("---")

# Initialize Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=5,
        return_messages=True
    )

# Sidebar: PDF Upload
with st.sidebar:
    st.header("📂 Course Materials")
    uploaded_file = st.file_uploader("Upload a Science PDF", type="pdf")

    if uploaded_file and "retriever_tool" not in st.session_state:
        with st.spinner("Indexing your course material locally..."):
            tool = build_retriever_tool(uploaded_file)
            if tool:
                st.session_state.retriever_tool = tool
                st.success("PDF Ready!")

# -------------------------
# Agent & Tools Setup
# -------------------------

search = DuckDuckGoSearchRun()
tools = [
    Tool(
        name="web_search",
        func=search.run,
        description="Search the web for real-world context and modern applications."
    )
]

if "retriever_tool" in st.session_state:
    tools.append(st.session_state.retriever_tool)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an elite Socratic science tutor. 
Your goal is to guide students to understanding, NOT to give direct answers. 

Format EVERY response strictly into these 3 sections:

### 📚 From the Course
(If a PDF is uploaded, use curriculum_retriever. If not, explain based on general principles.)

### 🌐 Real-World Context
(Use web_search to find a modern application or discovery.)

### 💡 Simple Analogy
(Create a simple, relatable analogy using everyday objects.)

Tone: Encouraging and helpful."""),

    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Initialize Agent
llm = init_llm()
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=st.session_state.memory,
    verbose=True,
    handle_parsing_errors=True
)

# -------------------------
# Chat Interface
# -------------------------

# Display message history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if user_query := st.chat_input("Ask a science question..."):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = agent_executor.invoke({"input": user_query})
                response = result.get("output", "I had trouble generating a response.")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Something went wrong: {e}")
