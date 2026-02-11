"""
text_utils.py - PDF 파일 텍스트 추출 및 청킹 유틸리티
"""
import io
from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """PDF 바이트로부터 텍스트를 추출합니다."""
    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
    """
    텍스트를 지정된 크기의 청크로 나눕니다.
    chunk_size: 각 청크의 최대 문자 수
    chunk_overlap: 인접 청크 간 겹치는 문자 수
    """
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # 문장 끝에서 자르기 시도 (마지막 청크 제외)
        if end < len(text):
            # 마지막 마침표, 물음표, 느낌표 또는 줄바꿈 위치 찾기
            for sep in ["\n\n", "\n", ". ", "? ", "! "]:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1 and last_sep > chunk_size * 0.5:
                    end = start + last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - chunk_overlap if end < len(text) else len(text)

    return chunks
