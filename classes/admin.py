"""
admin.py - 관리자 문서 관리 (Supabase Storage + Vector 인덱싱)
"""
import streamlit as st
from classes.text_utils import extract_text_from_pdf, chunk_text
from classes.rag import supabase, store_chunks


BUCKET_NAME = "kepco-docs"


def check_admin_password() -> bool:
    """관리자 비밀번호를 확인합니다."""
    admin_pw = st.secrets.get("ADMIN_PASSWORD", "changeme123")
    entered = st.text_input("🔑 관리자 비밀번호", type="password")
    if entered == admin_pw:
        return True
    elif entered:
        st.error("비밀번호가 틀렸습니다.")
    return False


def upload_document(uploaded_file) -> bool:
    """PDF 파일을 Supabase Storage에 업로드하고 벡터 인덱싱합니다."""
    try:
        file_bytes = uploaded_file.read()
        filename = uploaded_file.name

        # 1. Supabase Storage에 업로드
        with st.spinner("📤 파일 업로드 중..."):
            supabase.storage.from_(BUCKET_NAME).upload(
                path=filename,
                file=file_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )

        # 2. PDF 텍스트 추출
        with st.spinner("📄 텍스트 추출 중..."):
            text = extract_text_from_pdf(file_bytes)
            if not text:
                st.error("PDF에서 텍스트를 추출할 수 없습니다.")
                return False

        # 3. 청킹 & 임베딩 저장
        with st.spinner("🧠 AI 인덱싱 중... (시간이 걸릴 수 있습니다)"):
            chunks = chunk_text(text)
            store_chunks(chunks, filename)

        st.success(f"✅ '{filename}' 업로드 완료! ({len(chunks)}개 청크 인덱싱)")
        return True

    except Exception as e:
        st.error(f"❌ 업로드 실패: {str(e)}")
        return False


def list_documents() -> list[str]:
    """Storage에 업로드된 문서 목록을 가져옵니다."""
    try:
        files = supabase.storage.from_(BUCKET_NAME).list()
        return [f["name"] for f in files if f["name"].endswith(".pdf")]
    except Exception:
        return []


def delete_document(filename: str) -> bool:
    """문서를 Storage와 벡터DB에서 삭제합니다."""
    try:
        # Storage에서 삭제
        supabase.storage.from_(BUCKET_NAME).remove([filename])

        # 벡터DB에서 해당 문서의 청크 삭제
        supabase.table("documents").delete().filter(
            "metadata->>source", "eq", filename
        ).execute()

        return True
    except Exception as e:
        st.error(f"삭제 실패: {str(e)}")
        return False


def render_admin_panel():
    """관리자 패널 UI를 렌더링합니다."""
    st.header("⚙️ 관리자 설정")

    if not check_admin_password():
        st.info("관리자 비밀번호를 입력해주세요.")
        return

    st.success("✅ 관리자 인증 완료")

    # -- 문서 업로드 --
    st.subheader("📁 문서 업로드")
    uploaded_file = st.file_uploader(
        "KEPCO EERS 관련 PDF 파일을 업로드하세요",
        type=["pdf"],
        help="절차서, 기기별 공고문, 대구본부 공고문 등"
    )
    if uploaded_file:
        if st.button("📤 업로드 & 인덱싱 시작"):
            upload_document(uploaded_file)

    # -- 등록된 문서 목록 --
    st.subheader("📋 등록된 문서 목록")
    docs = list_documents()
    if docs:
        for doc in docs:
            col1, col2 = st.columns([4, 1])
            col1.write(f"📄 {doc}")
            if col2.button("🗑️", key=f"del_{doc}"):
                if delete_document(doc):
                    st.success(f"'{doc}' 삭제 완료")
                    st.rerun()
    else:
        st.info("아직 등록된 문서가 없습니다.")
