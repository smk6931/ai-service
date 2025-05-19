from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str
    personality: str
    

class ChatResponse(BaseModel):
    response: str
