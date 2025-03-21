import chromadb
import uuid
from google import generativeai as genai
from sentence_transformers import SentenceTransformer
from text_extraction import extract_text
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("API_KEY"))

chroma_client = chromadb.PersistentClient(path="./chroma_db")
documents = chroma_client.get_or_create_collection(name="documents")
embedding_model = SentenceTransformer("BAAI/bge-small-en")

HISTORY = []  # Store conversation history in-memory for the purpose of hackathon


def vectorize_and_store(file):
    text = extract_text(file)
    embedding = get_embedding(text)
    documents.add(ids=str(uuid.uuid4()), documents=text, embeddings=embedding)


def get_embedding(text):
    return embedding_model.encode(text)


def query_documents(query_embedding, top_k=3):
    results = documents.query(query_embeddings=query_embedding, n_results=top_k)
    return results["documents"], results["metadatas"]


def get_prompt(query, context):
    prompt = f"""
    Conversation History:
    {"\n".join([f"User: {exchange['user']}\nBot: {exchange['bot']}" for exchange in HISTORY])}

    User Query: {query}

    Context:
    {context}

    Instructions:
    You are an AI assistant designed to answer user questions based on the provided context. Focus on providing a clear and relevant answer based on the context and the conversation history if applicable. Do not mention the process of retrieving or accessing data, and keep the conversation natural and focused on the user's needs. If a piece of information is missing, simply state that you don't know it, but avoid referencing how or why you lack that information.

    Answer:
    """

    return prompt



def get_response(query):
    query_embedding = get_embedding(query)
    documents, metadatas = query_documents(query_embedding)
    context = "\n".join([doc for doc in documents[0]])

    model = genai.GenerativeModel(model_name='gemini-2.0-flash')
    response = model.generate_content(get_prompt(query, context))

    HISTORY.append({"user": query, "bot": response})

    return response.text
