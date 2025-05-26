import os
import json
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Load environment variables
load_dotenv(override=True)

# 1) TF-CPP 로그 레벨 설정 (0=ALL, 1=INFO 제외, 2=INFO+WARNING 제외, 3=INFO+WARNING+ERROR 제외)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# 2) 파이썬 로깅 기본 레벨 설정
import logging
logging.basicConfig(level=logging.ERROR)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "item_gen_history.jsonl")

KST = timezone(timedelta(hours=9))  # 한국 시간대 (UTC+9)

def log_interaction(entry: dict):
    now_kst = datetime.now(KST)
    entry["timestamp"] = now_kst.isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# 1) 벡터DB 불러오기 및 리트리버 설정
embedding_model = HuggingFaceEmbeddings(model_name="nlpai-lab/KURE-v1")
db_scene_desc = Chroma(
    persist_directory="./app/vector_db/loreless_act1",
    embedding_function=embedding_model,
    collection_name="loreless_act_1"
)
retriever = db_scene_desc.as_retriever(search_kwargs={"k": 3})

# 2) World lore summary
loreless_summary = """
[세계관 & 분위기]
안개 낀 호숫가·폐허·끝없는 사막·숨 막히는 숲·깊은 협곡이 교차하는 어두운 배경
중세 판타지 세계관, 비밀스럽고 글루미한 분위기
기억을 잃은 주인공이 유물을 단서로 과거를 되찾고, 감정과 기억을 시험당하며 성장하는 서사

[주인공]
이름 없는 자

[핵심 지명]
카일름 마을, 파란디온 폐허, 브라에 사막, 나르센 숲, 불협의 성채, 라실로 예언탑 & 봉인 신전

[테마 & 감정]
상실·죄책감, 책임과 선택, 기억의 무기화

"""

# 3) Prompt template
item_prompt = ChatPromptTemplate.from_template("""
당신은 중세 판타지 소설의 아이템 디자이너입니다.
사용자가 입력한 아이템의 '아이템 기능'과 '장면', '세계관'를 참고하여, 판타지 아이템 정보를 직접 작성해주세요.
                                               
[스타일 지침]
- ‘아이템 기능’과 ‘장면 요약’을 보고,  
  - 분위기를 살린 간단한 서술형 설명을 만들어주세요..  
  - 단순하거나 평범한 효과나 기능만 요구된 경우엔 세계관 정보 없이 핵심 위주로 간결하게 설명하세요.  
  - 과도한 미사여구나 불필요한 수식어는 자제하고, 상황에 맞는 스타일을 선택하세요.

[아이템 기능]
{function}

[세계관]
{loreless_summary}

[장면]
{scene_summary}

다음과 같은 마크다운 형식으로 출력해주세요:

## item_category          
- (0=소비아이템, 1=무기 및 방어구, 2=Else 중 가장 적절한 하나를 선택하여 int만 출력)                                     
## category_name                                            
- (Equip, Consume, Else 중 가장 적절한 하나를 선택하여 출력)
## item_type
- (0=무기, 1=방어구, 2=투구, 3=망토, 4=크리처, 5=소비아이템, 0=그외 중 하나를 선택하여 출력)
## item_class
- (1=전사(검), 2=궁수(활, 화살), 0=공용 중 하나를 선택하여 출력)
## item_name
- ({loreless_summary}에 어울리며 자연스럽고 간결한 아이템 한글 이름) 
## description
- (아이템기능{function}을 단답형으로 생성, 아이템에 대한 설명을 세계관{loreless_summary}과 장면{scene_summary}을 반영하여 간결한 문장으로 생성)                                     
                                               
"""
)

# 4) Initialize LLM chain
llm = ChatOpenAI(
    temperature=0.6,
    model="gpt-4.1-nano",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)
chain = (item_prompt | llm)

# 5) Stateful designer class
default_steps = ("function", "scene_desc")
class ItemDesigner:
    def __init__(self, retriever, chain, lore_summary):
        self.retriever = retriever
        self.chain = chain
        self.lore_summary = lore_summary
        self.reset()

    def reset(self):
        self.function = None
        self.scene_desc = None

    async def step(self, user_input: str) -> str:
        print(f"▶ step() 호출 (function={self.function!r}, scene_desc={self.scene_desc!r})")
        if self.function is None:
            self.function = user_input
            return "🛠️ 이 아이템은 어떤 상황에 등장하나요? 장면을 설명해주세요."

        if self.scene_desc is None:
            self.scene_desc = user_input
            docs = self.retriever.invoke(self.scene_desc)
            merged = "\n\n".join(d.page_content for d in docs[:3])
            summary = await llm.ainvoke(f"다음 문맥을 3문장 이내로 요약:\n{merged}")
            # Generate final item
            result = await self.chain.ainvoke({
                "function": self.function,
                "loreless_summary": self.lore_summary,
                "scene_summary": summary
            })
            self.reset()
            return getattr(result, "content", result)
            # 메타데이터를 제외한 순수 텍스트만 반환
            #return result.content if hasattr(result, "content") else result

# 6) Pycord bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)
designers: dict[int, ItemDesigner] = {}

@bot.event
async def on_ready():
    print(f"▶ {bot.user} 연결됨, 명령어·메시지 핸들러 대기 중…")


@bot.command(name="아이템")
async def item_design(ctx, *, user_input: str = None):
    user_id = ctx.author.id
    # 사용자 커맨드 기록
    log_interaction({
        "type": "user",
        "user_id": user_id,
        "command": "아이템",
        "content": user_input or ""
    })

    # Start new session
    if user_id not in designers:
        designers[user_id] = ItemDesigner(retriever, chain, loreless_summary)
        prompt = "🛠️ 어떤 기능의 아이템을 만들고 싶으신가요? 예: '체력 30 회복'"
        log_interaction({
            "type": "bot",
            "user_id": user_id,
            "command": "아이템",
            "content": prompt
        })
        await ctx.send(prompt)
        return

    designer = designers[user_id]
    text = await designer.step(user_input)
    
    log_interaction({
        "type": "bot",
        "user_id": user_id,
        "content": text
    })

    await ctx.send(text)
    # End session
    if designer.function is None and designer.scene_desc is None:
        designers.pop(user_id, None)    

@bot.event
async def on_message(message):
    # 봇 자신의 메시지나 다른 봇은 무시
    if message.author.bot:
        return

    user_id = message.author.id
    print(f"▶ on_message 호출 (ID: {user_id}, content={message.content!r})")
    
    # 사용자 메시지 기록
    log_interaction({
        "type": "user",
        "user_id": user_id,
        "channel": str(message.channel),
        "content": message.content
    })    
    
    # 1) 진행 중인 디자이너가 있으면, step() 실행
    if user_id in designers:
        designer = designers[user_id]
        text = await designer.step(message.content)
        log_interaction({
            "type": "bot",
            "user_id": user_id,
            "channel": str(message.channel),
            "content": text
        })
        await message.channel.send(text)
        if designer.function is None and designer.scene_desc is None:
            designers.pop(user_id, None)
        return

    # 2) 대화 중이 아니면, 평소 커맨드 처리
    await bot.process_commands(message)

# Run
bot.run(os.getenv("DISCORD_TOKEN"))
