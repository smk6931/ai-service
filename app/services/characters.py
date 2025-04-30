import json
import uuid
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.db.characters import Character, CharacterStats
from app.db.users import Users

from app.models.characters import CharacterCreateRequest, CharacterUpdateRequest, CharacterStatsUpdateRequest, CharacterInfoRequest
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

ALLOWED_TRAITS = [
    "강인함", "잔잔함", "호전적", "충동적", "수비적", "신중함", "관찰꾼", "잔인함",
    "겁쟁이", "허세꾼", "교란꾼", "파괴적", "협동적", "용감함", "조화적",
    "고립적", "지능적", "냉정함", "원한꾼", "민첩함"
]

def get_character(request: CharacterInfoRequest, db: Session) -> Character:
    character = db.query(Character).filter_by(user_id=request.user_id).order_by(Character.created_time.desc()).first()
    return character

def create_character(request: CharacterCreateRequest, db: Session) -> Character:
    # 사용자 존재 여부 체크
    user = db.query(Users).filter(Users.user_id == request.user_id).first()
    if not user:
        raise ValueError("등록되지 않은 사용자입니다.")
    
    # 캐릭터 이름 중복 체크
    character_name = db.query(Character).filter_by(character_name=request.character_name).first()
    if character_name:
        raise ValueError("이미 존재하는 캐릭터 이름입니다.")

    character = Character(
        user_id=request.user_id,
        character_name=request.character_name,
        job=request.job,
        gender=request.gender,
        traits=request.traits
    )
    
    db.add(character)
    # character_id 확보
    db.flush()

    # 직업별 기본 스탯 세팅
    base_stats = {
        "warrior": dict(hp=120, attack=20, defense=15, resistance=10, critical_rate=0.05, critical_damage=1.5, move_range=4, speed=8, points=0),
        "archer": dict(hp=90, attack=25, defense=8, resistance=5, critical_rate=0.10, critical_damage=2.0, move_range=6, speed=12, points=0),
    }

    stats = CharacterStats(
        character_id=character.character_id,
        **base_stats[request.job.value]
    )
    
    db.add(stats)
    db.commit()
    db.refresh(character)
    
    return character

def update_character(request: CharacterUpdateRequest, db: Session) -> Character:
    character = db.query(Character).filter(Character.character_id == request.character_id).first()
    if not character:
        raise ValueError("캐릭터가 존재하지 않습니다.")
    
    update_fields = request.dict(exclude_unset=True, exclude={"character_id"})

    for field, value in update_fields.items():
        setattr(character, field, value)

    db.commit()
    db.refresh(character)

def update_character_stats(request: CharacterStatsUpdateRequest, db: Session):
    stats = db.query(CharacterStats).filter_by(character_id=request.character_id).first()

    if not stats:
        raise ValueError("해당 캐릭터의 스탯 정보가 없습니다.")

    update_fields = request.dict(exclude_unset=True, exclude={"character_id"})

    for field, value in update_fields.items():
        setattr(stats, field, value)

    db.commit()
    db.refresh(stats)

class CharacterCreationService:
    def __init__(self, db: Session):
        self.sessions = {}
        self.db = db

    async def prepare_session(self, user_id: str, websocket):
        """세션 초기화만 준비"""
        self.sessions[user_id] = {
            "websocket": websocket,
            "history": [
                {"role": "system", "content": (
                    "당신은 판타지 세계의 신비로운 존재입니다.\n"
                    "이 세계를 찾아온 이방인(사용자)에게 직접적으로 직업이나 성격을 묻지 말고, "
                    "대화를 통해 그들의 기질과 성향을 파악하세요.\n"
                    "최종 목표는 그들의 내면을 알아차리고 다음 두 직업 중 하나를 결정하는 것입니다:\n"
                    "- warrior (전사): 강력한 근접 전투 능력과 높은 방어력을 가진 직업\n"
                    "- archer (궁수): 원거리 공격과 높은 기동성을 가진 직업\n\n"
                    "또한 아래 고정된 성격 목록 중에서 3개를 추론해야 합니다:\n"
                    "성격 목록:\n"
                    "강인함, 잔잔함, 호전적, 충동적, 수비적, 신중함, 관찰꾼, 잔인함, "
                    "겁쟁이, 허세꾼, 교란꾼, 파괴적, 협동적, 용감함, 조화적, "
                    "고립적, 지능적, 냉정함, 원한꾼, 민첩함\n\n"
                    "5회의 대화 이후 서버가 이름과 성별을 요청할 것입니다.\n"
                    "그대는 부드럽운 어조를 유지해야 하며, "
                    "사용자의 깊은 본질을 끌어내기 위해 노력해야 합니다."
                )}
            ],
            "message_count": 0,
            "stage": "chatting",
            "user_inputs": {
                "character_name": None,
                "gender": None
            }
        }

    async def send_first_question(self, user_id: str):
        session = self.sessions.get(user_id)
        if session:
            websocket = session["websocket"]
            first_message = (
                "드디어 깨어났군요..\n"
                "앞으로의 모험에 대해 몇가지 질문을 드리겠습니다.\n"
                "지금부터 당신이 대답하는 내용에 따라 저는 당신을 기억할 것입니다."
            )
            session["history"].append({"role": "assistant", "content": first_message})
            await websocket.send_text(first_message)

    async def handle_user_message(self, user_id: str, user_message: str):
        """사용자 메시지 처리"""
        session = self.sessions.get(user_id)
        if not session:
            return
        
        websocket = session["websocket"]
        stage = session["stage"]

        if stage == "chatting":
            session["history"].append({"role": "user", "content": user_message})
            session["message_count"] += 1

            if session["message_count"] >= 5:
                # 5번 대화 완료 후 이름 요청
                session["stage"] = "asking_name"
                await websocket.send_text("알겠습니다. 앞으로의 모험을 위해 캐릭터의 이름을 지정해주세요.")
            else:
                # 자연스러운 대화 이어가기
                next_response = await self.ask_llm(session["history"])
                session["history"].append({"role": "assistant", "content": next_response})
                await websocket.send_text(next_response)

        elif stage == "asking_name":
            # 이름 입력 받기
            character_name = user_message.strip()
            
            # 이름 중복 체크
            existing_character = self.db.query(Character).filter_by(character_name=character_name).first()
            if existing_character:
                await websocket.send_text("이미 존재하는 캐릭터 이름입니다. 다른 이름을 입력해주세요.")
                return
                
            session["user_inputs"]["character_name"] = character_name
            session["stage"] = "asking_gender"
            await websocket.send_text("캐릭터의 성별을 알려주세요.")

        elif stage == "asking_gender":
            # 성별 입력 받기
            gender = self.detect_gender(user_message)
            if gender:
                session["user_inputs"]["gender"] = gender
                await self.finalize_character(user_id)
            else:
                await websocket.send_text("성별을 명확히 입력해주세요. (남성 / 여성)")

    async def ask_llm(self, history: list):
        """자연스러운 대화용 LLM 호출"""
        response = await openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=history,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    async def finalize_character(self, user_id: str):
        """대화 기록과 이름/성별을 종합해 캐릭터 최종 생성"""
        session = self.sessions.get(user_id)
        websocket = session["websocket"]

        summarize_prompt = (
            "지금까지 사용자와 나눈 대화를 바탕으로 다음 정보를 추론하여 JSON으로 출력하세요.\n"
            "- 직업 (warrior 또는 archer 중 하나)\n"
            "- 성격 (아래 목록 중 3개 고르세요)\n\n"
            "성격 목록:\n"
            "강인함, 잔잔함, 호전적, 충동적, 수비적, 신중함, 관찰꾼, 잔인함, "
            "겁쟁이, 허세꾼, 교란꾼, 파괴적, 협동적, 용감함, 조화적, "
            "고립적, 지능적, 냉정함, 원한꾼, 민첩함\n\n"
            f"캐릭터 이름: {session['user_inputs']['character_name']}\n"
            f"성별: {session['user_inputs']['gender']}\n\n"
            "반드시 아래 JSON 형태로만 출력하세요.\n"
            "{\n"
            "  \"job\": \"warrior\",\n"
            "  \"traits\": [\"강인함\", \"용감함\", \"민첩함\"]\n"
            "}"
        )

        extended_history = session["history"] + [{"role": "user", "content": summarize_prompt}]
        
        response = await openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=extended_history,
            temperature=0.3,
        )

        try:
            result = json.loads(response.choices[0].message.content)
            result["traits"] = self.validate_traits(result.get("traits", []))

            await self.save_character(user_id, result, session["user_inputs"])
            await websocket.send_text(
                f"캐릭터 생성 완료!\n"
                f"직업: {result['job']}\n"
                f"성격: {', '.join(result['traits'])}\n"
                f"이름: {session['user_inputs']['character_name']}\n"
                f"성별: {session['user_inputs']['gender']}"
            )
            session["stage"] = "finalized"
            await websocket.close()
        except Exception:
            await websocket.send_text("캐릭터 생성에 실패했습니다. 다시 시도해주세요.")
            await websocket.close()

    async def save_character(self, user_id: str, character_info: dict, user_inputs: dict):
        try:
            # 캐릭터 생성
            new_character = Character(
                character_id=str(uuid.uuid4()),
                user_id=user_id,
                character_name=user_inputs["character_name"],
                gender=user_inputs["gender"],
                job=character_info["job"],
                traits=character_info["traits"]
            )
            self.db.add(new_character)
            self.db.flush()

            # 직업별 기본 스탯 세팅
            base_stats = {
                "warrior": dict(hp=120, attack=20, defense=15, resistance=10, critical_rate=0.05, critical_damage=1.5, move_range=4, speed=8, points=0),
                "archer": dict(hp=90, attack=25, defense=8, resistance=5, critical_rate=0.10, critical_damage=2.0, move_range=6, speed=12, points=0),
            }

            stats = CharacterStats(
                character_id=new_character.character_id,
                **base_stats[character_info["job"]]
            )
            
            self.db.add(stats)
            self.db.commit()
            self.db.refresh(new_character)
            
            return new_character
        except Exception as e:
            self.db.rollback()
            raise e

    def validate_traits(self, traits: list):
        """성격 리스트를 고정 목록 기준으로 필터링"""
        return [trait for trait in traits if trait in ALLOWED_TRAITS]

    def detect_gender(self, text: str):
        """텍스트에서 성별 감지"""
        text = text.lower()
        if "남" in text or "male" in text:
            return "M"
        if "여" in text or "female" in text:
            return "F"
        return None