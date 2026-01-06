"""
Embeddings Module - Vector embeddings using Ollama
Optimized for RTX 3060 Ti
"""
import requests
import json
import numpy as np
from typing import List, Optional
from pathlib import Path
import pickle

from .config import embedding_config, llm_config


class OllamaEmbeddings:
    """Generate embeddings using Ollama's embedding models"""
    
    def __init__(self, config=None):
        self.config = config or embedding_config
        self.base_url = llm_config.base_url
        self.model = self.config.model
        self.dimension = self.config.dimension
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=30
            )
            response.raise_for_status()
            embedding = response.json().get("embedding", [])
            return np.array(embedding, dtype=np.float32)
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama. Make sure it's running."
            )
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            emb = self.embed_text(text)
            embeddings.append(emb)
        return np.vstack(embeddings)
    
    def check_model_available(self) -> bool:
        """Check if embedding model is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(self.model in m.get("name", "") for m in models)
            return False
        except:
            return False


class FAISSIndex:
    """FAISS-based vector index for similarity search"""
    
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.index = None
        self.documents = []  # Store original documents
        self.metadata = []   # Store metadata for each document
        self._init_index()
    
    def _init_index(self):
        """Initialize FAISS index"""
        try:
            import faiss
            # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
            self.index = faiss.IndexFlatIP(self.dimension)
        except ImportError:
            raise ImportError(
                "FAISS not installed. Install with: pip install faiss-cpu"
            )
    
    def add(
        self, 
        embeddings: np.ndarray, 
        documents: List[str], 
        metadata: Optional[List[dict]] = None
    ):
        """Add embeddings to the index"""
        import faiss
        
        # Normalize vectors for cosine similarity
        faiss.normalize_L2(embeddings)
        
        self.index.add(embeddings)
        self.documents.extend(documents)
        
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{} for _ in documents])
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        k: int = 5
    ) -> List[tuple]:
        """Search for similar documents
        
        Returns:
            List of (document, score, metadata) tuples
        """
        import faiss
        
        # Normalize query vector
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents) and idx >= 0:
                results.append((
                    self.documents[idx],
                    float(score),
                    self.metadata[idx]
                ))
        
        return results
    
    def save(self, path: Path):
        """Save index to disk"""
        import faiss
        
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(path / "index.faiss"))
        
        # Save documents and metadata
        with open(path / "documents.pkl", "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "metadata": self.metadata,
                "dimension": self.dimension
            }, f)
    
    @classmethod
    def load(cls, path: Path) -> "FAISSIndex":
        """Load index from disk"""
        import faiss
        
        path = Path(path)
        
        # Load documents and metadata
        with open(path / "documents.pkl", "rb") as f:
            data = pickle.load(f)
        
        # Create instance
        instance = cls(dimension=data["dimension"])
        instance.documents = data["documents"]
        instance.metadata = data["metadata"]
        
        # Load FAISS index
        instance.index = faiss.read_index(str(path / "index.faiss"))
        
        return instance
    
    def __len__(self):
        return self.index.ntotal if self.index else 0


class TextChunker:
    """Split text into chunks for embedding"""
    
    def __init__(
        self, 
        chunk_size: int = 512, 
        chunk_overlap: int = 50
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for sep in ['. ', '.\n', '!\n', '?\n', '\n\n']:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > self.chunk_size // 2:
                        end = start + last_sep + len(sep)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
        
        return chunks
    
    def chunk_documents(
        self, 
        documents: List[str], 
        metadatas: Optional[List[dict]] = None
    ) -> tuple:
        """Chunk multiple documents, preserving metadata"""
        all_chunks = []
        all_metadata = []
        
        for i, doc in enumerate(documents):
            chunks = self.chunk_text(doc)
            all_chunks.extend(chunks)
            
            # Add metadata for each chunk
            base_meta = metadatas[i] if metadatas else {}
            for j, _ in enumerate(chunks):
                chunk_meta = {
                    **base_meta,
                    "chunk_index": j,
                    "total_chunks": len(chunks)
                }
                all_metadata.append(chunk_meta)
        
        return all_chunks, all_metadata


# Singleton instances
_embedder: Optional[OllamaEmbeddings] = None

def get_embedder() -> OllamaEmbeddings:
    """Get or create embedder instance"""
    global _embedder
    if _embedder is None:
        _embedder = OllamaEmbeddings()
    return _embedder


def embed_text(text: str) -> np.ndarray:
    """Convenience function to embed text"""
    return get_embedder().embed_text(text)


def embed_batch(texts: List[str]) -> np.ndarray:
    """Convenience function to embed multiple texts"""
    return get_embedder().embed_batch(texts)
