from app.core.embedder import embed_texts
from app.core.llm import ask_llm
from app.repositories.vector_repository import query_similar


def answer_query(question: str) -> str:
    query_embedding = embed_texts([question])[0]
    results = query_similar(query_embedding, n_results=3)
    context = "\n".join(results["documents"][0])
    return ask_llm(context, question)
