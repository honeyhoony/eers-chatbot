"""
한국전력 대구본부 효율향상사업 AI 상담원
문서 기반 Q&A 챗봇
"""
import streamlit as st
from classes.rag import ask
from classes.admin import render_admin_panel

# ========== 페이지 설정 ==========
st.set_page_config(
    page_title="한국전력 효율향상사업 도우미",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ========== 미니멀 CSS (흑백 + 블루 포인트) ==========
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');

    /* 전역 폰트 - 아이콘 제외 */
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* 배경 */
    .stApp {
        background: #0a0a0a;
    }

    /* 숨김 */
    footer, #MainMenu, header { visibility: hidden; }

    /* ===== 헤더 ===== */
    .header-box {
        border: 1px solid #222;
        border-radius: 16px;
        padding: 2rem 1.5rem;
        text-align: center;
        margin-bottom: 1.2rem;
        background: #111;
    }
    .header-box h1 {
        font-size: 1.5rem;
        font-weight: 700;
        color: #fff;
        margin: 0 0 0.3rem 0;
        letter-spacing: -0.02em;
    }
    .header-box p {
        color: #666;
        font-size: 0.85rem;
        margin: 0;
    }

    /* ===== 안내 배너 ===== */
    .info-bar {
        background: #111;
        border: 1px solid #222;
        border-left: 3px solid #3b82f6;
        border-radius: 0 10px 10px 0;
        padding: 0.7rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.82rem;
        color: #888;
    }
    .info-bar strong { color: #ccc; }

    /* ===== 채팅 메시지 ===== */
    .stChatMessage {
        background: #111 !important;
        border: 1px solid #1a1a1a !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* 아바타 숨기고 심플하게 */
    [data-testid="stChatMessageAvatarCustom"],
    [data-testid="chatAvatarIcon-user"],
    [data-testid="chatAvatarIcon-assistant"] {
        display: none !important;
    }

    /* ===== 채팅 입력 ===== */
    .stChatInput > div {
        border-radius: 12px !important;
        border: 1px solid #222 !important;
        background: #111 !important;
    }
    .stChatInput > div:focus-within {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 1px #3b82f6 !important;
    }

    /* ===== 탭 ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #111;
        border: 1px solid #222;
        border-radius: 10px;
        padding: 3px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
        color: #666 !important;
    }
    .stTabs [aria-selected="true"] {
        background: #1a1a1a !important;
        color: #fff !important;
    }

    /* ===== 버튼 ===== */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        border: 1px solid #222;
        background: #111;
        color: #ccc;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: #3b82f6;
        color: #fff;
        background: #0f1a2e;
    }
    /* Primary 버튼 */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: #3b82f6 !important;
        color: #fff !important;
        border-color: #3b82f6 !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        background: #2563eb !important;
    }

    /* ===== 파일 업로더 ===== */
    .stFileUploader > div {
        border-radius: 12px !important;
        border: 1px dashed #333 !important;
        background: #111 !important;
    }

    /* ===== 프로그레스 바 ===== */
    .stProgress > div > div {
        background: #3b82f6 !important;
    }

    /* ===== 스피너 ===== */
    .stSpinner > div > div {
        border-top-color: #3b82f6 !important;
    }

    /* ===== 연락처 카드 ===== */
    .contact-card {
        background: #111;
        border: 1px solid #1a1a1a;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .contact-card:hover {
        border-color: #333;
    }
    .contact-name {
        font-weight: 600;
        color: #e5e5e5;
        font-size: 0.92rem;
    }
    .contact-area {
        color: #555;
        font-size: 0.8rem;
        margin-top: 2px;
    }
    .contact-phone {
        color: #3b82f6;
        font-weight: 600;
        font-size: 0.95rem;
        white-space: nowrap;
    }

    /* ===== 텍스트 입력 ===== */
    .stTextInput > div > div {
        border-radius: 8px !important;
        border-color: #222 !important;
        background: #111 !important;
    }
    .stTextInput > div > div:focus-within {
        border-color: #3b82f6 !important;
    }
</style>
""", unsafe_allow_html=True)

# ========== 관할지사 연락처 데이터 ==========
BRANCH_OFFICES = [
    {"사업소": "대구본부 직할 (북구)", "전화번호": "053-350-2452", "관할구역": "대구 북구"},
    {"사업소": "대구본부 직할 (중구)", "전화번호": "053-350-2183", "관할구역": "대구 중구"},
    {"사업소": "동대구지사", "전화번호": "053-757-2216", "관할구역": "동구, 수성구, 달성군(가창면)"},
    {"사업소": "경주지사", "전화번호": "054-740-2242", "관할구역": "경주시 전역"},
    {"사업소": "남대구지사", "전화번호": "053-630-2226", "관할구역": "달서구 일부, 달성군 일부(화원, 논공, 옥포, 현풍, 유가, 구지면)"},
    {"사업소": "서대구지사", "전화번호": "053-550-2221", "관할구역": "서구, 남구 전역, 달성군 일부(다사읍, 하빈면), 달서구 일부"},
    {"사업소": "포항지사", "전화번호": "054-271-7226", "관할구역": "포항시 남구 전역, 북구 일부"},
    {"사업소": "경산지사", "전화번호": "053-810-4122", "관할구역": "경산시 전역"},
    {"사업소": "김천지사", "전화번호": "054-429-5226", "관할구역": "김천시 전역"},
    {"사업소": "영천지사", "전화번호": "054-330-2222", "관할구역": "영천시 전역"},
    {"사업소": "칠곡지사", "전화번호": "054-970-3211", "관할구역": "왜관읍, 석적읍, 북삼읍, 기산면, 약목면, 지천면, 동명면 등"},
    {"사업소": "성주지사", "전화번호": "054-930-2221", "관할구역": "성주군 전역"},
    {"사업소": "청도지사", "전화번호": "054-370-4253", "관할구역": "청도군 전역"},
    {"사업소": "북포항지사", "전화번호": "054-260-4224", "관할구역": "포항시 북구 일부(흥해읍, 송라면, 청하면 등)"},
    {"사업소": "고령지사", "전화번호": "054-950-2221", "관할구역": "고령군 전역"},
    {"사업소": "영덕지사", "전화번호": "054-730-3254", "관할구역": "영덕군 전역"},
]

# ========== 예시 질문 ==========
EXAMPLE_QUESTIONS = [
    "효율향상사업 참여 절차가 어떻게 되나요?",
    "고효율 LED 지원 기준과 지원금이 궁금합니다",
    "고효율 인버터 신청 서류는 무엇이 필요한가요?",
    "소상공인 대상 특별지원 기준이 있나요?",
    "고효율 냉동기 지원 공고 내용을 알려주세요",
    "농어민 대상 효율향상사업 지원 기준은?",
]

# ========== 탭 구성 ==========
tab_chat, tab_contacts, tab_admin = st.tabs(["💬 상담", "📞 연락처", "⚙️ 관리"])

# ========== 챗봇 탭 ==========
with tab_chat:
    st.markdown("""
    <div class="header-box">
        <h1>⚡ 한국전력 대구본부<br>효율향상사업 도우미</h1>
        <p>설비효율향상사업 관련 궁금한 점을 물어보세요</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-bar">
        📌 본 챗봇은 <strong>효율향상사업 관련 문서에 기반하여</strong> 답변합니다.
        자세한 사항은 <strong>관할지사 담당자</strong>에게 문의해주세요.
    </div>
    """, unsafe_allow_html=True)

    # 세션 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_example" not in st.session_state:
        st.session_state.selected_example = None

    # 예시 질문 (대화 없을 때)
    if len(st.session_state.messages) == 0:
        st.markdown("##### 💡 자주 묻는 질문")
        cols = st.columns(2)
        for i, q in enumerate(EXAMPLE_QUESTIONS):
            with cols[i % 2]:
                if st.button(q, key=f"ex_{i}", use_container_width=True):
                    st.session_state.selected_example = q
                    st.rerun()

    # 메시지 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 예시 질문 처리
    if st.session_state.selected_example:
        prompt = st.session_state.selected_example
        st.session_state.selected_example = None
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                try:
                    response = ask(prompt)
                except Exception as e:
                    response = f"오류가 발생했습니다: {str(e)}"
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    # 직접 입력
    if prompt := st.chat_input("효율향상사업에 대해 질문해주세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                try:
                    response = ask(prompt)
                except Exception as e:
                    response = f"오류가 발생했습니다: {str(e)}"
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ========== 연락처 탭 ==========
with tab_contacts:
    st.markdown("""
    <div class="header-box" style="padding: 1.5rem;">
        <h1 style="font-size: 1.3rem;">📞 관할지사 연락처</h1>
        <p>한국전력공사 대구본부 사업소 효율향상사업 담당</p>
    </div>
    """, unsafe_allow_html=True)

    search_area = st.text_input("지역명으로 검색", placeholder="예: 경산, 포항, 서구...")

    filtered = BRANCH_OFFICES
    if search_area:
        filtered = [b for b in BRANCH_OFFICES
                    if search_area in b["사업소"] or search_area in b["관할구역"]]

    if filtered:
        for office in filtered:
            st.markdown(f"""
            <div class="contact-card">
                <div>
                    <div class="contact-name">{office['사업소']}</div>
                    <div class="contact-area">{office['관할구역']}</div>
                </div>
                <div class="contact-phone">{office['전화번호']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("해당 지역의 사업소를 찾을 수 없습니다.")

    st.markdown("""
    <div class="info-bar" style="margin-top: 1rem;">
        💡 효율향상사업 관련 자세한 상담은 <strong>관할 지사 담당자</strong>에게 전화 문의해주세요.
    </div>
    """, unsafe_allow_html=True)

# ========== 관리자 탭 ==========
with tab_admin:
    render_admin_panel()
