"""
RAG Service for managing vector store operations.
Handles initialization, embedding, and retrieval of achievement standards.
"""

import logging
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from .data_loader import DataLoader

logger = logging.getLogger(__name__)


class RAGService:
    """
    Service for managing vector store operations for special education RAG system.
    """

    def __init__(
        self,
        persist_directory: str = "server/vector_store",
        collection_name: str = "special_education_standards"
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.vectorstore: Optional[Chroma] = None
        self.data_loader = DataLoader()

        # Ensure persist directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)

    def initialize_vector_store(self, force_recreate: bool = False) -> bool:
        """
        Initialize or recreate the vector store with achievement standards.

        Args:
            force_recreate: If True, delete existing store and recreate

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if vector store already exists
            if self.persist_directory.exists() and not force_recreate:
                self.logger.info("Vector store already exists, loading...")
                self.vectorstore = Chroma(
                    persist_directory=str(self.persist_directory),
                    embedding_function=self.embeddings,
                    collection_name=self.collection_name
                )
                return True

            # Delete existing store if force recreate
            if force_recreate and self.persist_directory.exists():
                import shutil
                shutil.rmtree(self.persist_directory)
                self.persist_directory.mkdir(parents=True, exist_ok=True)

            # Load documents from data files
            documents_data = self.data_loader.get_documents_for_embedding()

            if not documents_data:
                self.logger.warning("No documents found to embed")
                return False

            # Convert to LangChain documents
            documents = []
            for doc_data in documents_data:
                doc = Document(
                    page_content=doc_data["content"],
                    metadata=doc_data["metadata"]
                )
                documents.append(doc)

            self.logger.info(f"Creating vector store with {len(documents)} documents")

            # Create vector store
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=str(self.persist_directory),
                collection_name=self.collection_name
            )

            # Persist the vector store
            self.vectorstore.persist()

            self.logger.info("Vector store initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize vector store: {e}")
            return False

    def search_similar_standards(
        self,
        query: str,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        disability_type: Optional[str] = None,
        k: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar achievement standards using semantic search.

        Args:
            query: The search query (teacher/parent description)
            grade: Filter by grade
            subject: Filter by subject
            disability_type: Filter by disability type
            k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of relevant documents with metadata and scores
        """
        if not self.vectorstore:
            if not self.initialize_vector_store():
                return []

        try:
            # Build filter for metadata
            filter_dict = {}
            if grade:
                filter_dict["grade"] = grade
            if subject:
                filter_dict["subject"] = subject
            if disability_type:
                filter_dict["disability_type"] = disability_type

            filter_condition = filter_dict if filter_dict else None

            # Perform similarity search with score
            docs_and_scores = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_condition
            )

            # Filter by score threshold and format results
            results = []
            for doc, score in docs_and_scores:
                if score >= score_threshold:
                    result = {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": float(score),
                        "id": doc.metadata.get("id", "")
                    }
                    results.append(result)

            self.logger.info(f"Found {len(results)} relevant standards for query")
            return results

        except Exception as e:
            self.logger.error(f"Error during similarity search: {e}")
            return []

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the current vector store collection.

        Returns:
            Dictionary with collection statistics
        """
        if not self.vectorstore:
            return {"status": "not_initialized"}

        try:
            count = self.vectorstore._collection.count()
            return {
                "status": "initialized",
                "document_count": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory)
            }
        except Exception as e:
            self.logger.error(f"Error getting collection info: {e}")
            return {"status": "error", "error": str(e)}

    def delete_vector_store(self) -> bool:
        """
        Delete the entire vector store.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.persist_directory.exists():
                import shutil
                shutil.rmtree(self.persist_directory)
                self.vectorstore = None
                self.logger.info("Vector store deleted successfully")
                return True
            return True  # Already doesn't exist
        except Exception as e:
            self.logger.error(f"Error deleting vector store: {e}")
            return False

    @property
    def logger(self):
        return logger