"""
admin.py - 관리자 문서 관리 (웹 업로드 + 벡터DB 조회/삭제)
"""
import json
import streamlit as st
from classes.rag import supabase, get_secret
from classes.text_utils import extract_text_from_pdf, chunk_text
import requests as http_requests

OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_SERVICE_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"


def check_admin_password() -> bool:
    """관리자 비밀번호를 확인합니다."""
    admin_pw = st.secrets.get("ADMIN_PASSWORD", "changeme123")
    entered = st.text_input("관리자 비밀번호", type="password")
    if entered == admin_pw:
        return True
    elif entered:
        st.error("비밀번호가 틀렸습니다.")
    return False


def web_get_embedding(text: str) -> list[float]:
    """requests로 직접 OpenAI 임베딩 호출 (httpx 우회)"""
    truncated = text[:6000] if len(text) > 6000 else text
    if not truncated.strip():
        truncated = "empty"
    body = json.dumps({"model": EMBEDDING_MODEL, "input": truncated})
    resp = http_requests.post(
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


def web_store_chunk(content: str, source: str, chunk_index: int, embedding: list[float]):
    """requests로 직접 Supabase 저장 (httpx 우회)"""
    data = {
        "content": content,
        "metadata": {"source": source, "chunk_index": chunk_index},
        "embedding": embedding
    }
    body = json.dumps(data)
    resp = http_requests.post(
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


def upload_document(uploaded_file) -> bool:
    """PDF 파일을 웹에서 업로드하고 인덱싱합니다."""
    original_name = uploaded_file.name
    try:
        file_bytes = uploaded_file.read()
    except Exception:
        st.error(f"파일 읽기 실패: {original_name}")
        return False

    # 0. 중복 체크
    existing_docs = get_indexed_documents()
    existing_names = {d["name"] for d in existing_docs}
    if original_name in existing_names:
        st.warning(f"'{original_name}' — 이미 등록된 문서입니다 (건너뜀)")
        return True  # 성공으로 처리

    # 1. 텍스트 추출
    try:
        text = extract_text_from_pdf(file_bytes)
        if not text:
            st.error(f"텍스트 추출 실패: {original_name}")
            return False
    except Exception as e:
        st.error(f"텍스트 추출 오류: {str(e)[:100]}")
        return False

    # 2. 청킹
    chunks = chunk_text(text)

    # 3. 임베딩 + 저장 (requests로 직접 호출)
    try:
        for i, chunk in enumerate(chunks):
            embedding = web_get_embedding(chunk)
            web_store_chunk(chunk, original_name, i, embedding)
    except Exception as e:
        st.error(f"인덱싱 오류: {str(e)[:150]}")
        return False

    st.success(f"'{original_name}' — {len(chunks)}개 청크 인덱싱 완료")
    return True


def get_indexed_documents() -> list[dict]:
    """벡터DB에 인덱싱된 문서 목록과 청크 수를 조회합니다."""
    try:
        resp = http_requests.get(
            f"{SUPABASE_URL}/rest/v1/documents?select=metadata",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()

        doc_counts = {}
        for row in data:
            meta = row.get("metadata", {})
            if isinstance(meta, dict):
                source = meta.get("source", "알 수 없음")
                doc_counts[source] = doc_counts.get(source, 0) + 1

        return [{"name": name, "chunks": count} for name, count in sorted(doc_counts.items())]
    except Exception:
        return []


def delete_document_by_source(source_name: str) -> bool:
    """특정 문서를 벡터DB에서 삭제합니다."""
    try:
        supabase.table("documents").delete().filter(
            "metadata->>source", "eq", source_name
        ).execute()
        return True
    except Exception as e:
        st.error(f"삭제 실패: {str(e)}")
        return False


def delete_all_documents() -> bool:
    """모든 문서를 벡터DB에서 삭제합니다."""
    try:
        supabase.table("documents").delete().neq("id", 0).execute()
        return True
    except Exception as e:
        st.error(f"전체 삭제 실패: {str(e)}")
        return False


def render_admin_panel():
    """관리자 패널 UI를 렌더링합니다."""
    st.header("관리자 설정")

    if not check_admin_password():
        st.info("관리자 비밀번호를 입력해주세요.")
        return

    st.success("관리자 인증 완료")

    # -- 문서 업로드 --
    st.subheader("문서 업로드")
    uploaded_files = st.file_uploader(
        "PDF 파일을 업로드하세요 (여러 파일 선택 가능)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Ctrl/Shift 클릭으로 다중 선택"
    )
    if uploaded_files:
        st.info(f"{len(uploaded_files)}개 파일 선택됨")
        if st.button(f"{len(uploaded_files)}개 파일 업로드 시작"):
            progress_bar = st.progress(0, text="준비 중...")
            success_count = 0
            fail_count = 0
            for i, file in enumerate(uploaded_files):
                progress_bar.progress(
                    i / len(uploaded_files),
                    text=f"({i+1}/{len(uploaded_files)}) 처리 중..."
                )
                if upload_document(file):
                    success_count += 1
                else:
                    fail_count += 1
            progress_bar.progress(1.0, text="완료")
            if fail_count == 0:
                st.balloons()
                st.success(f"전체 {success_count}개 파일 인덱싱 완료!")
            else:
                st.warning(f"완료 — 성공: {success_count}개 / 실패: {fail_count}개")

    # -- 인덱싱된 문서 목록 --
    st.markdown("---")
    st.subheader("인덱싱된 문서 목록")

    docs = get_indexed_documents()
    if docs:
        total_chunks = sum(d["chunks"] for d in docs)
        st.caption(f"총 {len(docs)}개 문서 / {total_chunks}개 청크")

        for doc in docs:
            col1, col2, col3 = st.columns([5, 1, 1])
            col1.write(f"{doc['name']}")
            col2.caption(f"{doc['chunks']}청크")
            if col3.button("삭제", key=f"del_{doc['name']}"):
                if delete_document_by_source(doc['name']):
                    st.success(f"'{doc['name']}' 삭제 완료")
                    st.rerun()

        # -- 전체 삭제 --
        st.markdown("---")
        st.subheader("전체 삭제")
        st.warning("등록된 모든 문서와 인덱싱 데이터가 삭제됩니다. 되돌릴 수 없습니다.")
        if "confirm_delete_all" not in st.session_state:
            st.session_state.confirm_delete_all = False

        if not st.session_state.confirm_delete_all:
            if st.button("전체 삭제 요청", type="primary"):
                st.session_state.confirm_delete_all = True
                st.rerun()
        else:
            st.error("정말로 모든 문서를 삭제하시겠습니까?")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("네, 전체 삭제합니다", type="primary"):
                    if delete_all_documents():
                        st.success("모든 문서가 삭제되었습니다.")
                        st.session_state.confirm_delete_all = False
                        st.rerun()
            with col_no:
                if st.button("취소"):
                    st.session_state.confirm_delete_all = False
                    st.rerun()
    else:
        st.info("인덱싱된 문서가 없습니다.")
