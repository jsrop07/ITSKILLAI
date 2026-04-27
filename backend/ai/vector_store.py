# ai/vector_store.py

import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "ai_question_documents"
)

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

collection = client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME
)


def add_chunk_to_vector_store(
    vector_id: str,
    content: str,
    embedding: list[float],
    metadata: dict
):
    collection.upsert(
        ids=[vector_id],
        documents=[content],
        embeddings=[embedding],
        metadatas=[metadata]
    )


def search_similar_chunks(
    query_embedding: list[float],
    top_k: int = 5
):
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )