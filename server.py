from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from dotenv import load_dotenv

# RAG 관련 함수
from classes.rag import ask, get_secret, supabase

load_dotenv(override=True)

app = FastAPI()

# 정적 파일 서빙 (나중에 index.html이 위치할 곳)
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """사용자의 질문에 답변합니다."""
    try:
        response = ask(request.message, request.history)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def get_documents():
    """등록된 문서 목록을 가져옵니다."""
    try:
        # Supabase에서 문서 목록 조회 (중복 제거)
        resp = supabase.table("documents").select("metadata").execute()
        sources = set()
        for item in resp.data:
            meta = item.get("metadata", {})
            if meta and "source" in meta:
                sources.add(meta["source"])
        
        return {"documents": sorted(list(sources))}
    except Exception as e:
        return {"documents": [], "error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 페이지 (index.html) 반환"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
