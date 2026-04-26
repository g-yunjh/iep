"""RAG Service for managing vector store operations.
Handles initialization, embedding, and retrieval for curriculum and career data.
Supports multiple collections (curriculum, career) for different RAG use cases.
"""

import logging
import os
import re
import shutil
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .data_loader import DataLoader

logger = logging.getLogger(__name__)


def _google_api_key() -> Optional[str]:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


# Collection names
COLLECTION_CURRICULUM = "curriculum_standards"
COLLECTION_CAREER = "career_data"


class RAGService:
    """
    Service for managing vector store operations for special education RAG system.
    Supports multiple collections for different data types (curriculum, career).
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = COLLECTION_CURRICULUM
    ):
        self.project_root = Path(__file__).resolve().parents[3]
        self.server_root = self.project_root / "server"
        default_persist_dir = self.server_root / "vector_store"
        self.persist_directory = (
            Path(persist_directory).expanduser().resolve()
            if persist_directory
            else default_persist_dir.resolve()
        )
        self.collection_name = collection_name
        embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001")
        self.embedding_model = embedding_model
        api_key = _google_api_key()
        if not api_key:
            raise ValueError(
                "API key required for Gemini embeddings. "
                "Set GOOGLE_API_KEY or GEMINI_API_KEY in environment (or .env)."
            )
        self.api_key = api_key
        self.embeddings = self._create_embeddings(embedding_model)
        self.vectorstore: Optional[Chroma] = None
        self.data_loader = DataLoader(data_dir=str(self.server_root / "data"))

        # Ensure persist directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.logger.info("RAG persist directory resolved: %s", self.persist_directory)

    def _get_collection_dir(self, collection_name: str) -> Path:
        """Get the directory for a specific collection."""
        return self.persist_directory / collection_name

    def _create_embeddings(self, model_name: str) -> GoogleGenerativeAIEmbeddings:
        """Create embedding client for a given model name."""
        return GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=self.api_key,
        )

    def _safe_remove_dir(self, target_dir: Path, retries: int = 5, delay_sec: float = 0.4) -> None:
        """Remove directory with retries to tolerate Windows sqlite file locks."""
        # Release references that may keep sqlite file handles open.
        self.vectorstore = None
        last_error = None
        for _ in range(retries):
            try:
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                return
            except Exception as e:
                last_error = e
                time.sleep(delay_sec)
        if last_error:
            raise last_error

    def _is_quota_exhausted_error(self, error: Exception) -> bool:
        """Return True when Gemini request failed due to quota/rate limits."""
        error_text = str(error).upper()
        return "RESOURCE_EXHAUSTED" in error_text or "QUOTA" in error_text or "429" in error_text

    def _extract_retry_delay_seconds(self, error: Exception, default_delay: float = 15.0) -> float:
        """
        Extract suggested retry delay from Gemini error text.
        Example: 'Please retry in 13.416026615s.'
        """
        error_text = str(error)
        match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", error_text, flags=re.IGNORECASE)
        if not match:
            return default_delay
        try:
            return max(float(match.group(1)), 1.0)
        except ValueError:
            return default_delay

    def _run_with_quota_retry(self, operation_name: str, action, max_attempts: int = 3):
        """Run a Gemini-dependent action with quota-aware retries."""
        for attempt in range(1, max_attempts + 1):
            try:
                return action()
            except Exception as e:
                if not self._is_quota_exhausted_error(e) or attempt == max_attempts:
                    raise
                delay_sec = self._extract_retry_delay_seconds(e)
                self.logger.warning(
                    "Gemini quota/rate limit during %s (attempt %d/%d): %s. "
                    "Retrying in %.1f seconds.",
                    operation_name,
                    attempt,
                    max_attempts,
                    str(e),
                    delay_sec,
                )
                time.sleep(delay_sec)

    def initialize_vector_store(
        self,
        data_type: str = "curriculum",
        force_recreate: bool = False
    ) -> bool:
        """
        Initialize or recreate the vector store with specified data type.

        Args:
            data_type: Type of data ("curriculum" or "career")
            force_recreate: If True, delete existing store and recreate

        Returns:
            True if successful, False otherwise
        """
        # Set collection name based on data type
        if data_type == "career":
            self.collection_name = COLLECTION_CAREER
        else:
            self.collection_name = COLLECTION_CURRICULUM

        collection_dir = self._get_collection_dir(self.collection_name)
        had_existing_store = collection_dir.exists()
        collection_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Validate Gemini embedding call early so failures are explicit.
            try:
                self.embeddings.embed_query("ping")
                self.logger.info("Using Gemini embedding model: %s", self.embedding_model)
            except Exception as e:
                error_text = str(e)
                error_type = e.__class__.__name__
                self.logger.error(
                    "Gemini embedding validation failed (%s): %s. "
                    "Check API key validity, Gemini API access, and network connectivity.",
                    error_type,
                    error_text,
                )
                return False

            # Check if vector store already exists
            if had_existing_store and not force_recreate:
                self.logger.info(f"Vector store for {data_type} already exists, loading...")
                self.vectorstore = Chroma(
                    persist_directory=str(collection_dir),
                    embedding_function=self.embeddings,
                    collection_name=self.collection_name
                )
                existing_count = self.vectorstore._collection.count()
                if existing_count > 0:
                    return True
                self.logger.info(
                    "Existing vector store for %s is empty. Rebuilding embeddings.",
                    data_type,
                )

            # Delete existing store if force recreate
            if force_recreate and collection_dir.exists():
                self._safe_remove_dir(collection_dir)
                collection_dir.mkdir(parents=True, exist_ok=True)

            # Load documents from data files
            documents_data = self.data_loader.get_documents_for_embedding(data_type)

            if not documents_data:
                self.logger.warning(f"No documents found to embed for {data_type}")
                return False

            # Convert to LangChain documents
            documents = []
            for doc_data in documents_data:
                doc = Document(
                    page_content=doc_data["content"],
                    metadata=doc_data["metadata"]
                )
                documents.append(doc)

            self.logger.info(f"Creating vector store with {len(documents)} documents for {data_type}")

            # Create vector store (auto-persisted by Chroma 0.4+)
            # Career data can be large, so ingest in batches to stay within free-tier quotas.
            if data_type == "career":
                batch_size = int(os.getenv("RAG_CAREER_BATCH_SIZE", "10"))
                batch_size = max(1, batch_size)
                inter_batch_delay_sec = float(os.getenv("RAG_CAREER_BATCH_DELAY_SEC", "8"))
                inter_batch_delay_sec = max(0.0, inter_batch_delay_sec)
                first_batch = documents[:batch_size]
                remaining_docs = documents[batch_size:]
                total_batches = 1 + ((len(remaining_docs) + batch_size - 1) // batch_size)

                self.logger.info(
                    "Career ingestion in %d batches (batch_size=%d, batch_delay=%.1fs, total_docs=%d)",
                    total_batches,
                    batch_size,
                    inter_batch_delay_sec,
                    len(documents),
                )

                self.vectorstore = self._run_with_quota_retry(
                    operation_name=f"{data_type} vector store initial batch creation",
                    action=lambda: Chroma.from_documents(
                        documents=first_batch,
                        embedding=self.embeddings,
                        persist_directory=str(collection_dir),
                        collection_name=self.collection_name,
                    ),
                )

                for batch_index, start in enumerate(range(0, len(remaining_docs), batch_size), start=2):
                    batch_docs = remaining_docs[start:start + batch_size]
                    self.logger.info(
                        "Adding career batch %d/%d (%d docs)",
                        batch_index,
                        total_batches,
                        len(batch_docs),
                    )
                    self._run_with_quota_retry(
                        operation_name=f"{data_type} vector store batch add {batch_index}/{total_batches}",
                        action=lambda docs=batch_docs: self.vectorstore.add_documents(docs),
                    )
                    if inter_batch_delay_sec > 0 and batch_index < total_batches:
                        self.logger.info(
                            "Sleeping %.1f seconds before next career batch to avoid quota spikes.",
                            inter_batch_delay_sec,
                        )
                        time.sleep(inter_batch_delay_sec)
            else:
                self.vectorstore = self._run_with_quota_retry(
                    operation_name=f"{data_type} vector store creation",
                    action=lambda: Chroma.from_documents(
                        documents=documents,
                        embedding=self.embeddings,
                        persist_directory=str(collection_dir),
                        collection_name=self.collection_name
                    ),
                )

            self.logger.info(f"Vector store for {data_type} initialized successfully")
            return True

        except Exception as e:
            self.logger.error(
                "Failed to initialize vector store for %s (%s): %s",
                data_type,
                e.__class__.__name__,
                str(e),
            )
            return False

    def initialize_all_stores(self, force_recreate: bool = False) -> Dict[str, bool]:
        """
        Initialize all vector stores (curriculum and career).

        Args:
            force_recreate: If True, delete existing stores and recreate

        Returns:
            Dictionary with initialization status for each data type
        """
        results = {}
        
        # Initialize curriculum store
        results["curriculum"] = self.initialize_vector_store("curriculum", force_recreate)

        # Free-tier embed quota is per-minute. Cool down before large career ingestion.
        cooldown_sec = float(os.getenv("RAG_INTER_STORE_COOLDOWN_SEC", "65"))
        cooldown_sec = max(0.0, cooldown_sec)
        if cooldown_sec > 0:
            self.logger.info(
                "Sleeping %.1f seconds between curriculum and career initialization.",
                cooldown_sec,
            )
            time.sleep(cooldown_sec)

        # Initialize career store
        results["career"] = self.initialize_vector_store("career", force_recreate)
        
        return results

    def search_similar(
        self,
        query: str,
        data_type: str = "curriculum",
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        disability_type: Optional[str] = None,
        k: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using semantic search.

        Args:
            query: The search query
            data_type: Type of data to search ("curriculum" or "career")
            grade: Filter by grade (curriculum only)
            subject: Filter by subject (curriculum only)
            disability_type: Filter by disability type (curriculum only)
            k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of relevant documents with metadata and scores
        """
        # Set collection based on data type
        if data_type == "career":
            self.collection_name = COLLECTION_CAREER
        else:
            self.collection_name = COLLECTION_CURRICULUM

        collection_dir = self._get_collection_dir(self.collection_name)

        try:
            # Load existing vector store
            if collection_dir.exists():
                self.vectorstore = Chroma(
                    persist_directory=str(collection_dir),
                    embedding_function=self.embeddings,
                    collection_name=self.collection_name
                )
            else:
                # Initialize if not exists
                if not self.initialize_vector_store(data_type):
                    return []

            # Build filter for metadata
            filter_dict = {}
            if data_type == "curriculum":
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

            self.logger.info(f"Found {len(results)} relevant documents for {data_type} query")
            return results

        except Exception as e:
            self.logger.error(f"Error during similarity search: {e}")
            return []

    def search_curriculum(
        self,
        query: str,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        disability_type: Optional[str] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search curriculum standards."""
        return self.search_similar(
            query=query,
            data_type="curriculum",
            grade=grade,
            subject=subject,
            disability_type=disability_type,
            k=k
        )

    def search_career(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search career data."""
        return self.search_similar(
            query=query,
            data_type="career",
            k=k
        )

    def get_collection_info(self, data_type: str = "curriculum") -> Dict[str, Any]:
        """
        Get information about the vector store collection.

        Args:
            data_type: Type of data ("curriculum" or "career")

        Returns:
            Dictionary with collection statistics
        """
        if data_type == "career":
            self.collection_name = COLLECTION_CAREER
        else:
            self.collection_name = COLLECTION_CURRICULUM

        collection_dir = self._get_collection_dir(self.collection_name)

        if not collection_dir.exists():
            return {"status": "not_initialized", "data_type": data_type}

        try:
            self.vectorstore = Chroma(
                persist_directory=str(collection_dir),
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            count = self.vectorstore._collection.count()
            status = "initialized" if count > 0 else "empty"
            return {
                "status": status,
                "document_count": count,
                "collection_name": self.collection_name,
                "data_type": data_type,
                "persist_directory": str(collection_dir)
            }
        except Exception as e:
            self.logger.error(f"Error getting collection info: {e}")
            return {"status": "error", "error": str(e), "data_type": data_type}

    def get_all_collections_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all collections."""
        return {
            "curriculum": self.get_collection_info("curriculum"),
            "career": self.get_collection_info("career")
        }

    def delete_vector_store(self, data_type: Optional[str] = None) -> bool:
        """
        Delete vector store(s).

        Args:
            data_type: Type of data to delete ("curriculum", "career", or None for all)

        Returns:
            True if successful, False otherwise
        """
        try:
            if data_type:
                # Delete specific collection
                if data_type == "career":
                    self.collection_name = COLLECTION_CAREER
                else:
                    self.collection_name = COLLECTION_CURRICULUM
                
                collection_dir = self._get_collection_dir(self.collection_name)
                if collection_dir.exists():
                    self._safe_remove_dir(collection_dir)
                    self.logger.info(f"Vector store for {data_type} deleted successfully")
            else:
                # Delete all
                if self.persist_directory.exists():
                    self._safe_remove_dir(self.persist_directory)
                    self.persist_directory.mkdir(parents=True, exist_ok=True)
                    self.logger.info("All vector stores deleted successfully")
            
            self.vectorstore = None
            return True

        except Exception as e:
            self.logger.error(f"Error deleting vector store: {e}")
            return False

    @property
    def logger(self):
        return logger