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

# ========== 관할지사 연락처 데이터 ==========
BRANCH_OFFICES = [
    {"사업소": "대구본부 직할 (북구)", "전화번호": "053-350-2452", "관할구역": "대구 북구"},
    {"사업소": "대구본부 직할 (중구)", "전화번호": "053-350-2183", "관할구역": "대구 중구"},
    {"사업소": "동대구지사", "전화번호": "053-757-2216", "관할구역": "동구, 수성구, 달성군(가창면)"},
    {"사업소": "경주지사", "전화번호": "054-740-2242", "관할구역": "경주시 전역"},
    {"사업소": "남대구지사", "전화번호": "053-630-2226", "관할구역": "달서구 일부, 달성군 일부(화원, 논공, 옥포, 현풍, 유가, 구지면), 용산동 일부"},
    {"사업소": "서대구지사", "전화번호": "053-550-2221", "관할구역": "서구, 남구 전역, 달성군 일부(다사읍, 하빈면), 달서구 일부, 용산동 일부"},
    {"사업소": "포항지사", "전화번호": "054-271-7226", "관할구역": "포항시 남구 전역, 북구 일부(연일, 오천, 구룡포읍 등)"},
    {"사업소": "경산지사", "전화번호": "053-810-4122", "관할구역": "경산시 전역"},
    {"사업소": "김천지사", "전화번호": "054-429-5226", "관할구역": "김천시 전역"},
    {"사업소": "영천지사", "전화번호": "054-330-2222", "관할구역": "영천시 전역"},
    {"사업소": "칠곡지사", "전화번호": "054-970-3211", "관할구역": "왜관읍, 석적읍, 북삼읍, 기산면, 약목면, 지천면, 동명면 등"},
    {"사업소": "성주지사", "전화번호": "054-930-2221", "관할구역": "성주군 전역"},
    {"사업소": "청도지사", "전화번호": "054-370-4253", "관할구역": "청도군 전역"},
    {"사업소": "북포항지사", "전화번호": "054-260-4224", "관할구역": "포항시 북구 일부(흥해읍, 송라면, 청하면, 신광면, 죽장면, 기계면, 기북면)"},
    {"사업소": "고령지사", "전화번호": "054-950-2221", "관할구역": "고령군 전역"},
    {"사업소": "영덕지사", "전화번호": "054-730-3254", "관할구역": "영덕군 전역"},
]

# ========== 탭 구성 ==========
tab_chat, tab_contacts, tab_admin = st.tabs(["💬 챗봇", "📞 관할지사 연락처", "⚙️ 관리자"])

# ========== 예시 질문 목록 ==========
EXAMPLE_QUESTIONS = [
    "효율향상사업 참여 절차가 어떻게 되나요?",
    "고효율 LED 지원 기준과 지원금이 궁금합니다",
    "고효율 인버터 신청 서류는 무엇이 필요한가요?",
    "소상공인 대상 특별지원 기준이 있나요?",
    "고효율 냉동기 지원 공고 내용을 알려주세요",
    "농어민 대상 효율향상사업 지원 기준은?",
]

# ========== 챗봇 탭 ==========
with tab_chat:
    # 히어로 헤더
    st.markdown("""
    <div class="hero-container">
        <div class="hero-icon">⚡</div>
        <h1 class="hero-title">한국전력 대구본부<br>효율향상사업 도우미</h1>
        <p class="hero-subtitle">설비효율향상사업 관련 궁금한 점을 물어보세요</p>
    </div>
    """, unsafe_allow_html=True)

    # 안내 배너
    st.markdown("""
    <div class="notice-banner">
        📌 본 챗봇은 <strong>한국전력 효율향상사업 관련 문서에 기반하여</strong> 답변합니다.<br>
        자세한 사항은 <strong>한전 관할지사 효율향상사업 담당자</strong>에게 문의해주세요.
    </div>
    """, unsafe_allow_html=True)

    # 채팅 히스토리 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 예시 질문 선택 상태
    if "selected_example" not in st.session_state:
        st.session_state.selected_example = None

    # 예시 질문 버튼 (대화가 없을 때만 표시)
    if len(st.session_state.messages) == 0:
        st.markdown("#### 💡 이런 것들을 물어보세요")
        cols = st.columns(2)
        for i, question in enumerate(EXAMPLE_QUESTIONS):
            with cols[i % 2]:
                if st.button(f"💬 {question}", key=f"example_{i}", use_container_width=True):
                    st.session_state.selected_example = question
                    st.rerun()

    # 이전 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 예시 질문 클릭 처리
    if st.session_state.selected_example:
        prompt = st.session_state.selected_example
        st.session_state.selected_example = None

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

    # 직접 입력
    if prompt := st.chat_input("💬 효율향상사업에 대해 질문해주세요..."):
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

# ========== 관할지사 연락처 탭 ==========
with tab_contacts:
    st.markdown("""
    <div class="hero-container" style="padding: 1.5rem;">
        <div class="hero-icon">📞</div>
        <h1 class="hero-title" style="font-size: 1.4rem;">관할지사 연락처</h1>
        <p class="hero-subtitle">한국전력공사 대구본부 사업소 효율향상사업 담당</p>
    </div>
    """, unsafe_allow_html=True)

    # 검색 필터
    search_area = st.text_input("🔍 지역명으로 검색 (예: 경산, 포항, 서구)", placeholder="지역명 입력...")

    st.markdown("---")

    filtered = BRANCH_OFFICES
    if search_area:
        filtered = [b for b in BRANCH_OFFICES
                    if search_area in b["사업소"] or search_area in b["관할구역"]]

    if filtered:
        for office in filtered:
            st.markdown(f"""
            <div style="background: rgba(26,31,46,0.6); border: 1px solid rgba(255,107,53,0.15);
                        border-radius: 12px; padding: 1rem; margin-bottom: 0.7rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #FF6B35; font-size: 1rem;">🏢 {office['사업소']}</strong><br>
                        <span style="color: #8B95A5; font-size: 0.85rem;">📍 {office['관할구역']}</span>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: #FFB347; font-size: 1.1rem; font-weight: 600;">📞 {office['전화번호']}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("해당 지역의 사업소를 찾을 수 없습니다.")

    st.markdown("""
    <div class="notice-banner" style="margin-top: 1rem;">
        💡 효율향상사업 관련 자세한 상담은 <strong>관할 지사 담당자</strong>에게 전화 문의해주세요.
    </div>
    """, unsafe_allow_html=True)

# ========== 관리자 탭 ==========
with tab_admin:
    render_admin_panel()
