import openai

SYSTEM_PROMPT = "당신은 게임 속 질문에 친절하게 답하는 NPC입니다."

class NPCChatAI:
    def get_npc_personality(self, personality) -> str:
        system_prompt = f"당신은 게임 속 질문에 답하는 NPC입니다. {personality} 말투로 답변해주세요."
        
        return system_prompt
    
    def chat(self, user_input: str, retriever, personality) -> str:
        docs = retriever.invoke(user_input)
        context = "\n\n".join(d.page_content for d in docs)

        messages = [
            # {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": self.get_npc_personality(personality)},
            {"role": "user", "content": f"{context}\n\n{user_input}에 대해 3줄 이내로 답변해주세요."}
        ]
        resp = openai.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            temperature=0.5
        )
        return resp.choices[0].message.content

    def chat_stream(self, user_input: str, retriever, personality):
        docs = retriever.invoke(user_input)
        context = "\n\n".join(d.page_content for d in docs)

        messages = [
            # {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": self.get_npc_personality(personality)},
            {"role": "user", "content": f"{context}\n\n{user_input}에 대해 3줄 이내로 답변해주세요."}
        ]
        response = openai.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            temperature=0.5,
            stream=True
        )

        for chunk in response:
            token = chunk.choices[0].delta.content
            if token:
                yield token
