"""
admin.py - 관리자 문서 관리 (Supabase Storage + Vector 인덱싱)
"""
import re
import hashlib
import streamlit as st
from classes.text_utils import extract_text_from_pdf, chunk_text
from classes.rag import supabase, store_chunks


BUCKET_NAME = "kepco-docs"


def sanitize_filename(filename: str) -> str:
    """한글/특수문자가 포함된 파일명을 Supabase Storage에 안전한 형식으로 변환합니다.
    원본 파일명의 해시를 사용하여 고유성을 보장합니다."""
    name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "pdf")
    # 원본 파일명의 해시로 고유 ID 생성
    file_hash = hashlib.md5(name.encode("utf-8")).hexdigest()[:12]
    # 영문/숫자만 추출 (있으면 prefix로 사용)
    safe_part = re.sub(r"[^a-zA-Z0-9]", "", name)[:20]
    if safe_part:
        safe_name = f"{safe_part}_{file_hash}.{ext}"
    else:
        safe_name = f"doc_{file_hash}.{ext}"
    return safe_name


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
        original_name = uploaded_file.name
        safe_name = sanitize_filename(original_name)

        # 1. Supabase Storage에 업로드 (안전한 파일명 사용)
        with st.spinner(f"📤 '{original_name}' 업로드 중..."):
            supabase.storage.from_(BUCKET_NAME).upload(
                path=safe_name,
                file=file_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )

        # 2. PDF 텍스트 추출
        with st.spinner("📄 텍스트 추출 중..."):
            text = extract_text_from_pdf(file_bytes)
            if not text:
                st.error(f"PDF에서 텍스트를 추출할 수 없습니다: {original_name}")
                return False

        # 3. 청킹 & 임베딩 저장 (원본 파일명을 metadata에 보존)
        with st.spinner("🧠 AI 인덱싱 중... (시간이 걸릴 수 있습니다)"):
            chunks = chunk_text(text)
            store_chunks(chunks, original_name)

        st.success(f"✅ '{original_name}' 업로드 완료! ({len(chunks)}개 청크 인덱싱)")
        return True

    except Exception as e:
        st.error(f"❌ '{uploaded_file.name}' 업로드 실패: {str(e)}")
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

    # -- 문서 업로드 (일괄 지원) --
    st.subheader("📁 문서 업로드")
    uploaded_files = st.file_uploader(
        "KEPCO EERS 관련 PDF 파일을 업로드하세요 (여러 파일 선택 가능)",
        type=["pdf"],
        accept_multiple_files=True,
        help="절차서, 기기별 공고문, 대구본부 공고문 등 — Ctrl/Shift 클릭으로 다중 선택"
    )
    if uploaded_files:
        st.info(f"📎 {len(uploaded_files)}개 파일 선택됨")
        if st.button(f"📤 {len(uploaded_files)}개 파일 일괄 업로드 & 인덱싱 시작"):
            progress_bar = st.progress(0, text="업로드 준비 중...")
            success_count = 0
            fail_count = 0
            for i, file in enumerate(uploaded_files):
                progress_bar.progress(
                    (i) / len(uploaded_files),
                    text=f"({i+1}/{len(uploaded_files)}) {file.name} 처리 중..."
                )
                if upload_document(file):
                    success_count += 1
                else:
                    fail_count += 1
            progress_bar.progress(1.0, text="완료!")
            st.balloons()
            st.success(f"🎉 일괄 업로드 완료! 성공: {success_count}개 / 실패: {fail_count}개")

    # -- 등록된 문서 목록 --
    st.subheader("📋 등록된 문서 목록")
    docs = list_documents()
    if docs:
        st.caption(f"총 {len(docs)}개 문서 등록됨")
        for doc in docs:
            col1, col2 = st.columns([4, 1])
            col1.write(f"📄 {doc}")
            if col2.button("🗑️", key=f"del_{doc}"):
                if delete_document(doc):
                    st.success(f"'{doc}' 삭제 완료")
                    st.rerun()
    else:
        st.info("아직 등록된 문서가 없습니다.")

