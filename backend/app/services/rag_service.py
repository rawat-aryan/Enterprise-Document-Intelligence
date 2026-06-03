from __future__ import annotations

import logging
from typing import Optional

from backend.app.config import settings

logger = logging.getLogger(__name__)


class RAGResult:
    def __init__(self, answer: str, sources: list[dict], context: str = ""):
        self.answer = answer
        self.sources = sources
        self.context = context


class RAGService:
    def __init__(self):
        self._collection = None
        self._embeddings = None
        self._llm = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            return self._collection
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            return None

    def _get_embeddings(self):
        if self._embeddings is not None:
            return self._embeddings
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.GEMINI_EMBEDDING_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
            )
            return self._embeddings
        except Exception as e:
            logger.warning(f"Gemini embeddings unavailable: {e}")
            return None

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            # Try to break at sentence boundary
            last_period = chunk.rfind(".")
            if last_period > chunk_size * 0.7:
                chunk = chunk[: last_period + 1]
            chunks.append(chunk.strip())
            start += len(chunk) - overlap
        return [c for c in chunks if c]

    async def add_document(self, document_id: str, text: str, metadata: dict | None = None) -> bool:
        """Add document chunks to ChromaDB."""
        collection = self._get_collection()
        if collection is None:
            logger.warning("ChromaDB not available, skipping RAG indexing")
            return False

        try:
            chunks = self._chunk_text(text)
            embeddings_fn = self._get_embeddings()

            ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
            chunk_metadata = [
                {**(metadata or {}), "document_id": document_id, "chunk_index": i} for i in range(len(chunks))
            ]

            if embeddings_fn:
                embeddings = embeddings_fn.embed_documents(chunks)
                collection.upsert(
                    ids=ids,
                    documents=chunks,
                    metadatas=chunk_metadata,
                    embeddings=embeddings,
                )
            else:
                # Let ChromaDB handle embeddings
                collection.upsert(
                    ids=ids,
                    documents=chunks,
                    metadatas=chunk_metadata,
                )
            logger.info(f"Indexed {len(chunks)} chunks for document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add document to RAG: {e}")
            return False

    async def query(self, question: str, n_results: int = 5, tenant_id: Optional[str] = None) -> RAGResult:
        """Query the RAG system and get an answer."""
        collection = self._get_collection()
        if collection is None:
            return RAGResult(
                answer="Document search is not available at this time.",
                sources=[],
            )

        try:
            where = {"tenant_id": tenant_id} if tenant_id else None
            results = collection.query(
                query_texts=[question],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            if not docs:
                return RAGResult(answer="No relevant documents found.", sources=[])

            context = "\n\n---\n\n".join(docs)
            answer = await self._generate_answer(question, context)

            sources = [
                {
                    "document_id": m.get("document_id", ""),
                    "chunk_index": m.get("chunk_index", 0),
                    "relevance_score": 1 - d,
                    "preview": doc[:200],
                }
                for doc, m, d in zip(docs, metas, distances)
            ]

            return RAGResult(answer=answer, sources=sources, context=context)

        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return RAGResult(answer=f"Query failed: {str(e)}", sources=[])

    async def _generate_answer(self, question: str, context: str) -> str:
        try:
            import google.generativeai as genai

            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)

            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            prompt = f"""You are an enterprise document assistant.
Answer the question based ONLY on the provided context.
If the answer is not in the context, say "I don't have enough information."

Context:
{context[:3000]}

Question: {question}

Answer:"""
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            # Fall back to extractive answer
            lines = context.split("\n")
            question_words = set(question.lower().split())
            best_line = max(
                lines,
                key=lambda ln: len(set(ln.lower().split()) & question_words),
                default="",
            )
            return best_line.strip() or "Unable to generate answer."

    async def get_relevant_chunks(self, query: str, n_results: int = 3) -> list[str]:
        """Get raw relevant text chunks for a query."""
        collection = self._get_collection()
        if collection is None:
            return []
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents"],
            )
            return results.get("documents", [[]])[0]
        except Exception as e:
            logger.error(f"Chunk retrieval failed: {e}")
            return []

    async def delete_document(self, document_id: str) -> bool:
        """Remove all chunks for a document from ChromaDB."""
        collection = self._get_collection()
        if collection is None:
            return False
        try:
            collection.delete(where={"document_id": document_id})
            return True
        except Exception as e:
            logger.error(f"Failed to delete document from RAG: {e}")
            return False


rag_service = RAGService()
