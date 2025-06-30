
# FILE: services/rag_service.py
# Final, Unabridged Version: June 29, 2025

import os
import uuid
import logging
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class RAGService:
    """
    Manages the vector memory for the AI Companion (Retrieval-Augmented Generation).
    This service handles the creation of text embeddings and performs similarity
    searches to provide the AI with relevant long-term memory for any given query.
    """
    def __init__(self):
        """
        Initializes the RAG service with a persistent vector database client.
        The database will be stored on the server's file system.
        """
        self.collection = None
        try:
            # Use a standard, absolute path inside the container for persistence.
            db_path = "/app/data/chroma"

            # CORRECTED: Ensure the directory exists before the client tries to write to it.
            os.makedirs(db_path, exist_ok=True)
            logger.info(f"Ensured ChromaDB persistence directory exists at: {db_path}")

            # This uses a persistent client, storing data in the specified directory.
            # This directory MUST be mounted as a Docker volume to persist data across restarts.
            self.client = chromadb.PersistentClient(path=db_path)

            # Use an embedding function from ChromaDB's utilities. OpenAI's is a powerful choice.
            # This requires the platform's primary API key to be set in the environment.
            api_key = os.getenv("BOOTSTRAP_AGENT_API_KEY")
            if not api_key:
                raise ValueError("BOOTSTRAP_AGENT_API_KEY is not set for the embedding model.")
                
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name="text-embedding-3-large"
            )

            # Get or create the main collection for conversation memory.
            self.collection = self.client.get_or_create_collection(
                name="ai_companion_memory",
                embedding_function=self.embedding_function
            )
            logger.info("RAG Service initialized successfully with PERSISTENT ChromaDB client.")

        except Exception as e:
            logger.exception(f"FATAL: Failed to initialize RAG Service. The memory system will be offline. Error: {e}")
            self.client = None

    def add_memory(self, user_id: str, text: str, doc_id: str = None):
        """Adds a piece of text (a memory) to the user's vector store."""
        if not self.collection:
            logger.error("Cannot add memory: RAG service is not available.")
            return

        if not text or not isinstance(text, str) or not text.strip():
            logger.warning("Attempted to add empty or invalid memory text. Skipping.")
            return

        if not doc_id:
            doc_id = f"{user_id}_{uuid.uuid4()}"

        try:
            self.collection.add(
                documents=[text],
                metadatas=[{"user_id": user_id}],
                ids=[doc_id]
            )
            logger.debug(f"Added memory with ID '{doc_id}' for user '{user_id}'.")
        except Exception as e:
            logger.error(f"Failed to add memory to ChromaDB for doc_id '{doc_id}': {e}")

    def search_memory(self, user_id: str, query_text: str, n_results: int = 5) -> list[str]:
        """Finds the most relevant memories for a given query text via vector similarity search."""
        if not self.collection:
            logger.error("Cannot search memory: RAG service is not available.")
            return []

        if not query_text or not isinstance(query_text, str) or not query_text.strip():
            return []
            
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where={"user_id": user_id} # CRITICAL: Ensures data privacy between users
            )
            
            retrieved_docs = results['documents'][0] if results and results.get('documents') else []
            logger.info(f"RAG service retrieved {len(retrieved_docs)} memories for user '{user_id}'.")
            return retrieved_docs
        except Exception as e:
            logger.error(f"Failed to search memory in ChromaDB for user '{user_id}': {e}")
            return []

# Create a singleton instance to be used across the entire application.
rag_service = RAGService()
