"""
upload_docs.py - 로컬 PDF 일괄 업로드 스크립트
docs/ 폴더의 PDF를 읽고 → 텍스트 추출 → 청킹 → 임베딩 → Supabase 저장
httpx를 사용하지 않고 requests로 직접 호출하여 인코딩 문제 완전 회피

사용법:
  1. docs/ 폴더에 PDF 파일을 넣으세요
  2. python upload_docs.py 실행
"""
import os
import io
import json
import requests
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
DOCS_FOLDER = "docs"


def extract_text_from_pdf(filepath: str) -> str:
    """PDF 파일에서 텍스트를 추출합니다."""
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """텍스트를 청크로 나눕니다."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", "? ", "! "]:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1 and last_sep > chunk_size * 0.5:
                    end = start + last_sep + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if end < len(text) else len(text)
    return chunks


def get_embedding(text: str) -> list[float]:
    """OpenAI API를 requests로 직접 호출하여 임베딩을 얻습니다."""
    # 토큰 제한 방지를 위해 6000자로 자르기
    truncated = text[:6000] if len(text) > 6000 else text
    if not truncated.strip():
        truncated = "empty"

    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": EMBEDDING_MODEL,
            "input": truncated
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def store_chunk(content: str, source: str, chunk_index: int, embedding: list[float]):
    """Supabase REST API를 requests로 직접 호출하여 저장합니다."""
    data = {
        "content": content,
        "metadata": {"source": source, "chunk_index": chunk_index},
        "embedding": embedding
    }
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/documents",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        timeout=30
    )
    resp.raise_for_status()


def main():
    # docs 폴더 확인
    if not os.path.exists(DOCS_FOLDER):
        os.makedirs(DOCS_FOLDER)
        print(f"📁 '{DOCS_FOLDER}/' 폴더를 생성했습니다. PDF 파일을 넣고 다시 실행하세요.")
        return

    pdf_files = [f for f in os.listdir(DOCS_FOLDER) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"📁 '{DOCS_FOLDER}/' 폴더에 PDF 파일이 없습니다.")
        return

    print(f"📄 {len(pdf_files)}개 PDF 파일 발견\n")

    total_success = 0
    total_fail = 0

    for file_idx, filename in enumerate(pdf_files):
        filepath = os.path.join(DOCS_FOLDER, filename)
        print(f"[{file_idx+1}/{len(pdf_files)}] {filename}")

        try:
            # 텍스트 추출
            text = extract_text_from_pdf(filepath)
            if not text:
                print(f"  ⚠️ 텍스트 추출 실패 (건너뜀)")
                total_fail += 1
                continue

            # 청킹
            chunks = chunk_text(text)
            print(f"  📝 {len(chunks)}개 청크 생성")

            # 임베딩 + 저장
            for i, chunk in enumerate(chunks):
                embedding = get_embedding(chunk)
                store_chunk(chunk, filename, i, embedding)
                # 진행률 표시 (10개마다)
                if (i + 1) % 10 == 0 or i == len(chunks) - 1:
                    print(f"  ✅ {i+1}/{len(chunks)} 청크 완료")

            total_success += 1
            print(f"  🎉 완료!\n")

        except Exception as e:
            total_fail += 1
            print(f"  ❌ 오류: {str(e)[:150]}\n")

    print(f"\n{'='*50}")
    print(f"📊 결과: 성공 {total_success}개 / 실패 {total_fail}개")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
