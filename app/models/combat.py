from pydantic import BaseModel, Field
from typing import List, Optional, Tuple, Literal

# 캐릭터 공통 필드
class CharacterBase(BaseModel):
    id: str

# 전투 시작 요청용
class CharacterConfig(CharacterBase):
    name: str
    type: Literal["monster", "player"]
    personality: str
    skills: List[str]

class BattleInitRequest(BaseModel):
    characters: List[CharacterConfig]
    terrain: str
    weather: str

# 전투 판단 요청용
class CharacterState(CharacterBase):
    position: Tuple[int, int]
    hp: int
    ap: int
    status: List[str]

class BattleState(BaseModel):
    characters: List[CharacterState]
    cycle: int
    turn: int
    target_monster_id: str

# 전투 판단 응답용 (LLM → 행동 판단)
class MonsterAction(BaseModel):
    skill: str = Field(description="사용할 스킬의 이름")
    target_id: Optional[str] = Field(default=None, description="스킬을 사용할 대상의 ID (타겟이 필요하지 않은 경우 None 가능)")
    reason: Optional[str] = Field(default=None, description="행동 선택 이유")

class BattleActionResponse(BaseModel):
    monster_id: str
    actions: List[MonsterAction]

# AI 판단 용 모델
class CharacterForAI(CharacterConfig, CharacterState):
    pass


class BattleStateForAI(BaseModel):
    characters: List[CharacterForAI]
    cycle: int
    turn: int
    target_monster_id: str
    terrain: str
    weather: str
    