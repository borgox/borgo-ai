"""
RAG Module - Retrieval Augmented Generation for borgo-ai
"""
from typing import List, Optional, Dict
from pathlib import Path
import json

from config import KNOWLEDGE_DIR, embedding_config
from embeddings import (
    FAISSIndex, 
    TextChunker, 
    get_embedder, 
    embed_text
)


class KnowledgeBase:
    """RAG Knowledge Base using FAISS"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.index_dir = KNOWLEDGE_DIR / name
        self.index: Optional[FAISSIndex] = None
        self.chunker = TextChunker(
            chunk_size=embedding_config.chunk_size,
            chunk_overlap=embedding_config.chunk_overlap
        )
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing index or create new one"""
        if (self.index_dir / "index.faiss").exists():
            try:
                self.index = FAISSIndex.load(self.index_dir)
            except Exception:
                self.index = FAISSIndex(dimension=embedding_config.dimension)
        else:
            self.index = FAISSIndex(dimension=embedding_config.dimension)
    
    def add_document(
        self, 
        content: str, 
        source: str = "unknown",
        metadata: Optional[dict] = None
    ):
        """Add a document to the knowledge base"""
        embedder = get_embedder()
        
        # Chunk the document
        chunks = self.chunker.chunk_text(content)
        
        if not chunks:
            return
        
        # Create metadata for each chunk
        base_meta = metadata or {}
        base_meta["source"] = source
        
        chunk_metadata = []
        for i, chunk in enumerate(chunks):
            chunk_metadata.append({
                **base_meta,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })
        
        # Generate embeddings
        embeddings = embedder.embed_batch(chunks)
        
        # Add to index
        self.index.add(embeddings, chunks, chunk_metadata)
        
        # Save index
        self.save()
    
    def add_documents(
        self, 
        documents: List[str], 
        sources: Optional[List[str]] = None,
        metadatas: Optional[List[dict]] = None
    ):
        """Add multiple documents"""
        for i, doc in enumerate(documents):
            source = sources[i] if sources else f"doc_{i}"
            metadata = metadatas[i] if metadatas else None
            self.add_document(doc, source, metadata)
    
    def query(
        self, 
        query: str, 
        k: int = 5,
        threshold: float = 0.5
    ) -> List[Dict]:
        """Query the knowledge base"""
        if len(self.index) == 0:
            return []
        
        # Generate query embedding
        query_embedding = embed_text(query)
        
        # Search
        results = self.index.search(query_embedding, k)
        
        # Filter by threshold and format
        formatted_results = []
        for doc, score, metadata in results:
            if score >= threshold:
                formatted_results.append({
                    "content": doc,
                    "score": score,
                    "metadata": metadata
                })
        
        return formatted_results
    
    def save(self):
        """Save the index"""
        self.index.save(self.index_dir)
    
    def clear(self):
        """Clear all documents"""
        self.index = FAISSIndex(dimension=embedding_config.dimension)
        self.save()
    
    def __len__(self):
        return len(self.index)


class RAGEngine:
    """RAG Engine combining retrieval and generation"""
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        self.kb = knowledge_base or KnowledgeBase()
    
    def build_prompt(
        self, 
        query: str, 
        context: str = "",
        conversation_history: Optional[List[Dict]] = None,
        max_context_length: int = 3000
    ) -> str:
        """Build a RAG prompt with retrieved context"""
        
        # Get relevant documents from knowledge base
        kb_results = self.kb.query(query, k=3)
        
        # Build context section
        context_parts = []
        
        # Add web search context if provided
        if context:
            context_parts.append("### Web Search Results:")
            context_parts.append(context[:max_context_length // 2])
        
        # Add knowledge base context
        if kb_results:
            context_parts.append("\n### From Knowledge Base:")
            for i, result in enumerate(kb_results):
                source = result["metadata"].get("source", "unknown")
                context_parts.append(f"[Source: {source}]")
                context_parts.append(result["content"])
                context_parts.append("")
        
        context_text = "\n".join(context_parts)
        
        # Truncate if needed
        if len(context_text) > max_context_length:
            context_text = context_text[:max_context_length] + "..."
        
        # Build final prompt
        if context_text.strip():
            prompt = f"""Use the following context to answer the user's question. If the context doesn't contain relevant information, use your own knowledge but mention that.

### Context:
{context_text}

### User Question:
{query}

### Instructions:
- Answer based on the provided context when relevant
- Be concise but comprehensive
- If you're not sure about something, say so
- Format your response clearly

### Answer:"""
        else:
            prompt = query
        
        return prompt
    
    def add_to_knowledge(
        self, 
        content: str, 
        source: str = "user"
    ):
        """Add content to knowledge base"""
        self.kb.add_document(content, source)


def build_rag_prompt(
    query: str, 
    context: str = "",
    kb_name: str = "default"
) -> str:
    """Convenience function to build RAG prompt"""
    kb = KnowledgeBase(kb_name)
    engine = RAGEngine(kb)
    return engine.build_prompt(query, context)


def add_knowledge(
    content: str, 
    source: str = "user",
    kb_name: str = "default"
):
    """Add content to knowledge base"""
    kb = KnowledgeBase(kb_name)
    kb.add_document(content, source)


def query_knowledge(
    query: str, 
    k: int = 5,
    kb_name: str = "default"
) -> List[Dict]:
    """Query knowledge base"""
    kb = KnowledgeBase(kb_name)
    return kb.query(query, k)
