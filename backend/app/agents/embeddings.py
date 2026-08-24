from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings


embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.gemini_api_key,
    output_dimensionality=768,
)


def embed_documents(texts: list[str]) -> list[list[float]]:
    return embeddings.embed_documents(texts)


def embed_query(text: str) -> list[float]:
    return embeddings.embed_query(text)


        #         UPLOAD PDF
        #             ↓
        #      Extract the text
        #             ↓
        #       Split into chunks
        #             ↓
        #   embed_documents(chunks)
        #             ↓
        #   Gemini Embedding Model
        #             ↓
        # 768-dimensional vectors
        #             ↓
        #       PostgreSQL
        #        pgvector
        #             ↓
        #      Store chunks


    #             USER QUESTION
    #                 ↓
    #     embed_query(question)
    #                 ↓
    #       Gemini Embedding Model
    #                 ↓
    #     768-dimensional vector
    #                 ↓
    #    Search pgvector for similar
    #            chunks
    #                 ↓
    #       Relevant DocumentChunks
    #                 ↓
    #     Question + relevant chunks
    #                 ↓
    #             Gemini LLM
    #                 ↓
    #            Final Answer