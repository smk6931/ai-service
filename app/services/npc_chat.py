from functools import lru_cache
from app.ai.npc_chat import NPCChatAI  # 변경된 import 경로
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

class NPCChatService:
    def __init__(self):
        self.ai = NPCChatAI()

    def chat(self, user_input: str) -> str:
        retriever = self.get_retriever()
        return self.ai.chat(user_input, retriever)

    def chat_stream(self, user_input: str):
        retriever = self.get_retriever()
        return self.ai.chat_stream(user_input, retriever)

    @lru_cache(maxsize=1)
    def get_embedding_model(self):
        return HuggingFaceEmbeddings(model_name="nlpai-lab/KURE-v1")

    @lru_cache(maxsize=1)
    def get_vectorstore(self):
        return Chroma(
            persist_directory="C:/LORELESS/ai-service/test/ChromaDB/Loreless_act_1",
            embedding_function=self.get_embedding_model(),
            collection_name="loreless_act_1"
        )

    @lru_cache(maxsize=1)
    def get_retriever(self):
        return self.get_vectorstore().as_retriever(search_kwargs={"k": 2})
