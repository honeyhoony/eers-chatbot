"""
upload_docs.py - PDF 문서 LlamaIndex 스타일 Markdown 변환 및 Supabase 업로드 스크립트
주의: 실행 시 기존 문서를 모두 삭제하고 새로 업로드합니다.
"""

import os
import json
import time
import requests
import pymupdf4llm  # 마크다운 변환 라이브러리
from dotenv import load_dotenv

# Windows 콘솔 인코딩 설정
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"

# PDF 폴더 경로
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")


def chunk_markdown(text: str, chunk_size: int = 1500, chunk_overlap: int = 300) -> list[str]:
    """
    마크다운 텍스트를 의미 단위(헤더 기준)로 유지하며 청킹합니다.
    """
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        
        # 마지막 청크 처리
        if end >= text_len:
            end = text_len
            chunks.append(text[start:end].strip())
            break
            
        # 1. 헤더(###)나 줄바꿈(\n\n) 기준으로 자르기 시도
        # (너무 짧게 잘리면 안 되므로 chunk_size의 50% 지점 이후부터 탐색)
        cut_candidates = ["\n## ", "\n### ", "\n#### ", "\n\n", ". "]
        best_cut = -1
        
        search_start = start + int(chunk_size * 0.7)
        search_end = min(start + chunk_size + 100, text_len) # 조금 더 뒤까지 봐도 됨
        
        current_chunk_text = text[start:search_end]
        
        # 뒤에서부터 찾아서 가장 적절한 분기점 찾기
        for candidate in cut_candidates:
            last_pos = text.rfind(candidate, search_start, search_end)
            if last_pos != -1:
                best_cut = last_pos
                break
        
        if best_cut != -1:
            end = best_cut
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        # 겹치게 이동
        start = max(start + 1, end - chunk_overlap)
        
    return chunks


def get_embedding(text: str) -> list[float]:
    """OpenAI 임베딩 생성"""
    truncated = text[:6000] if len(text) > 6000 else text
    if not truncated.strip():
        truncated = "empty"
        
    body = json.dumps({"model": EMBEDDING_MODEL, "input": truncated})
    
    for i in range(3):
        try:
            resp = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                data=body.encode("utf-8"), 
                timeout=60
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
        except Exception as e:
            if i == 2: raise e
            time.sleep(1)


def store_chunk(content: str, source: str, chunk_index: int, embedding: list[float]):
    """Supabase에 청크 저장"""
    data = {
        "content": content,
        "metadata": {"source": source, "chunk_index": chunk_index},
        "embedding": embedding
    }
    
    body = json.dumps(data)
    
    for i in range(3):
        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                data=body.encode("utf-8"),
                timeout=30
            )
            if resp.status_code in (200, 201, 204):
                return
            else:
                resp.raise_for_status()
        except Exception as e:
            if i == 2: 
                print(f"Failed to store chunk {chunk_index}: {e}")
            time.sleep(1)


def reset_database():
    """기존 문서 데이터를 모두 삭제합니다."""
    print("🗑️  기존 데이터를 모두 삭제합니다...")
    try:
        url = f"{SUPABASE_URL}/rest/v1/documents?id=neq.0"
        requests.delete(
            url,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        print("✅ 데이터베이스 초기화 완료.")
    except Exception as e:
        print(f"❌ 초기화 실패 (테이블이 비어있을 수 있음): {e}")


def main():
    if not os.path.exists(DOCS_DIR):
        print(f"Directory not found: {DOCS_DIR}")
        return

    # 1. DB 초기화
    reset_database()

    files = [f for f in os.listdir(DOCS_DIR) if f.lower().endswith(".pdf")]
    print(f"📂 Found {len(files)} PDF files.")

    for i, filename in enumerate(files):
        filepath = os.path.join(DOCS_DIR, filename)
        print(f"\n[{i+1}/{len(files)}] Processing {filename}...")

        try:
            # 2. Markdown으로 변환 (PyMuPDF4LLM)
            # tables=True 옵션이 기본값으로 포함되어 있음
            markdown_text = pymupdf4llm.to_markdown(filepath)
            
            if not markdown_text:
                print(f"⚠️  No text extracted from {filename}")
                continue

            # 3. 청킹 (1500자, 오버랩 300)
            chunks = chunk_markdown(markdown_text, chunk_size=1500, chunk_overlap=300)
            print(f"   -> {len(chunks)} chunks generated.")

            # 4. 임베딩 및 저장
            for idx, chunk_content in enumerate(chunks):
                if not chunk_content.strip(): continue
                
                embedding = get_embedding(chunk_content)
                store_chunk(chunk_content, filename, idx, embedding)
                print(f"   Saved chunk {idx+1}/{len(chunks)}", end="\r")
                
        except Exception as e:
            print(f"   ❌ Error processing file: {e}")

    print("\n\n🎉 All documents uploaded successfully!")


if __name__ == "__main__":
    main()
