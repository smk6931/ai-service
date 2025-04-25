from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# API 라우터 임포트
from app.api.combat import router as combat_router
from app.api.users import router as users_router
from app.api.metadata import router as metadata_router
from app.api.characters import router as characters_router
from app.api.me import router as me_router
from app.api.npc_chat import router as npc_chat_router

# 환경 변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(title="Loreless AI Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(combat_router)
app.include_router(users_router)
app.include_router(metadata_router)
app.include_router(characters_router)
app.include_router(me_router)
app.include_router(npc_chat_router)

@app.get("/")
async def root():
    """헬스 체크 및 서버 상태 확인"""
    return {"status": "AI 서버 실행 중"}
