"""
rag.py - Supabase pgvector 기반 RAG(Retrieval Augmented Generation) 파이프라인
"""
import os
import json

# ====== httpx ASCII 인코딩 버그 패치 ======
import httpx._models as _hm
_orig_normalize = _hm._normalize_header_value
def _safe_normalize(value, encoding=None):
    if isinstance(value, bytes):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Header value must be str or bytes, not {type(value)}")
    safe_value = value.encode("ascii", errors="ignore").decode("ascii")
    return safe_value.encode("ascii")
_hm._normalize_header_value = _safe_normalize
# ====== 패치 끝 ======

from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(override=True)


def get_secret(key: str) -> str:
    """환경변수 읽기 (오직 .env만 사용)"""
    return os.getenv(key)


# Clients
openai_client = OpenAI(api_key=get_secret("OPENAI_API_KEY"))
supabase: Client = create_client(
    get_secret("SUPABASE_URL"),
    get_secret("SUPABASE_SERVICE_KEY")
)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_SERVICE_KEY")

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
SIMILARITY_THRESHOLD = 0.25  # 검색 민감도 완화 (더 많은 문서 검색)


def get_embedding(text: str) -> list[float]:
    """텍스트를 임베딩 벡터로 변환합니다."""
    # 한국어는 토큰이 많으므로 6000자로 제한 (약 8000토큰)
    truncated = text[:6000] if len(text) > 6000 else text
    # 빈 텍스트 방지
    if not truncated.strip():
        truncated = "empty"
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=truncated
    )
    return response.data[0].embedding


def store_chunks(chunks: list[str], source_filename: str):
    """청크 리스트를 임베딩하여 Supabase에 저장합니다."""
    # ... (생략 - upload_docs.py에서 직접 처리하므로 여기서는 사용 안 함)
    pass


def search_similar(query: str, match_count: int = 10) -> list[dict]:  # 검색 개수 10개로 증가
    """쿼리와 유사한 문서 청크를 검색합니다."""
    query_embedding = get_embedding(query)

    # RPC 호출 시 match_threshold 제거 (DB 함수 시그니처 불일치 해결)
    result = supabase.rpc("match_documents", {
        "query_embedding": query_embedding,
        "match_count": match_count
    }).execute()

    return result.data if result.data else []


from duckduckgo_search import DDGS

def search_web(query: str) -> str:
    """DuckDuckGo 검색을 통해 정보를 찾습니다."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"한국전력 {query}", region="kr-kr", max_results=3))
            if not results:
                return ""
            
            web_context = "\n".join([f"- {r['title']}: {r['body']} ({r['href']})" for r in results])
            return web_context
    except Exception as e:
        print(f"Web Search Error: {e}")
        return ""


def generate_answer(query: str, context_docs: list[dict], web_context: str = "") -> str:
    """검색된 문서를 기반으로 답변을 생성합니다."""
    # 컨텍스트 조립 (길이 제한 적용)
    context_parts = []
    current_length = 0
    max_length = 15000  # 약 2~3만 토큰 방지
    
    for doc in context_docs:
        content = doc['content']
        if current_length + len(content) > max_length:
            break
        context_parts.append(content)
        current_length += len(content)
        
    context = "\n\n---\n\n".join(context_parts)
    
    # 웹 검색 결과가 있으면 추가
    if web_context:
        context += f"\n\n[웹 검색 결과]\n{web_context}\n\n⚠️ 위 웹 검색 결과는 KEPCO 공식 문서가 아닐 수 있으니 참고용으로만 활용하세요."

    system_prompt = """당신은 한국전력공사(KEPCO) 대구본부 효율향상사업 AI 상담원입니다.
주어진 참고 문서를 기반으로 **정확하고 친절하게** 답변해주세요.

[핵심 규칙]
1. 제공된 참고 문서를 최우선으로 활용하되, **문서에서 내용을 찾을 수 없거나 '지원금', '서류', '담당자' 관련 기본 질문인 경우 아래 [기본 지식]을 활용하여 상세히 답변하세요.** (무조건 답변 제공)
2. **지원금(지원단가):** 문서에 없더라도 아래 표를 기반으로 반드시 마크다운 표로 답변하세요.
3. **담당자 연락처:** 
    - 사용자가 담당자 연락처를 물어보면, **"화면의 [📞 담당자 연락처 찾기] 버튼을 눌러 팝업에서 관할 사업소를 선택해주세요."** 라고 안내하세요.
    - 또는 **'[📞 연락처] 탭에서 전체 담당자 목록을 확인하실 수 있습니다.'**라고 안내하세요.
    - 모든 연락처를 나열하지 마세요.
4. **필요 서류:** 공고문 확인을 최우선으로 유도하되, 일반적인 서류(신청서, 사업자등록증, 통장사본 등)를 안내하세요.
5. **웹 검색 결과 활용:** 문서에 내용이 없고 웹 검색 결과가 제공된 경우, 이를 참고하여 답변하되 **"웹 검색 결과에 따르면..."** 이라고 출처를 명시하세요.
6. **동문서답 금지:**
    - 질문과 관련 없는 문서 내용은 무시하세요.
    - 특히 '사회복지시설', '소상공인' 등 특정 대상 질문 시, 해당 대상과 관련 없는 일반 기기(인버터, LED 등)의 지원금을 섞어서 답변하지 마세요.
    - **자신 없으면 "해당 내용은 공고문에서 정확한 확인이 필요합니다."라고 솔직하게 말하세요.** 잘못된 정보를 지어내지 마세요.

[기본 지식: 주요 기기 지원금 (2026년 기준)]
| 기기명 | 구분 | 지원금(단가) | 비고 |
| :--- | :--- | :--- | :--- |
| **고효율 LED** | 0.4kW 이상 절감 | **77,000원/kW** | - |
| **스마트 LED** | 스마트조명제어 | **77,000원/kW** | - |
| **회생제동장치** | 장치 / 제어반 | **50,000원 / 30,000원(대)** | (한도 1억) |
| **사출성형기** | 절감전력 기준 | **315,000원/kW** | - |
| **프리미엄 전동기**| 절감전력 기준 | **900,000원/kW** | - |
| **고효율 냉동기** | 원심식 / 스크루 | **13,500 / 33,100원(USRT)**| - |
| **시설원예 히트펌프**| - | **57,000원/kW** | - |
| **고효율 변압기** | 용량별 정액 | **160만원 ~ 590만원** | 공고문 참조 |
| **인버터/압축기/펌프**| 용량별 상이 | **공고문 내 표 참조** | - |

[기본 지식: 필요 서류 (공통)]
1. 효율향상사업 지원신청서
2. 사업자등록증 사본
3. 통장사본 (법인/대표자 명의)
4. 설치 전/후 현장 사진
5. 기타 기기별 필수 서류 (설치계획서, 시험성적서 등은 **신청서류 파일** 및 **공고문** 참조)

[기본 지식: 관할 지사 대표 전화번호]
- 직할/중구/북구: 053-210-2255
- 동대구/수성구: 053-740-3233
- 서대구/서구/남구: 053-570-2233
- 남대구/달서구/달성: 053-620-3233
- 경산/청도: 053-810-2233
- 경주: 054-770-2233
- 김천: 054-420-2233
- 구미: 054-460-2233
- 칠곡: 054-970-2233
- 성주/고령: 054-930-2233
- 영천: 054-330-2233
- 포항: 054-270-2233
- 영덕: 054-730-2233
- 상주/문경: 054-530-2233
- **정확한 담당자 직통 번호는 '한국전력공사 관할 사업소 문의처.pdf' 파일을 참고하거나 위 대표번호로 문의 바랍니다.**

[답변 형식]
- **문서 내용이 있으면 그것을 우선**하세요.
- **문서가 없어도** 위 [기본 지식]을 바탕으로 "문서에서는 찾을 수 없으나, 일반적인 기준은 다음과 같습니다."라고 답변하세요.
- '등록된 문서에서 찾을 수 없습니다'라는 답변은 **절대 금지**입니다.
- **기기의 정의(개념), 상세 기술적 내용, 또는 에너지 절감 효과(산출 근거)**를 물어볼 경우, **'★260127_설비효율향상사업 업무절차서_전문_6차.pdf'** 파일 내용을 참고하여 설명하세요.
- **문서와 기본 지식에도 없는 내용**일 경우 웹 검색 결과를 참고하여 답변하세요.
- 'EERS'라는 단어는 사용하지 마시고, 대신 **'효율향상사업'**이라고 표현하세요.
- 답변은 한국어로 작성하세요.
- 지원금, 자격요건, 필요서류 등은 **개조식 목록이나 표**를 사용하여 가독성을 높이세요.
- 답변 마지막에는 **참고한 문서 파일명이나 출처를 절대 언급하지 마세요.**
"""

    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"참고 문서 및 검색 결과:\n{context}\n\n질문: {query}"}
        ],
        temperature=0.1, # 온도를 더 낮춰서(0.3 -> 0.1) 환각 및 딴소리 방지
        max_tokens=2000
    )

    return response.choices[0].message.content.strip()



def is_query_relevant(query: str) -> bool:
    """LLM을 사용하여 쿼리가 사업과 관련있는지 판단"""
    try:
        system_prompt = (
            "You are a relevance classifier for KEPCO Energy Efficiency Chatbot.\n"
            "Determine if the user's query is related to: \n"
            "- Energy Efficiency Support Projects (EERS)\n"
            "- Electrical equipment (LED, Inverter, Pump, etc.)\n"
            "- KEPCO business procedures, documents, or contacts\n"
            "- General business/industrial inquiries relevant to facility management\n"
            "\n"
            "Examples of IRRELEVANT topics:\n"
            "- Weather, Stock Market, Politics, Entertainment, Games, Daily Chitchat (unless simple greetings), Food recipes\n"
            "\n"
            "Query: " + query + "\n"
            "Output ONLY 'true' if relevant, or 'false' if irrelevant."
        )
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0,
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip().lower()
        return "true" in result
    except Exception as e:
        print(f"Relevance Check Error: {e}")
        return True  # 에러 시 관대하게 허용


def ask(query: str, chat_history: list[dict] = None) -> str:
    """전체 RAG 파이프라인: 검색 → 유사도 필터 → 웹 검색(필요시) → 답변 생성"""
    try:
        # 1. 문서 검색 시도
        docs = search_similar(query) 
        
        # 2. 강제 답변 키워드 체크 (문서 검색 실패해도 기본 지식으로 답변해야 하는 질문들)
        force_answer_keywords = ["지원금", "서류", "담당자", "연락처", "문의", "절차", "방법", "효율", "뭐", "무엇", "대상", "기간", "신청", "효과", "절감", "산출", "계산"]
        should_force_answer = any(k in query for k in force_answer_keywords)

        relevant_docs = []
        web_context = ""

        # 3. 문서 검색 결과 필터링
        if docs:
            relevant_docs = [d for d in docs if d.get("similarity", 0) >= 0.25]
        
        # 4. 문서 결과가 부족하면 웹 검색 시도
        if not relevant_docs and not should_force_answer:
            # === 관련성 체크 (무분별한 웹 검색 방지) ===
            if not is_query_relevant(query):
                return ("죄송합니다. 저는 에너지 효율향상사업과 관련된 질문에만 답변할 수 있습니다.\n\n"
                        "날씨, 주식, 연예 등 사업과 무관한 질문에는 답변하지 않습니다.")

            print("문서 검색 결과 없음, 웹 검색 시도...")
            web_context = search_web(query)
            
            if not web_context:
                return ("죄송합니다. 해당 질문과 관련된 내용을 문서나 웹 검색에서 찾을 수 없습니다.\n\n"
                        "효율향상사업의 절차, 기기, 공고 등에 대해 질문해주세요.")
        
        # 5. LLM 호출 (문서 + 웹 검색 결과 함께 전달)
        final_docs = relevant_docs if relevant_docs else []
        
        return generate_answer(query, final_docs, web_context)

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"RAG Error: {error_msg}")
        return f"시스템 내부 오류가 발생했습니다.\n상세 에러: {str(e)}"
