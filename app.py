import os
import streamlit as st
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_text_splitters.character import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain


working_dir = os.path.dirname(os.path.abspath(__file__))


def load_document(file_path):
    loader = UnstructuredPDFLoader(file_path)
    documents = loader.load()
    return documents


def setup_vectorstore(documents):
    embeddings = HuggingFaceEmbeddings()
    text_splitter = CharacterTextSplitter(
        separator="/n",
        chunk_size=1000,
        chunk_overlap=200
    )
    doc_chunks = text_splitter.split_documents(documents)
    vectorstore = FAISS.from_documents(doc_chunks, embeddings)
    return vectorstore


def create_chain(vectorstore, api_key):
    # Asegúrate de pasar el api_key al LLM si es necesario
    llm = ChatGroq(
        model="llama-3.1-70b-versatile",
        temperature=0,
        api_key=api_key  # Usa el API Key ingresado por el usuario
    )
    retriever = vectorstore.as_retriever()
    memory = ConversationBufferMemory(
        llm=llm,
        output_key="answer",
        memory_key="chat_history",
        return_messages=True
    )
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        chain_type="map_reduce",
        memory=memory,
        verbose=True
    )
    return chain


st.set_page_config(
    page_title="Chat with Doc",
    page_icon="📄",
    layout="centered"
)

st.title("🦙 Chat with Doc - LLAMA 3.1")

# Inicializa el historial de chat en el estado de sesión
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Entrada para el API Key
api_key = st.text_input("Ingrese su API Key", type="password")  # Tipo 'password' para ocultar el API Key

# Verifica si el API Key ha sido ingresado
if api_key:
    uploaded_file = st.file_uploader(label="Sube tu archivo PDF", type=["pdf"])

    if uploaded_file:
        file_path = f"{working_dir}/{uploaded_file.name}"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        if "vectorstore" not in st.session_state:
            st.session_state.vectorstore = setup_vectorstore(load_document(file_path))

        if "conversation_chain" not in st.session_state:
            st.session_state.conversation_chain = create_chain(st.session_state.vectorstore, api_key)

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Pregúntale a Llama...")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            response = st.session_state.conversation_chain({"question": user_input})
            assistant_response = response["answer"]
            st.markdown(assistant_response)
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
else:
    st.warning("Por favor, ingresa tu API Key para continuar.")
