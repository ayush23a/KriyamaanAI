import sys
import os
import chromadb
from typing import Any
from kriyaman.services.base import BaseService


# Ensure backend path is added to sys.path so we can reuse existing ingestion / rag_chain logic
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from server.ingestion import ingest_docs
from server.rag_chain import build_rag

class KnowledgeService(BaseService):
    """
    Service responsible for document ingestion, vector retrieval, and indexing.
    """
    def __init__(self, vector_db_path: str = "data/vectordb"):
        self.vector_db_path = vector_db_path

    def ingest_documents(self, folder: str, session_id: str) -> int:
        """
        Ingests all PDF documents located in folder into session-scoped vector store.
        """
        # TODO: Qdrant Migration / PostgreSQL Migration
        # Initially forwards execution to the existing ingestion pipeline
        return ingest_docs(folder=folder, session_id=session_id)

    def get_retriever(self, session_id: str) -> Any:
        """
        Builds and returns the retriever for the given session.
        """
        # TODO: Qdrant Migration / PostgreSQL Migration
        return build_rag(session_id=session_id)

    def delete_collection(self, session_id: str) -> bool:
        """
        Deletes the session's vector store collection.
        """
        # TODO: Qdrant Migration / PostgreSQL Migration
        try:
            chroma_client = chromadb.PersistentClient(path=self.vector_db_path)
            collection_name = f"session_{session_id}"
            collection_name = "".join(c if c.isalnum() else "_" for c in collection_name)
            chroma_client.delete_collection(name=collection_name)
            return True
        except Exception as e:
            print(f"Error in KnowledgeService.delete_collection: {e}")
            return False
