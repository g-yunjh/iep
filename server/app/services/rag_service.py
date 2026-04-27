"""RAG Service for managing vector store operations.
Handles initialization, embedding, and retrieval for curriculum and career data.
Supports multiple collections (curriculum, career) for different RAG use cases.
"""

import logging
import os
import shutil
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from .data_loader import DataLoader

logger = logging.getLogger(__name__)


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
        embedding_model = os.getenv("LOCAL_EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
        self.embedding_model = embedding_model
        self.embeddings = self._create_embeddings(embedding_model)
        self.vectorstore: Optional[Chroma] = None
        self.data_loader = DataLoader(data_dir=str(self.server_root / "data"))

        # Ensure persist directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.logger.info("RAG persist directory resolved: %s", self.persist_directory)

    def _get_collection_dir(self, collection_name: str) -> Path:
        """Get the directory for a specific collection."""
        return self.persist_directory / collection_name

    def _create_embeddings(self, model_name: str) -> HuggingFaceEmbeddings:
        """Create local embedding client for a given model name."""
        try:
            return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception as e:
            fallback_model = "jhgan/ko-sroberta-multitask"
            if model_name == fallback_model:
                raise
            self.logger.warning(
                "Failed to load local embedding model '%s' (%s). Falling back to '%s'.",
                model_name,
                str(e),
                fallback_model,
            )
            self.embedding_model = fallback_model
            return HuggingFaceEmbeddings(
                model_name=fallback_model,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
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

    def _load_documents_for_data_type(self, data_type: str) -> List[Dict[str, Any]]:
        """
        Load documents for embedding with curriculum directory priority.

        For curriculum, prefer `data/curriculum/**.json` files and only fallback
        to the legacy combined loader when the directory-based source is empty.
        """
        documents: List[Dict[str, Any]] = []

        if data_type == "curriculum":
            curriculum_standards = self.data_loader.load_curriculum_from_directory()
            for standard in curriculum_standards:
                documents.append(standard.to_document())

            if documents:
                self.logger.info(
                    "Loaded %d curriculum documents from curriculum directory.",
                    len(documents),
                )
                return documents

            self.logger.warning(
                "No curriculum files found under curriculum directory. "
                "Falling back to legacy curriculum loader."
            )
            return self.data_loader.get_documents_for_embedding("curriculum")

        if data_type == "career":
            career_data = self.data_loader.load_all_careers()
            for career in career_data:
                documents.append(career.to_document())
            return documents

        return self.data_loader.get_documents_for_embedding(data_type)

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
            # Validate local embedding model call early so failures are explicit.
            try:
                self.embeddings.embed_query("ping")
                self.logger.info("Using local embedding model: %s", self.embedding_model)
            except Exception as e:
                error_text = str(e)
                error_type = e.__class__.__name__
                self.logger.error(
                    "Local embedding model validation failed (%s): %s. "
                    "Check model download/cache and runtime environment.",
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
            documents_data = self._load_documents_for_data_type(data_type)

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

            # Create vector store in a single pass (auto-persisted by Chroma 0.4+)
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=str(collection_dir),
                collection_name=self.collection_name
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