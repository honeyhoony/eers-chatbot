"""
KEPCO EERS 챗봇 - 메인 애플리케이션
에너지효율향상의무화제도 관련 문서 기반 Q&A 챗봇
"""
import streamlit as st
from classes.rag import ask
from classes.admin import render_admin_panel

# ========== 페이지 설정 ==========
st.set_page_config(
    page_title="대구본부 효율향상사업 챗봇",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ========== 프리미엄 CSS ==========
st.markdown("""
<style>
    /* ===== 전체 배경 & 폰트 ===== */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

    * { font-family: 'Noto Sans KR', sans-serif !important; }

    .stApp {
        background: linear-gradient(180deg, #0E1117 0%, #151B28 100%);
    }

    /* ===== 헤더 영역 ===== */
    .hero-container {
        background: linear-gradient(135deg, #1a1f2e 0%, #2d1f3d 50%, #1a2f3e 100%);
        border: 1px solid rgba(255, 107, 53, 0.2);
        border-radius: 20px;
        padding: 2rem 1.5rem;
        text-align: center;
        margin-bottom: 1rem;
        position: relative;
        overflow: hidden;
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,107,53,0.05) 0%, transparent 70%);
        animation: pulse 4s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 0.5; }
        50% { transform: scale(1.1); opacity: 1; }
    }
    .hero-icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    .hero-title {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FF6B35, #FFB347);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .hero-subtitle {
        color: #8B95A5;
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }

    /* ===== 안내 배너 ===== */
    .notice-banner {
        background: rgba(255, 107, 53, 0.08);
        border-left: 3px solid #FF6B35;
        border-radius: 0 10px 10px 0;
        padding: 0.7rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.82rem;
        color: #B0B8C8;
    }
    .notice-banner strong { color: #FF6B35; }

    /* ===== 채팅 메시지 ===== */
    .stChatMessage {
        border-radius: 16px !important;
        padding: 1rem !important;
        margin-bottom: 0.8rem !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        backdrop-filter: blur(10px) !important;
    }

    /* ===== 채팅 입력 ===== */
    .stChatInput > div {
        border-radius: 25px !important;
        border: 1px solid rgba(255, 107, 53, 0.3) !important;
        background: rgba(26, 31, 46, 0.8) !important;
    }
    .stChatInput > div:focus-within {
        border-color: #FF6B35 !important;
        box-shadow: 0 0 15px rgba(255, 107, 53, 0.15) !important;
    }

    /* ===== 탭 스타일 ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(26, 31, 46, 0.5);
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #FF6B35, #FF8B55) !important;
        color: white !important;
    }

    /* ===== 버튼 ===== */
    .stButton > button {
        border-radius: 12px;
        font-weight: 500;
        border: 1px solid rgba(255, 107, 53, 0.3);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        border-color: #FF6B35;
        box-shadow: 0 0 20px rgba(255, 107, 53, 0.2);
        transform: translateY(-1px);
    }

    /* ===== 파일 업로더 ===== */
    .stFileUploader > div {
        border-radius: 16px !important;
        border: 2px dashed rgba(255, 107, 53, 0.3) !important;
    }

    /* ===== 프로그레스 바 ===== */
    .stProgress > div > div {
        background: linear-gradient(90deg, #FF6B35, #FFB347) !important;
    }

    /* ===== 숨김 요소 ===== */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    header { visibility: hidden; }

    /* ===== 스피너 ===== */
    .stSpinner > div > div {
        border-top-color: #FF6B35 !important;
    }

    /* ===== 예시 질문 카드 ===== */
    .example-card {
        background: rgba(26, 31, 46, 0.6);
        border: 1px solid rgba(255, 107, 53, 0.15);
        border-radius: 12px;
        padding: 0.6rem 1rem;
        margin: 0.3rem 0;
        font-size: 0.85rem;
        color: #B0B8C8;
        transition: all 0.2s ease;
    }
    .example-card:hover {
        border-color: rgba(255, 107, 53, 0.4);
        background: rgba(255, 107, 53, 0.05);
    }
    .example-card .emoji { margin-right: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ========== 탭 구성 ==========
tab_chat, tab_admin = st.tabs(["💬 챗봇", "⚙️ 관리자"])

# ========== 챗봇 탭 ==========
with tab_chat:
    # 히어로 헤더
    st.markdown("""
    <div class="hero-container">
        <div class="hero-icon">⚡</div>
        <h1 class="hero-title">KEPCO EERS 챗봇</h1>
        <p class="hero-subtitle">에너지효율향상의무화제도 · 문서 기반 AI 상담</p>
    </div>
    """, unsafe_allow_html=True)

    # 안내 배너
    st.markdown("""
    <div class="notice-banner">
        📌 본 챗봇은 관리자가 등록한 <strong>KEPCO EERS 관련 문서에 기반하여</strong> 답변합니다.
        등록된 문서에 없는 내용이나 EERS와 무관한 질문에는 답변이 제한됩니다.
    </div>
    """, unsafe_allow_html=True)

    # 채팅 히스토리 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! ⚡ **KEPCO EERS 챗봇**입니다.\n\n"
             "📌 **등록된 EERS 문서를 기반으로만 답변합니다.**\n\n"
             "아래와 같은 질문을 해보세요:\n"
             "- 🔌 EERS 사업 참여 절차가 어떻게 되나요?\n"
             "- 💰 고효율 기기 설치 시 지원금은 얼마인가요?\n"
             "- 📋 대구본부 공고 내용이 궁금합니다."}
        ]

    # 이전 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력
    if prompt := st.chat_input("💬 EERS에 대해 질문해주세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🔍 문서 검색 및 답변 생성 중..."):
                try:
                    response = ask(prompt)
                except Exception as e:
                    response = f"⚠️ 오류가 발생했습니다: {str(e)}\n\n관리자에게 문의하거나 문서가 업로드되어 있는지 확인해주세요."
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

# ========== 관리자 탭 ==========
with tab_admin:
    render_admin_panel()
