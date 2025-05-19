from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.npc_chat import ChatRequest, ChatResponse
from app.services.npc_chat import NPCChatService  # 변경된 import 경로

router = APIRouter(prefix="/npc", tags=["npc_chat"])
service = NPCChatService()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    text = service.chat(request.question, request.personality)
    return ChatResponse(response=text)

@router.post("/chat/stream")
def chat_stream(request: ChatRequest):
    generator = service.chat_stream(request.question, request.personality)
    return StreamingResponse(generator, media_type="text/event-stream")
