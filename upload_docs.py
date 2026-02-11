"""
upload_docs.py - PDF 일괄 업로드 스크립트
docs/ 폴더의 PDF -> 텍스트 추출 -> 청킹 -> 임베딩 -> Supabase 저장
이미 업로드된 파일은 자동 건너뜀 (중복 방지)
"""
import os
import sys
import json
import time
import traceback
import requests
import pdfplumber
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
DOCS_FOLDER = "docs"


def extract_text_from_pdf(filepath: str) -> str:
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        cells = [str(cell).strip() if cell else "" for cell in row]
                        text += " | ".join(cells) + "\n"
                    text += "\n"
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
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
    truncated = text[:6000] if len(text) > 6000 else text
    if not truncated.strip():
        truncated = "empty"
    body = json.dumps({"model": EMBEDDING_MODEL, "input": truncated})
    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        data=body.encode("ascii"),
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def store_chunk(content: str, source: str, chunk_index: int, embedding: list[float]):
    data = {
        "content": content,
        "metadata": {"source": source, "chunk_index": chunk_index},
        "embedding": embedding
    }
    body = json.dumps(data)
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/documents",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        data=body.encode("ascii"),
        timeout=30
    )
    resp.raise_for_status()


def get_uploaded_files() -> set:
    """이미 Supabase에 업로드된 파일명 목록을 조회합니다."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/documents?select=metadata",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        sources = set()
        for row in data:
            meta = row.get("metadata", {})
            if isinstance(meta, dict):
                src = meta.get("source")
                if src:
                    sources.add(src)
        return sources
    except Exception:
        return set()


def main():
    if not os.path.exists(DOCS_FOLDER):
        os.makedirs(DOCS_FOLDER)
        print("[INFO] docs/ folder created. Put PDF files inside and run again.")
        return

    pdf_files = sorted([f for f in os.listdir(DOCS_FOLDER) if f.lower().endswith(".pdf")])
    if not pdf_files:
        print("[INFO] No PDF files found in docs/")
        return

    # 이미 업로드된 파일 확인
    uploaded = get_uploaded_files()
    if uploaded:
        print(f"[INFO] {len(uploaded)} files already uploaded, will skip them")

    to_upload = [f for f in pdf_files if f not in uploaded]
    print(f"[START] {len(to_upload)} / {len(pdf_files)} files to upload\n")

    if not to_upload:
        print("[DONE] All files already uploaded!")
        return

    total_success = 0
    total_fail = 0

    for file_idx, filename in enumerate(to_upload):
        filepath = os.path.join(DOCS_FOLDER, filename)
        print(f"[{file_idx+1}/{len(to_upload)}] {filename}")

        try:
            text = extract_text_from_pdf(filepath)
            if not text:
                print("  [SKIP] No text extracted")
                total_fail += 1
                continue

            chunks = chunk_text(text)
            print(f"  -> {len(chunks)} chunks")

            for i, chunk in enumerate(chunks):
                # 네트워크 에러 시 재시도 (최대 3회)
                for attempt in range(3):
                    try:
                        embedding = get_embedding(chunk)
                        store_chunk(chunk, filename, i, embedding)
                        break
                    except requests.exceptions.ConnectionError:
                        if attempt < 2:
                            print(f"  [RETRY] chunk {i+1}, attempt {attempt+2}/3")
                            time.sleep(3)
                        else:
                            raise

                if (i + 1) % 10 == 0 or i == len(chunks) - 1:
                    print(f"  -> {i+1}/{len(chunks)} done")

            total_success += 1
            print("  [OK]\n")

        except Exception as e:
            total_fail += 1
            print(f"  [ERROR] {str(e)[:200]}\n")

    print(f"\n{'='*50}")
    print(f"Result: {total_success} success / {total_fail} fail")
    print(f"Total indexed: {len(uploaded) + total_success} files")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
