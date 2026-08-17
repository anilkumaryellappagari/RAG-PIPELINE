"""Retrieval-Augmented Generation pipeline."""

import os

from dotenv import load_dotenv
from groq import Groq

from retriever.embeddings import Embedder
from retriever.qdrant_store import QdrantStore


load_dotenv()


MODEL_NAME = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)


# Retrieve more chunks internally than the API limit.
INTERNAL_RETRIEVAL_LIMIT = 12


class RAGPipeline:

    def __init__(self) -> None:

        self.embedder = Embedder()

        self.store = QdrantStore()

        self.client = Groq(
            api_key=os.getenv(
                "GROQ_API_KEY"
            )
        )


    def answer(
        self,
        question: str,
        limit: int = 5,
        document_id: str | None = None,
    ) -> dict:
        """Answer a question using retrieved document context."""


        # ====================================================
        # VALIDATE QUESTION
        # ====================================================

        question = question.strip()

        if not question:

            raise ValueError(
                "Question cannot be empty"
            )


        # ====================================================
        # CREATE QUERY EMBEDDING
        # ====================================================

        query_vector = (
            self.embedder.embed_query(
                question
            )
        )


        # ====================================================
        # RETRIEVE MORE CANDIDATES
        # ====================================================

        retrieval_limit = max(
            limit,
            INTERNAL_RETRIEVAL_LIMIT,
        )


        results = self.store.search(
            query_vector=query_vector,
            limit=retrieval_limit,
            document_id=document_id,
        )


        # ====================================================
        # REMOVE EXACT DUPLICATE CHUNKS
        # ====================================================

        unique_results = []

        seen = set()


        for result in results:

            payload = result.payload or {}

            document_id_value = payload.get(
                "document_id"
            )

            chunk_id = payload.get(
                "chunk_id"
            )

            text = payload.get(
                "text",
                ""
            ).strip()


            unique_key = (
                document_id_value,
                chunk_id,
                text,
            )


            if unique_key in seen:

                continue


            seen.add(
                unique_key
            )

            unique_results.append(
                result
            )


        # ====================================================
        # BUILD CONTEXT
        # ====================================================

        context_parts = []


        for index, result in enumerate(
            unique_results,
            start=1,
        ):

            payload = result.payload or {}

            filename = payload.get(
                "filename",
                "Unknown document",
            )

            page_number = payload.get(
                "page_number",
                "Unknown",
            )

            text = payload.get(
                "text",
                "",
            ).strip()


            context_parts.append(
                f"""SOURCE {index}
Document: {filename}
Page: {page_number}

{text}
"""
            )


        context = "\n\n--------------------\n\n".join(
            context_parts
        )


        # ====================================================
        # NO RETRIEVED CONTEXT
        # ====================================================

        if not context:

            return {
                "answer": (
                    "I could not find relevant "
                    "information in the uploaded documents."
                ),
                "sources": [],
            }


        # ====================================================
        # LIMIT CONTEXT SENT TO MODEL
        # ====================================================

        selected_results = unique_results[
            :limit
        ]


        selected_context_parts = []


        for index, result in enumerate(
            selected_results,
            start=1,
        ):

            payload = result.payload or {}

            filename = payload.get(
                "filename",
                "Unknown document",
            )

            page_number = payload.get(
                "page_number",
                "Unknown",
            )

            text = payload.get(
                "text",
                "",
            ).strip()


            selected_context_parts.append(
                f"""SOURCE {index}
Document: {filename}
Page: {page_number}

{text}
"""
            )


        selected_context = (
            "\n\n--------------------\n\n".join(
                selected_context_parts
            )
        )


        # ====================================================
        # RAG PROMPT
        # ====================================================

        prompt = f"""
You are answering a question using a collection
of uploaded documents.

Use ONLY the information contained in the
SOURCE sections below.

Important rules:

1. Carefully read ALL provided sources before answering.

2. Combine information from multiple sources when
   the sources are related to the question.

3. Do not assume that the first source contains
   the complete answer.

4. Do not invent information that is not supported
   by the sources.

5. If the sources contain partial information,
   provide the supported information and clearly
   say what is not available.

6. When several sources describe the same topic,
   synthesize them into one clear answer.

7. Do not mention retrieval, embeddings, Qdrant,
   similarity scores, or internal system details
   unless the user asks about the RAG system itself.

8. Prefer specific details from the uploaded
   documents over general knowledge.

9. Answer the user's exact question directly.

SOURCE DOCUMENTS:

{selected_context}

USER QUESTION:

{question}
"""


        # ====================================================
        # CALL GROQ
        # ====================================================

        response = (
            self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise document-based "
                            "RAG assistant. "
                            "Answer using only the supplied "
                            "document sources."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0,
            )
        )


        answer = (
            response
            .choices[0]
            .message
            .content
        )


        # ====================================================
        # RETURN ANSWER + SOURCES
        # ====================================================

        return {
            "answer": answer,
            "sources": [
                {
                    "filename": (
                        result.payload.get(
                            "filename"
                        )
                    ),
                    "page": (
                        result.payload.get(
                            "page_number"
                        )
                    ),
                    "score": result.score,
                }
                for result in selected_results
            ],
        }
