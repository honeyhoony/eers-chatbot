"""
rag.py - Supabase pgvector 기반 RAG(Retrieval Augmented Generation) 파이프라인
"""
import os
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"


def get_embedding(text: str) -> list[float]:
    """텍스트를 임베딩 벡터로 변환합니다."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def store_chunks(chunks: list[str], source_filename: str):
    """텍스트 청크들을 임베딩하여 Supabase에 저장합니다."""
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        supabase.table("documents").insert({
            "content": chunk,
            "metadata": {
                "source": source_filename,
                "chunk_index": i
            },
            "embedding": embedding
        }).execute()


def search_similar(query: str, match_count: int = 5) -> list[dict]:
    """쿼리와 유사한 문서 청크를 검색합니다."""
    query_embedding = get_embedding(query)

    result = supabase.rpc("match_documents", {
        "query_embedding": query_embedding,
        "match_count": match_count
    }).execute()

    return result.data


def generate_answer(query: str, context_docs: list[dict]) -> str:
    """검색된 문서를 기반으로 답변을 생성합니다."""
    # 컨텍스트 조립
    context_parts = []
    for doc in context_docs:
        source = doc.get("metadata", {}).get("source", "알 수 없음")
        context_parts.append(f"[출처: {source}]\n{doc['content']}")

    context = "\n\n---\n\n".join(context_parts)

    system_prompt = """당신은 한국전력공사(KEPCO) 에너지효율향상의무화제도(EERS) 전문 상담 챗봇입니다.
주어진 참고 문서를 기반으로 정확하고 친절하게 답변해주세요.

규칙:
1. 반드시 제공된 참고 문서의 내용을 기반으로 답변하세요.
2. 참고 문서에 없는 내용은 "해당 내용은 현재 등록된 문서에서 찾을 수 없습니다"라고 안내하세요.
3. 답변 마지막에 참고한 문서의 출처를 표시하세요.
4. 한국어로 답변하세요.
"""

    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"참고 문서:\n{context}\n\n질문: {query}"}
        ],
        temperature=0.3,
        max_tokens=1500
    )

    return response.choices[0].message.content


def ask(query: str) -> str:
    """전체 RAG 파이프라인: 검색 → 답변 생성"""
    docs = search_similar(query)

    if not docs:
        return "등록된 문서에서 관련 내용을 찾을 수 없습니다. 관리자에게 문서 업로드를 요청해주세요."

    return generate_answer(query, docs)
