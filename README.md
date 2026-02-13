# KEPCO 효율향상사업 AI 챗봇 (Streamlit + Supabase RAG)

한국전력 대구본부 효율향상사업 안내를 위한 AI 챗봇입니다.
Streamlit 프레임워크를 기반으로 하며, Supabase pgvector를 활용한 RAG(Retrieval Augmented Generation) 기술이 적용되어 있습니다.

## 🚀 배포 방법 (Deployment)

이 프로젝트는 **Streamlit Community Cloud**를 통해 무료로 쉽게 배포할 수 있습니다.

### 1. GitHub 저장소 준비
1. GitHub에 새 저장소(Repository)를 생성합니다.
2. 이 프로젝트 코드를 해당 저장소에 업로드(Push)합니다.
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <당신의_GITHUB_REPO_URL>
   git push -u origin main
   ```

### 2. Streamlit Cloud 배포
1. [Streamlit Community Cloud](https://share.streamlit.io/)에 접속하여 로그인합니다.
2. **"New app"** 버튼을 클릭합니다.
3. 방금 생성한 GitHub 저장소, 브랜치(`main`), 메인 파일 경로(`app.py`)를 선택합니다.
4. **"Advanced settings"**를 클릭하여 환경 변수(Secrets)를 설정해야 합니다.

### 3. Secrets 설정 (필수!)
Streamlit Cloud의 배포 설정 화면에서 **Advanced settings > Secrets** 영역에 아래 내용을 복사하여 붙여넣으세요.
(`.env` 파일의 내용과 동일합니다)

```toml
# .streamlit/secrets.toml 형식
OPENAI_API_KEY = "sk-..."
SUPABASE_URL = "https://..."
SUPABASE_SERVICE_KEY = "ey..."
```

5. **"Deploy!"** 버튼을 클릭하면 배포가 완료됩니다.

---

## ⚡ 임시 배포 (Cloudflare Tunnel)
로컬에서 개발 중인 화면을 외부에 잠깐 공유하려면 프로젝트 폴더에 포함된 `cloudflared`를 사용할 수 있습니다.

1. 터미널에서 아래 명령어를 실행하세요.
   ```powershell
   .\cloudflared.exe tunnel --url http://localhost:8501
   ```
2. 실행 결과에 나오는 `https://....trycloudflare.com` 주소를 복사하여 공유하면 외부에서도 접속 가능합니다.

## 🛠️ 로컬 실행 방법
1. Python 3.9 이상 설치
2. 라이브러리 설치
   ```bash
   pip install -r requirements.txt
   ```
3. 실행
   ```bash
   streamlit run app.py
   ```
