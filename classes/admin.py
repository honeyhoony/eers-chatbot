"""
admin.py - 관리자 문서 관리 (벡터DB 조회/삭제)
PDF 업로드는 upload_docs.py 스크립트로 처리
"""
import streamlit as st
from classes.rag import supabase
import requests as http_requests
import os
from dotenv import load_dotenv

load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


def check_admin_password() -> bool:
    """관리자 비밀번호를 확인합니다."""
    admin_pw = st.secrets.get("ADMIN_PASSWORD", "changeme123")
    entered = st.text_input("관리자 비밀번호", type="password")
    if entered == admin_pw:
        return True
    elif entered:
        st.error("비밀번호가 틀렸습니다.")
    return False


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

        # 파일별 청크 수 계산
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

    # -- 인덱싱된 문서 목록 --
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
        st.info("인덱싱된 문서가 없습니다. upload_docs.py 스크립트로 PDF를 업로드하세요.")

    # -- 업로드 안내 --
    st.markdown("---")
    st.subheader("문서 업로드 방법")
    st.code("""# 1. docs/ 폴더에 PDF 파일을 넣고
# 2. 터미널에서 실행:
python upload_docs.py""", language="bash")
