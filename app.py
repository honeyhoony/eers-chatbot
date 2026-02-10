"""
KEPCO EERS 챗봇 - 메인 애플리케이션
에너지효율향상의무화제도 관련 문서 기반 Q&A 챗봇
"""
import streamlit as st
from classes.rag import ask
from classes.admin import render_admin_panel

# ========== 페이지 설정 ==========
st.set_page_config(
    page_title="KEPCO EERS 챗봇",
    page_icon="⚡",
    layout="centered"
)

# ========== 스타일 ==========
st.markdown("""
<style>
    .main-title {
        text-align: center;
        padding: 1rem 0;
    }
    .stChatMessage {
        border-radius: 12px;
    }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ========== 탭 구성 ==========
tab_chat, tab_admin = st.tabs(["💬 챗봇", "⚙️ 관리자"])

# ========== 챗봇 탭 ==========
with tab_chat:
    st.markdown("""
    <div class="main-title">
        <h1>⚡ KEPCO EERS 챗봇</h1>
        <p>에너지효율향상의무화제도(EERS) 관련 질문에 답변합니다</p>
    </div>
    """, unsafe_allow_html=True)

    st.info("ℹ️ **안내**: 본 챗봇은 관리자가 등록한 **KEPCO EERS 관련 문서에 기반하여** 답변합니다. "
            "등록된 문서에 없는 내용이나 EERS와 무관한 질문에는 답변이 제한됩니다.")

    # 채팅 히스토리 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! ⚡ KEPCO EERS 챗봇입니다.\n\n"
             "📌 **본 챗봇은 등록된 EERS 문서를 기반으로만 답변합니다.**\n"
             "문서에 없는 내용이나 EERS와 무관한 질문에는 답변이 제한됩니다.\n\n"
             "예시 질문:\n"
             "- EERS 사업 참여 절차가 어떻게 되나요?\n"
             "- 고효율 기기 설치 시 지원금은 얼마인가요?\n"
             "- 대구본부 공고 내용이 궁금합니다."}
        ]

    # 이전 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력
    if prompt := st.chat_input("EERS에 대해 질문해주세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 답변 생성
        with st.chat_message("assistant"):
            with st.spinner("📚 문서를 검색하고 답변을 생성하고 있습니다..."):
                try:
                    response = ask(prompt)
                except Exception as e:
                    response = f"⚠️ 오류가 발생했습니다: {str(e)}\n\n관리자에게 문의하거나 문서가 업로드되어 있는지 확인해주세요."
            st.markdown(response)

        # 어시스턴트 메시지 추가
        st.session_state.messages.append({"role": "assistant", "content": response})

# ========== 관리자 탭 ==========
with tab_admin:
    render_admin_panel()
